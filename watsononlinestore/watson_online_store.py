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
# Available data sources for Discovery
DISCOVERY_AMAZON_STORE = "AMAZON"
DISCOVERY_IBM_STORE = "IBM_STORE"


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
        self.workspace_id = self.setup_conversation_workspace(
            conversation_client, os.environ)

        # IBM Cloudant noSQL database
        self.cloudant_online_store = cloudant_online_store

        # IBM Watson Discovery Service
        self.discovery_client = discovery_client
        self.discovery_data_source = os.environ.get(
            'DISCOVERY_DATA_SOURCE', DISCOVERY_IBM_STORE)
        try:
            self.discovery_score_filter = float(
                os.environ.get(self.discovery_data_source +
                               '_DISCO_SCORE_FILTER', 0))
        except ValueError:
            LOG.debug(self.discovery_data_source +
                      "_DISCO_SCORE_FILTER must " +
                      "be a number between 0.0 and 1.0. " +
                      "Using default value of 0.0")
            self.discovery_score_filter = 0.0
            pass

        self.discovery_environment_id, self.discovery_collection_id = (
            self.setup_discovery_collection(discovery_client,
                                            self.discovery_data_source,
                                            os.environ))

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
        :param object environ: runtime environment variables
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
    def setup_discovery_collection(discovery_client,
                                   data_source,
                                   environ):
        """ Ensure that the collection exists in the Watson Discovery service.

        :param discovery_client: discovery service client
        :param str data_source: name of the discovery data source
        :param object environ: runtime environment variables
        :return: ID of discovery environment and collection to use
        :rtype: str
        :raise Exception: When collection is not found and cannot be created
        """

        def fixed_create_collection(
                environment_id, name, description="", configuration_id=None):
            """ Temporary fix until pypi version is released."""

            if configuration_id is None:
                default_config = discovery_client.get_default_configuration_id(
                    environment_id=environment_id)
                configuration_id = default_config

            data_dict = {'configuration_id': configuration_id,
                         'name': name,
                         'description': description}

            url_string = '/v1/environments/{0}/collections'.format(
                environment_id)

            return discovery_client.request(
                method='POST',
                url=url_string,
                json=data_dict,
                params={'version': discovery_client.version}, accept_json=True)

        # If environment id exist, ensure it is valid.
        environment_id = environ.get('DISCOVERY_ENVIRONMENT_ID')
        if environment_id:
            try:
                LOG.debug("Using DISCOVERY_ENVIRONMENT_ID=%s" % environment_id)
                discovery_client.get_environment(environment_id)
            except Exception:
                raise Exception("Environment with DISCOVERY_ENVIRONMENT_ID=%s "
                                "does not exist." % environment_id)
        else:
            # Try to find the environment by name.
            name = environ.get('DISCOVERY_ENVIRONMENT_NAME',
                               'watson-online-store')
            # Can't use/modify the defaullt discovery environment
            reserved_name = "Watson News Environment"

            environments = discovery_client.get_environments()['environments']
            for environment in environments:
                if environment['name'] == name:
                    environment_id = environment['environment_id']
                    LOG.debug("Found DISCOVERY_ENVIRONMENT_ID=%(id)s using "
                              "lookup by name=%(name)s" %
                              {'id': environment_id, 'name': name})
                    break
                elif environment['name'] != reserved_name:
                    # Last resort will be to use an available one
                    environment_id = environment['environment_id']

            if not environment_id:
                # No existing environment found, so create it.
                # NOTE that the number of environments that can be created
                # under a trial Bluemix account is limited to one environment
                # per organization.
                try:
                    LOG.debug("Creating discovery environment...")
                    created = discovery_client.create_environment(
                        name,
                        "Discovery environment created by "
                        "watson-online-store.",
                        size=0)
                    environment_id = created['environment_id']
                    LOG.debug("Created DISCOVERY_ENVIRONMENT_ID=%(id)s with "
                              "name=%(name)s" %
                              {'id': environment_id, 'name': name})
                except Exception as e:
                    raise Exception("Error creating Discovery "
                                    "Error: %s" % repr(e))

        # Determine if collection exists.
        collection_id = environ.get(data_source + '_DISCO_COLLECTION_ID')
        if collection_id:
            try:
                LOG.debug("Using DISCOVERY_COLLECTION_ID=%s" % collection_id)
                discovery_client.get_collection(environment_id,
                                                collection_id)
                return environment_id, collection_id
            except Exception:
                raise Exception("Collection with DISCOVERY_COLLECTION_ID=%s "
                                "does not exist." % collection_id)
        else:
            # Try to find collection by name. Search all collections
            # that exist in the discovery environment.

            # Discovery collection names
            amazon_collection_name = "amazon-shopping"
            ibm_collection_name = "ibm-logo-store"
            # File path location to discovery html files
            amazon_data_path = "data/amazon_data_html/"
            ibm_data_path = "data/ibm_store_html/"

            collections = discovery_client.list_collections(
                environment_id)['collections']
            for coll in collections:
                if ((data_source == DISCOVERY_AMAZON_STORE and
                        coll['name'] == amazon_collection_name) or
                        (data_source == DISCOVERY_IBM_STORE and
                            coll['name'] == ibm_collection_name)):
                    return environment_id, coll['collection_id']

        # Doesn't exist, so create it.
        LOG.debug("Creating collection from html files...")
        try:
            if data_source == DISCOVERY_AMAZON_STORE:
                name = amazon_collection_name
                path = amazon_data_path
            elif data_source == DISCOVERY_IBM_STORE:
                name = ibm_collection_name
                path = ibm_data_path
            if name:
                # collection = discovery_client.create_collection(
                collection = fixed_create_collection(
                    environment_id,
                    name)

                # Add documents to collection
                if collection:
                    collection_id = collection['collection_id']
                    for _, _, files in os.walk(path):
                        for file in files:
                            if file.endswith('.html'):
                                with open(os.path.join(path, file), 'r') as f:
                                    data = f.read()
                                discovery_client.add_document(environment_id,
                                                              collection_id,
                                                              file_data=data)

        except Exception as e:
            raise Exception("Discovery Collection could not be created. "
                            "Error: %s" % repr(e))

        if not collection_id:
            raise Exception("Discovery Collection could not be found "
                            "or created.")

        return environment_id, collection_id

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

        :param dict output_dict: text, channel, user, etc from slack posting
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
        try:
            first = user_json['user']['profile']['first_name']
        except KeyError:
            first = email_addr
        try:
            last = user_json['user']['profile']['last_name']
        except KeyError:
            last = email_addr
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

    def get_fake_discovery_response(self):
        """Returns fake response from IBM Discovery for testing purposes.

        :returns: list of Urls
        :rtype: list
        """
        index = random.randint(0, len(FAKE_DISCOVERY)-1)
        ret_string = {'discovery_result': FAKE_DISCOVERY[index]}
        return ret_string

    def handle_discovery_query(self):
        """Take query string from Watson Context and send to Discovery.

        Discovery response will be merged into context in order to allow it to
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
            response = self.get_fake_discovery_response()

        self.context = self.context_merge(self.context, response)
        LOG.debug("watson_discovery:\n{}\ncontext:\n{}".format(response,
                                                               self.context))

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
    def format_discovery_response(response, data_source):
        """Format data for Slack based on discovery data source.

        This method handles the different data source data and formats
        it specifically for Slack.

        The following functions are specific to the data source that has
        been fed into the Watson Discovery service. This example has two
        data sources to choose from: "IBM_STORE" and "AMAZON'. Which data
        source is being used is specified in the ".env" file by setting
        the following key values:

        <data_source>_DISCO_COLLECTION_ID=<collection id of data source>
        <data_source>_DISCO_SCORE_FILTER=<float value betweem 0.0. and 1.0>
        DISCOVERY_DATA_SOURCE="<data source string name>"

        This pattern should be followed if additional data sources are
        added.

        :param dict response: output from Discovery
        :param string data_source: name of the discovery data source
        :returns: cart_number, name, url, image for each item returned
        :rtype: dict
        """
        output = []
        if not response.get('results'):
            return output

        def get_product_name(entry):
            """ Pull product name from entry data for nice user display.

            :param dict entry: output from Discovery
            :returns: name of product
            :rtype: str
            """
            product_name = ""

            if data_source == DISCOVERY_AMAZON_STORE:
                # For amazon data, Watson Discovery has pulled the
                # product name from the html page and stored it as
                # "title" in its enriched metadata that it generates.
                if 'extracted_metadata' in entry:
                    metadata = entry['extracted_metadata']
                    if 'title' in metadata:
                        product_name = metadata['title']
            elif data_source == DISCOVERY_IBM_STORE:
                # For IBM store data, the product name was placed in
                # text of the page, in the format:
                # "Product: <product name> "Category".
                if 'text' in entry:
                    product_tag = "Product:"
                    category_tag = "Category:"
                    text = entry['text']
                    sidx = text.find(product_tag)
                    if sidx > 0:
                        sidx += len(product_tag)
                        eidx = text.find(category_tag, sidx, len(text))
                        if eidx > 0:
                            product_name = text[sidx:eidx-1]

            return product_name

        def get_product_url(entry):
            """ Pull product url from entry data so user can navigate
            to product page.

            :param dict entry: output from Discovery
            :returns: url link to product description
            :rtype: str
            """
            product_url = ""

            if 'html' in entry:
                html = entry['html']

                if data_source == DISCOVERY_AMAZON_STORE:
                    # For amazon data, the product URL is stored in an
                    # href tag located at the end of the html doc.
                    href_tag = "<a href="
                    # Search from bottom of the doc.
                    sidx = html.rfind(href_tag)
                    if sidx > 0:
                        sidx += len(href_tag)
                        eidx = html.find('>', sidx, len(html))
                        if eidx > 0:
                            product_url = html[sidx+1:eidx-1]
                elif data_source == DISCOVERY_IBM_STORE:
                    # For IBM store data, the product URL requires a
                    # product ID. The product ID can be found by searching
                    # the html doc for "/ProductDetail.aspx?pid=<PID>".
                    # The product URL can then be built by appending
                    # this string to:
                    # ""http://www.logostore-globalid.us".
                    url_start = "http://www.logostore-globalid.us"
                    href_tag = "/ProductDetail.aspx?pid="
                    sidx = html.find(href_tag)
                    if sidx > 0:
                        sidx += len(href_tag)
                        product_id = html[sidx:sidx+6]
                        product_url = url_start + href_tag + product_id

            return product_url

        def get_image_url(entry):
            """Pull product image url from entry data to allow
            pictures in slack.

            :param dict entry: output from Discovery
            :returns: url link to product image
            :rtype: str
            """
            image_url = ""

            if data_source == DISCOVERY_AMAZON_STORE:
                # There is no image url for Amazon data,
                # so use the product url.
                return get_product_url(entry)
            elif data_source == DISCOVERY_IBM_STORE:
                # For IBM store data, the image url is located in the
                # html page, and is specified with a "<a class='jqzoom'" tag.
                if 'html' in entry:
                    html = entry['html']
                    img_tag = '<a class="jqzoom" href="'
                    simg = html.find(img_tag)
                    if simg > 0:
                        simg += len(img_tag)
                        eimg = html.find('"', simg)
                        if eimg > 0:
                            img = html[simg:eimg]
                            # shrink the picture
                            image_url = re.sub(
                                r'scale\[[0-9]+\]', 'scale[50]', img)

            return image_url

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
        for i in range(min(len(results), DISCOVERY_KEEP_COUNT)):
            result = results[i]

            product_data = {
                "cart_number": str(cart_number),
                "name": slack_encode(get_product_name(result)),
                "url": slack_encode(get_product_url(result)),
                "image": slack_encode(get_image_url(result)),
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

        response = self.format_discovery_response(discovery_response,
                                                  self.discovery_data_source)
        self.response_tuple = response

        fmt = "{cart_number}) {name}\n{image}"
        formatted_response = "\n".join(fmt.format(**item) for item in response)
        return {'discovery_result': formatted_response}

    def handle_list_shopping_cart(self):
        """Get shopping_cart from DB and return formatted version to Watson

        :returns: formatted shopping_cart items
        :rtype: str
        """
        cust = self.customer.email
        shopping_list = self.cloudant_online_store.list_shopping_cart(cust)
        formatted_out = "\n".join("{}) {}".format(i + 1, item.encode('utf-8'))
                                  for i, item in enumerate(shopping_list))
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
        sender.send_message("\n".join(watson_response['output']['text']) + "\n")

        if (self.context.get('discovery_string') and self.discovery_client):
            return self.handle_discovery_query()

        cart_action = self.context.get('shopping_cart')
        if cart_action == 'list':
            return self.handle_list_shopping_cart()
        elif cart_action == 'add':
            if ('cart_item' in self.context and
               self.context['cart_item'] != ''):
                return self.handle_add_to_cart()
        elif cart_action == 'delete':
            if ('cart_item' in self.context.keys() and
               self.context['cart_item'] != ''):
                return self.handle_delete_from_cart()

        if self.context.get('get_input') == 'no':
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
