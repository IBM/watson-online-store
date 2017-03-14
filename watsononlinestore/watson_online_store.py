import random
import os
import time
from pprint import pprint
from fake_discovery import  FAKE_DISCOVERY

# Limit the result count when calling Discovery query.
DISCOVERY_QUERY_COUNT = 5
# Limit more when formatting. This one could be removed now that the above
# was added, but keeping it allows us to log more results for dev/test even
# though we return fewer to the client.
DISCOVERY_KEEP_COUNT = 5
# Truncate the Discovery 'text'. It can be a lot. We'll add "..." if truncated.
DISCOVERY_TRUNCATE = 500

DEBUG = True


class OnlineStoreCustomer:
    def __init__(self, email=None, first_name=None, last_name=None,
                 shopping_cart=[], logged_in=False):

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

    def context_merge(self, dict1, dict2):
        new_dict = dict1.copy()
        if dict2:
            new_dict.update(dict2)

        return new_dict

    def parse_slack_output(self, slack_rtm_output):
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output and \
                    'user_profile' not in output and \
                        self.at_bot in output['text']:
                    return (output['text'].split(
                        self.at_bot)[1].strip().lower(),
                         output['channel'],
                         output['user'])
        return None, None, None

    def post_to_slack(self, response, channel):
        self.slack_client.api_call("chat.postMessage",
                                   channel=channel,
                                   text=response, as_user=True)

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
        user_json = None
        user_data = None

        try:
            # Get the authenticated user profile from Slack
            user_json = self.slack_client.api_call("users.info",
                                                   user=user_id)
        except:
            pass
        if DEBUG and user_json and "error" not in user_json:
            print("user_from_slack:\n{}\n".format(user_json))

        # Slack will output even before user provides input,
        # this will show up as "error"
        if "error" not in user_json:
            cust = user_json['user']['profile']['email']
            user_data = self.cloudant_online_store.find_customer(cust)
        if user_data and DEBUG:
            print("user_from_DB\n{}\n".format(user_data))
        # We found this Slack user in our Cloudant DB
        if user_data:
            self.customer_from_db(user_data)
        elif "error" not in user_json:
            # Didn't find Slack user in DB, so add them
            self.create_user_from_ui(user_json)

        if self.customer:
            # Now Watson will have customer info
            self.add_customer_to_context()

    def get_fake_discovery_response(self, input_text):
        index =  random.randint(0,len(FAKE_DISCOVERY)-1)
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

        # is response Json? It needs to be...
        self.context = self.context_merge(self.context, response)
        if DEBUG:
            print("watson_discovery:\n{}\ncontext:\n{}".format(
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
        if not ('results' in response and response['results']):
            return "No results from Discovery."

        results = response['results']

        output = ["Top results found for your query:"]
        for i in range(min(len(results), DISCOVERY_KEEP_COUNT)):
            result = results[i]

            if 'html' in result:
                html = result['html']
                href_tag = "<a href="
                sidx = html.find(href_tag)
                if sidx > 0:
                    sidx += len(href_tag) + 1
                    eidx = html.find(">", sidx, len(html))
                    if eidx > 0:
                        tag = html[sidx:eidx-1]
                        output.append(tag)

            if 'text' in result:
                text = result['text']
                text = text if len(text) < DISCOVERY_TRUNCATE else (
                    "%s ..." % text[:DISCOVERY_TRUNCATE])
                output.append(text)

            if 'blekko' in result:
                blekko = result['blekko']

                # Trying to use result['text'] instead. Need to compare.
                # if 'snippet' in blekko:
                # output.append('\n'.join(blekko['snippet']))
                # elif 'clean_title' in blekko:
                # # Using elif because snippet usually includes a title.
                # output.append('\n'.join(blekko['clean_title']))

                if 'url' in blekko:
                    output.append(blekko['url'])

                if 'twitter' in blekko:
                    twitter = blekko['twitter']
                    if 'image' in twitter:
                        output.append(twitter['image'])
                    if 'image:src' in twitter:
                        output.append(twitter['image:src'])

        return '\n'.join(output)

    def get_discovery_response(self, input_text):

        discovery_response = self.discovery_client.query(
            environment_id=self.discovery_environment_id,
            collection_id=self.discovery_collection_id,
            query_options={'query': input_text, 'count': DISCOVERY_QUERY_COUNT}
        )
        if DEBUG:
            # This dumps a ton of results for us to peruse:
            pprint(discovery_response)

        formatted_response = self.format_discovery_response(discovery_response)

        if DEBUG:
            # This dumps a ton of results for us to peruse:
            pprint(formatted_response)

        return {'discovery_result': formatted_response}

    def handle_list_shopping_cart(self):
        """ Get shopping_cart from DB and return to Watson
            Returns: list of shopping_cart items
        """
        cust = self.customer.email
        shopping_list = self.cloudant_online_store.list_shopping_cart(cust)
        self.context['shopping_cart'] = shopping_list

        # no need for user input, return to Watson Dialogue
        return False

    def clear_shopping_cart(self):
        self.context['shopping_cart'] = ''
        self.context['cart_item'] = ''

    def handle_delete_from_cart(self):
        """ Delete an item from this Customers shopping cart
        """
        item = self.context['cart_item']
        email = self.customer.email
        self.cloudant_online_store.delete_item_shopping_cart(email, item)
        self.clear_shopping_cart()

        # no need for user input, return to Watson Dialogue
        return False

    def handle_add_to_cart(self):
        """ Add an item to this Customers shopping cart
        """
        item = self.context['cart_item']
        email = self.customer.email
        self.cloudant_online_store.add_to_shopping_cart(email, item)
        self.clear_shopping_cart()

        # no need for user input, return to Watson Dialogue
        return False

    def handle_message(self, message, channel):
        """ Handler for messages.
            param: message from UI (slackbot)
            param: channel
        """

        watson_response = self.get_watson_response(message)
        if DEBUG:
            print("watson_response:\n{}\n".format(watson_response))
        if 'context' in watson_response:
            self.context = watson_response['context']

        response = ''
        for text in watson_response['output']['text']:
            response += text + "\n"

        self.post_to_slack(response, channel)

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
                                    shopping_cart=['floop','bark'],
                                    logged_in=True)
        self.cloudant_online_store.add_customer_obj(scott)

    def run(self):
        # make sure DB exists
        self.cloudant_online_store.init()
        self.add_test_users_to_DB()

        if self.slack_client.rtm_connect():
            print("Watson Online Store bot is connected and running!")
            get_input = True
            while True:
                slack_output = self.slack_client.rtm_read()
                if DEBUG and slack_output:
                    print("slack output\n:{}\n".format(slack_output))

                message, channel, user = self.parse_slack_output(slack_output)
                if not self.customer:
                    self.init_customer(user)

                if DEBUG and message:
                    print("message:\n %s\n channel:\n %s\n" %
                          (message, channel))
                if message and channel:
                    get_input = self.handle_message(message, channel)
                    while not get_input:
                        get_input = self.handle_message(message, channel)

                time.sleep(self.delay)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")
