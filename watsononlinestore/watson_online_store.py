import logging
import random
import os
import re
import time
from watsononlinestore.fake_discovery import FAKE_DISCOVERY

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)

# Limit the result count when calling Discovery query.
DISCOVERY_QUERY_COUNT = 5
# Limit more when formatting. This one could be removed now that the above
# was added, but keeping it allows us to log more results for dev/test even
# though we return fewer to the client.
DISCOVERY_KEEP_COUNT = 5
# Truncate the Discovery 'text'. It can be a lot. We'll add "..." if truncated.
DISCOVERY_TRUNCATE = 500


class SlackSender:

    def __init__(self, slack_client, channel):
        self.slack_client = slack_client
        self.channel = channel

    def send_message(self, message):
        self.slack_client.api_call("chat.postMessage",
                                   channel=self.channel,
                                   text=message,
                                   as_user=True)


class OnlineStoreCustomer:
    def __init__(self, email=None, first_name=None, last_name=None,
                 shopping_cart=None, logged_in=False):

        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.shopping_cart = shopping_cart
        self.logged_in = logged_in

    def get_customer_dict(self):
        """ Specific to our cloudant_online_store
        """
        customer = {
            'type': 'customer',
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'shopping_cart': self.shopping_cart,
            'logged_in': self.logged_in
        }
        return customer


class WatsonOnlineStore:
    def __init__(self, bot_id, slack_client,
                 conversation_client, discovery_client,
                 cloudant_online_store):
        self.bot_id = bot_id

        self.slack_client = slack_client
        self.conversation_client = conversation_client
        self.discovery_client = discovery_client
        self.cloudant_online_store = cloudant_online_store

        self.at_bot = "<@" + bot_id + ">"
        self.delay = 0.5  # second
        self.workspace_id = os.environ.get("WORKSPACE_ID")
        self.discovery_environment_id = os.environ.get(
            'DISCOVERY_ENVIRONMENT_ID')
        self.discovery_collection_id = os.environ.get(
            'DISCOVERY_COLLECTION_ID')

        self.context = {}
        self.context['email'] = None
        self.context['logged_in'] = False

        self.customer = None
        self.response_tuple = None

    def context_merge(self, dict1, dict2):
        new_dict = dict1.copy()
        if dict2:
            new_dict.update(dict2)

        return new_dict

    def parse_slack_output(self, output_list):
        if output_list and len(output_list) > 0:
            for output in output_list:
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
        self.slack_client.api_call("chat.postMessage",
                                   channel=channel,
                                   text=response,
                                   as_user=True)

    def add_customer_to_context(self):
        """ We have a customer, send info to Watson

           The customer data from the UI is in the Cloudant DB, or has
            been added. Now add it to the context and pass back to Watson.
        """
        self.context = self.context_merge(self.context,
                                          self.customer.get_customer_dict())

    def customer_from_db(self, user_data):
        """ Set the customer using data from Cloudant DB
        """

        email_addr = user_data['email']
        first = user_data['first_name']
        last = user_data['last_name']
        self.customer = OnlineStoreCustomer(email=email_addr,
                                            first_name=first,
                                            last_name=last,
                                            shopping_cart=[],
                                            logged_in=True)

    def create_user_from_ui(self, user_json):
        """Create a new user from data in Slack

            Authenticated user in slack will have email, First, and Last
           names. Create a user in the DB for this. Note that a different
           UI will require different code here
        """

        email_addr = user_json['user']['profile']['email']
        first = user_json['user']['profile']['first_name']
        last = user_json['user']['profile']['last_name']
        self.customer = OnlineStoreCustomer(email=email_addr,
                                            first_name=first,
                                            last_name=last,
                                            shopping_cart=[],
                                            logged_in=True)

    def init_customer(self, user_id):
        """ Get user from DB, or create entry for user.

            Note that this is specific to using Slack as the UI.
             A different UI will require different code for the API
             calls.
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
        index = random.randint(0, len(FAKE_DISCOVERY)-1)
        ret_string = {'discovery_result': FAKE_DISCOVERY[index]}
        return ret_string

    def handle_DiscoveryQuery(self):
        """ Do a Discovery query
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
        response = self.conversation_client.message(
            workspace_id=self.workspace_id,
            message_input={'text': message},
            context=self.context)
        return response

    @staticmethod
    def format_discovery_response(response):
        """Try to limit the volumes of response to just enough."""
        output = []
        if not ('results' in response and response['results']):
            return output

        def slack_encode(input_text):
            """Slack does not like <, &, >. That's all."""

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

        discovery_response = self.discovery_client.query(
            environment_id=self.discovery_environment_id,
            collection_id=self.discovery_collection_id,
            query_options={'query': input_text, 'count': DISCOVERY_QUERY_COUNT}
        )

        response = self.format_discovery_response(discovery_response)
        self.response_tuple = response

        formatted_response = ""
        for item in response:
            formatted_response += "\n" + item['cart_number'] + ") " + \
                                  item['name'] + \
                                  "\n" + item['image']  # "\n" + item['url']

        return {'discovery_result': formatted_response}

    def handle_list_shopping_cart(self):
        """ Get shopping_cart from DB and return to Watson
            Returns: list of shopping_cart items
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
        self.context['shopping_cart'] = ''
        self.context['cart_item'] = ''

    def handle_delete_from_cart(self):
        """ Delete an item from this Customers shopping cart
        """
        email = self.customer.email
        shopping_list = self.cloudant_online_store.list_shopping_cart(email)
        try:  # Passing text i.e. 'hi' breaks this. Fix better in future...
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
        """ Add an item to this Customers shopping cart
        """
        try:  # Passing text i.e. 'hi' breaks this. Fix better in future...
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
        """ Handler for messages.
            param: message from UI (slackbot)
            param: sender to use for send_message

            returns True if UI(slackbot) input is required
            returns False if we want app processing and no input
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
            self.context['discovery_string'] and
            # remove next line when tested:
                True):
            # add next line when tested
            # self.discovery_client):
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

    def add_test_users_to_DB(self):
        scott = OnlineStoreCustomer(email="scott.dangelo@ibm.com",
                                    first_name="Scott",
                                    last_name="DAngelo",
                                    shopping_cart=['floop', 'bark'],
                                    logged_in=True)
        self.cloudant_online_store.add_customer_obj(scott)

    def run(self):
        # make sure DB exists
        self.cloudant_online_store.init()
        self.add_test_users_to_DB()

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
