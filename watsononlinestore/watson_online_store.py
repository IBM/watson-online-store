# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import logging
import os
import random
import re
import time

from watsononlinestore.tests.fake_discovery import FAKE_DISCOVERY

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)

# Limit the result count when calling Discovery query.
DISCOVERY_QUERY_COUNT = 10
# Limit more when formatting and filtering out "weak" results.
# Also useful for allowing us to log more results for dev/test even
# though we return fewer to the client.
DISCOVERY_KEEP_COUNT = 5
# Truncate the Discovery 'text'. It can be a lot. We'll add "..." if truncated.
DISCOVERY_TRUNCATE = 500


class SlackSender:

    def __init__(self, slack_client, channel):
        self.slack_client = slack_client
        self.channel = channel

    def send_message(self, message):
        """Sends message via Slack API.

        :param str message: The message to be sent to slack
        """
        self.slack_client.api_call("chat.postMessage",
                                   channel=self.channel,
                                   text=message,
                                   as_user=True)


class OnlineStoreCustomer:
    def __init__(self, email=None, first_name=None, last_name=None,
                 shopping_cart=None):

        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.shopping_cart = shopping_cart

    def get_customer_dict(self):
        """Returns a dict in form usable by our cloudant_online_store DB

        :returns: customer dict of customer data for noSQL doc
        :rtype: dict
        """
        customer = {
            'type': 'customer',
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'shopping_cart': self.shopping_cart
        }
        return customer


class WatsonOnlineStore:
    def __init__(self, bot_id, slack_client,
                 conversation_client, discovery_client,
                 cloudant_online_store):

        # specific for Slack as UI
        self.bot_id = bot_id
        self.slack_client = slack_client
        self.at_bot = "<@" + bot_id + ">"

        # IBM Watson Conversation
        self.conversation_client = conversation_client
        self.discovery_client = discovery_client
        self.workspace_id = self.setup_conversation_workspace(
            conversation_client, os.environ)

        # IBM Cloudant noSQL database
        self.cloudant_online_store = cloudant_online_store

        # IBM Discovery Service
        self.discovery_environment_id = os.environ.get(
            'DISCOVERY_ENVIRONMENT_ID')
        self.discovery_collection_id = os.environ.get(
            'DISCOVERY_COLLECTION_ID')

        try:
            self.discovery_score_filter = float(os.environ.get(
                "DISCOVERY_SCORE_FILTER", 0))
        except ValueError:
            LOG.error("DISCOVERY_SCORE_FILTER must be a number between " +
                      "0.0 and 1.0. Using default value of 0.0")
            self.discovery_score_filter = 0
            pass

        self.context = {}
        self.customer = None
        self.response_tuple = None
        self.delay = 0.5  # second

    @staticmethod
    def setup_conversation_workspace(conversation_client, environ):
        """Verify and/or initialize the conversation workspace.

        If a WORKSPACE_ID is specified in the runtime environment,
        make sure that workspace exists. If no WORKSTATION_ID is
        specified then try to find it using a lookup by name.
        Name will be 'watson-online-store' unless overridden
        using the WORKSPACE_NAME environment variable.

        If a workspace is not found by ID or name, then try to
        create one from the JSON in data/workspace.json. Use the
        name as mentioned above so future lookup will find what
        was created.

        :param conversation_client: Conversation service client
        :param environ: Runtime environment variables
        :return: ID of conversation workspace to use
        :rtype: str
        :raise Exception: When workspace is not found and cannot be created
        """

        # Get the actual workspaces
        workspaces = conversation_client.list_workspaces()['workspaces']

        env_workspace_id = environ.get('WORKSPACE_ID')
        if env_workspace_id:
            # Optionally, we have an env var to give us a WORKSPACE_ID.
            # If one was set in the env, require that it can be found.
            LOG.debug("Using WORKSPACE_ID=%s" % env_workspace_id)
            for workspace in workspaces:
                if workspace['workspace_id'] == env_workspace_id:
                    ret = env_workspace_id
                    break
            else:
                raise Exception("WORKSPACE_ID=%s is specified in a runtime "
                                "environment variable, but that workspace "
                                "does not exist." % env_workspace_id)
        else:
            # Find it by name. We may have already created it.
            name = environ.get('WORKSPACE_NAME', 'watson-online-store')
            for workspace in workspaces:
                if workspace['name'] == name:
                    ret = workspace['workspace_id']
                    LOG.debug("Found WORKSPACE_ID=%(id)s using lookup by "
                              "name=%(name)s" % {'id': ret, 'name': name})
                    break
            else:
                # Not found, so create it.
                LOG.debug("Creating workspace from data/workspace.json...")
                workspace = WatsonOnlineStore.get_workspace_json()
                created = conversation_client.create_workspace(
                    name,
                    "Conversation workspace created by watson-online-store.",
                    workspace['language'],
                    intents=workspace['intents'],
                    entities=workspace['entities'],
                    dialog_nodes=workspace['dialog_nodes'],
                    counterexamples=workspace['counterexamples'],
                    metadata=workspace['metadata'])
                ret = created['workspace_id']
                LOG.debug("Created WORKSPACE_ID=%(id)s with "
                          "name=%(name)s" % {'id': ret, 'name': name})
        return ret

    @staticmethod
    def get_workspace_json():
        with open('data/workspace.json') as workspace_file:
            workspace = json.load(workspace_file)
        return workspace

    def context_merge(self, dict1, dict2):
        """Combine 2 dicts into one for Watson Conversation context.

        Common data in dict2 will override data in dict1

        :param dict dict1: original context dictionary
        :param dict dict2: new context dictionary - will override fields
        :returns: new_dict for context
        :rtype: dict
        """
        new_dict = dict1.copy()
        if dict2:
            new_dict.update(dict2)

        return new_dict

    def parse_slack_output(self, output_dict):
        """Prepare output when using Slack as UI.

        :param dict output: text, channel, user, etc from slack posting
        :returns: text, channel, user
        :rtype: str, str, str
        """
        if output_dict and len(output_dict) > 0:
            for output in output_dict:
                if output and 'text' in output and 'user' in output and (
                        'user_profile' not in output):
                    if self.at_bot in output['text']:
                        return (
                            ''.join(output['text'].split(self.at_bot
                                                         )).strip().lower(),
                            output['channel'],
                            output['user'])
                    elif (output['channel'].startswith('D') and
                          output['user'] != self.bot_id):
                        # Direct message!
                        return (output['text'].strip().lower(),
                                output['channel'],
                                output['user'])
        return None, None, None

    def post_to_slack(self, response, channel):
        """API for posting to Slack.

        :param str response: text from Watson to post to Slack
        :param str channel: Slack channel
        """
        self.slack_client.api_call("chat.postMessage",
                                   channel=channel,
                                   text=response,
                                   as_user=True)

    def add_customer_to_context(self):
        """Send Customer info to Watson using context.

        The customer data from the UI is in the Cloudant DB, or has
        been added. Now add it to the context and pass back to Watson.
        """
        self.context = self.context_merge(self.context,
                                          self.customer.get_customer_dict())

    def customer_from_db(self, user_data):
        """Set the customer using data from Cloudant DB.

        We have the Customer in the Cloudant DB. Create a Customer object from
        this data and set for this instance of WatsonOnlineStore

        :param dict user_data: email, first_name, and last_name
        """

        email_addr = user_data['email']
        first = user_data['first_name']
        last = user_data['last_name']
        self.customer = OnlineStoreCustomer(email=email_addr,
                                            first_name=first,
                                            last_name=last,
                                            shopping_cart=[])

    def create_user_from_ui(self, user_json):
        """Set the customer using data from Slack.

        Authenticated user in slack will have email, First, and Last
        names. Create a user in the DB for this. Note that a different
        UI will require different code here.
        json info in ['user']['profile']

        :param dict user_json: email, first_name, and last_name
        """

        email_addr = user_json['user']['profile']['email']
        first = user_json['user']['profile']['first_name']
        last = user_json['user']['profile']['last_name']
        self.customer = OnlineStoreCustomer(email=email_addr,
                                            first_name=first,
                                            last_name=last,
                                            shopping_cart=[])

    def init_customer(self, user_id):
        """Get user from DB, or create entry for user.

        Note that this is specific to using Slack as the UI.
        A different UI will require different code for the API calls.

        :param str user_id: email address of user
        """
        assert user_id

        try:
            # Get the authenticated user profile from Slack
            user_json = self.slack_client.api_call("users.info",
                                                   user=user_id)
        except Exception:
            LOG.exception("Slack client call exception:")
            return

        # Not found returns json with error.
        LOG.debug("user_from_slack:\n{}\n".format(user_json))

        if user_json and 'user' in user_json:
            cust = user_json['user'].get('profile', {}).get('email')
            if cust:
                user_data = self.cloudant_online_store.find_customer(cust)
                if user_data:
                    # We found this Slack user in our Cloudant DB
                    LOG.debug("user_from_DB\n{}\n".format(user_data))
                    self.customer_from_db(user_data)
                else:
                    # Didn't find Slack user in DB, so add them
                    self.create_user_from_ui(user_json)
                    self.cloudant_online_store.add_customer_obj(self.customer)

            if self.customer:
                # Now Watson will have customer info
                self.add_customer_to_context()

    def get_fake_discovery_response(self, input_text):
        """Returns fake response from IBM Discovery for testing purposes.

        :param str input_text: search request from UI
        :returns: list of Urls
        :rtype: list
        """
        index = random.randint(0, len(FAKE_DISCOVERY)-1)
        ret_string = {'discovery_result': FAKE_DISCOVERY[index]}
        return ret_string

    def handle_DiscoveryQuery(self):
        """Take query string from Watson Context and send to Discovery.

        Discovery reponse will be merged into context in order to allow it to
        be returned to Watson. In the case where there is no discovery client,
        a fake response will be returned, for testing purposes.

        :returns: False indicating no need for UI input, just return to Watson
        :rtype: Bool
        """
        query_string = self.context['discovery_string']
        if self.discovery_client:
            try:
                response = self.get_discovery_response(query_string)
            except Exception as e:
                response = {'discovery_result': repr(e)}
        else:
            response = self.get_fake_discovery_response(query_string)

        self.context = self.context_merge(self.context, response)
        LOG.debug("watson_discovery:\n{}\ncontext:\n{}".format(
                   response, self.context))

        # no need for user input, return to Watson Dialogue
        return False

    def get_watson_response(self, message):
        """Sends text and context to Watson and gets reply.

        Message input is text, self.context is also added and sent to Watson.

        :param str message: text to send to Watson
        :returns: json dict from Watson
        :rtype: dict
        """
        response = self.conversation_client.message(
            workspace_id=self.workspace_id,
            message_input={'text': message},
            context=self.context)
        return response

    @staticmethod
    def format_discovery_response(response):
        """Takes specific ibm_store_html data and formats for Slack.

        This method is particular to the data in ibm_store_html and a new
        method would be needed for other data. The formatted output is also
        specific for Slack.

        :param dict response: input from Discovery
        :returns: cart_numer, name, url, image for each item returned
        :rtype: dict
        """
        output = []
        if not ('results' in response and response['results']):
            return output

        def slack_encode(input_text):
            """Remove chars <, &, > for Slack.

            :param str input_text: text to be cleaned for Slack
            :returns: text without undesirable chars
            :rtype: str
            """

            if not input_text:
                return input_text

            args = [('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;')]
            for from_to in args:
                input_text = input_text.replace(*from_to)

            return input_text

        results = response['results']

        cart_number = 1
        href_tag = "/ProductDetail.aspx?pid="
        img_tag = '<a class="jqzoom" href="'
        product_tag = "Product:"
        category_tag = "Category:"
        url_start = "http://www.logostore-globalid.us"

        for i in range(min(len(results), DISCOVERY_KEEP_COUNT)):
            result = results[i]

            product_name = ""
            product_url = ""
            img_url = ""

            # Pull out product number so that we can build url link.
            if 'html' in result:
                html = result['html']
                sidx = html.find(href_tag)
                if sidx > 0:
                    sidx += len(href_tag)
                    product_id = html[sidx:sidx+6]
                    product_url = url_start + href_tag + product_id

                # grab the image url to allow pictures in slack
                simg = html.find(img_tag)
                if simg > 0:
                    simg += len(img_tag)
                    eimg = html.find('"', simg)
                    if eimg > 0:
                        img = html[simg:eimg]
                        # shrink the picture
                        img_url = re.sub(
                            r'scale\[[0-9]+\]', 'scale[50]', img)

            # Pull out product name from page text.
            if 'text' in result:
                text = result['text']
                sidx = text.find(product_tag)
                if sidx > 0:
                    sidx += len(product_tag)
                    eidx = text.find(category_tag, sidx, len(text))
                    if eidx > 0:
                        product_name = text[sidx:eidx-1]

            product_data = {"cart_number": str(cart_number),
                            "name": slack_encode(product_name),
                            "url": slack_encode(product_url),
                            "image": slack_encode(img_url),
                            }
            cart_number += 1
            output.append(product_data)

        return output

    def get_discovery_response(self, input_text):
        """Call discovery with input_text and return formatted response.

        Formatted response_tuple is saved for WatsonOnlineStore to allow item
        to be easily added to shopping cart.
        Response is then further formatted to be passed to UI.

        :param str input_text: query to be used with Watson Discovery Service
        :returns: Discovery response in format for Watson Conversation
        :rtype: dict
        """

        discovery_response = self.discovery_client.query(
            environment_id=self.discovery_environment_id,
            collection_id=self.discovery_collection_id,
            query_options={'query': input_text, 'count': DISCOVERY_QUERY_COUNT}
        )

        # Watson discovery assigns a confidence level to each result.
        # Based on data mix, we can assign a minimum tolerance value in an
        # attempt to filter out the "weakest" results.
        if self.discovery_score_filter and 'results' in discovery_response:
            fr = [x for x in discovery_response['results'] if 'score' in x and
                  x['score'] > self.discovery_score_filter]

            discovery_response['matching_results'] = len(fr)
            discovery_response['results'] = fr

        response = self.format_discovery_response(discovery_response)
        self.response_tuple = response

        formatted_response = ""
        for item in response:
            formatted_response += "\n" + item['cart_number'] + ") " + \
                                  item['name'] + \
                                  "\n" + item['image']  # "\n" + item['url']

        return {'discovery_result': formatted_response}

    def handle_list_shopping_cart(self):
        """Get shopping_cart from DB and return formatted version to Watson

        :returns: formatted shopping_cart items
        :rtype: str
        """
        cust = self.customer.email
        formatted_out = ""
        shopping_list = self.cloudant_online_store.list_shopping_cart(cust)
        for index, item in enumerate(shopping_list):
            formatted_out += str(index+1) + ") " + str(item) + "\n"

        self.context['shopping_cart'] = formatted_out

        # no need for user input, return to Watson Dialogue
        return False

    def clear_shopping_cart(self):
        """Clear shopping_cart and cart_item fields in context
        """
        self.context['shopping_cart'] = ''
        self.context['cart_item'] = ''

    def handle_delete_from_cart(self):
        """Pulls cart_item from Watson context and deletes from Cloudant DB

        cart_item in context must be an int or delete will silently fail.
        """
        email = self.customer.email
        shopping_list = self.cloudant_online_store.list_shopping_cart(email)
        try:
            item_num = int(self.context['cart_item'])
        except ValueError:
            LOG.exception("cart_item must be a number")
            return False

        for index, item in enumerate(shopping_list):
            if index+1 == item_num:
                self.cloudant_online_store.delete_item_shopping_cart(email,
                                                                     item)
        self.clear_shopping_cart()

        # no need for user input, return to Watson Dialogue
        return False

    def handle_add_to_cart(self):
        """Adds cart_item from Watson context and saves in Cloudant DB

        cart_item in context must be an int or add/save will silently fail.
        """
        try:
            cart_item = int(self.context['cart_item'])
        except ValueError:
            LOG.exception("cart_item must be a number")
            return False
        email = self.customer.email

        for index, entry in enumerate(self.response_tuple):
            if index+1 == cart_item:
                item = entry['name'] + ': ' + entry['url'] + '\n'
                self.cloudant_online_store.add_to_shopping_cart(email, item)
        self.clear_shopping_cart()

        # no need for user input, return to Watson Dialogue
        return False

    def handle_message(self, message, sender):
        """Handler for messages coming from Watson Conversation using context.

        Fields in context will trigger various actions in this application.

        :param str message: text from UI
        :param SlackSender sender: used for send_message, hard-coded as Slack

        :returns: True if UI input is required, False if we want app
         processing and no input
        :rtype: Bool
        """

        watson_response = self.get_watson_response(message)
        LOG.debug("watson_response:\n{}\n".format(watson_response))
        if 'context' in watson_response:
            self.context = watson_response['context']

        response = ''
        for text in watson_response['output']['text']:
            response += text + "\n"

        sender.send_message(response)

        if ('discovery_string' in self.context.keys() and
           self.context['discovery_string'] and self.discovery_client):
            return self.handle_DiscoveryQuery()

        if ('shopping_cart' in self.context.keys() and
                self.context['shopping_cart'] == 'list'):
            return self.handle_list_shopping_cart()

        if ('shopping_cart' in self.context.keys() and
                self.context['shopping_cart'] == 'add' and
            'cart_item' in self.context.keys() and
                self.context['cart_item'] != ''):
            return self.handle_add_to_cart()

        if ('shopping_cart' in self.context.keys() and
                self.context['shopping_cart'] == 'delete' and
            'cart_item' in self.context.keys() and
                self.context['cart_item'] != ''):
            return self.handle_delete_from_cart()

        if ('get_input' in self.context.keys() and
                self.context['get_input'] == 'no'):
            return False

        return True

    def run(self):
        """Main run loop of the application
        """
        # make sure DB exists
        self.cloudant_online_store.init()

        if self.slack_client.rtm_connect():
            LOG.info("Watson Online Store bot is connected and running!")
            while True:
                slack_output = self.slack_client.rtm_read()
                if slack_output:
                    LOG.debug("slack output\n:{}\n".format(slack_output))

                message, channel, user = self.parse_slack_output(slack_output)
                if user and not self.customer:
                    self.init_customer(user)

                if message:
                    LOG.debug("message:\n %s\n channel:\n %s\n" %
                              (message, channel))
                if message and channel:
                    sender = SlackSender(self.slack_client, channel)
                    get_input = self.handle_message(message, sender)
                    while not get_input:
                        get_input = self.handle_message(message, sender)

                time.sleep(self.delay)
        else:
            LOG.warning("Connection failed. Invalid Slack token or bot ID?")
