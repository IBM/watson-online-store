import os
import time
from pprint import pprint

# Limit the result count when calling Discovery query.
DISCOVERY_QUERY_COUNT = 2
# Limit more when formatting. This one could be removed now that the above
# was added, but keeping it allows us to log more results for dev/test even
# though we return fewer to the client.
DISCOVERY_KEEP_COUNT = 1
# Truncate the Discovery 'text'. It can be a lot. We'll add "..." if truncated.
DISCOVERY_TRUNCATE = 500

DEBUG = True


class OnlineStoreCustomer:
    def __init__(self, email=None, first_name=None, last_name=None,
                 purchase_history=None, favorites=None,
                 logged_in=False):

        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.purchase_history = purchase_history
        self.favorites = favorites
        self.logged_in = logged_in


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
        self.context['send_no_input'] = 'no'
        self.context['logged_in'] = False

        self.customer = None

    def context_merge(self, dict1, dict2):
        new_dict = dict1.copy()
        new_dict.update(dict2)

        return new_dict

    def parse_slack_output(self, slack_rtm_output):
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output and \
                    'user_profile' not in output and \
                        self.at_bot in output['text']:
                    return output['text'].split(
                        self.at_bot)[1].strip().lower(), output['channel']
        return None, None

    def post_to_slack(self, response, channel):
        self.slack_client.api_call("chat.postMessage",
                                   channel=channel,
                                   text=response, as_user=True)

    def cleanup_email(self, slack_response):
        email_addr = slack_response.split("|")[1]
        return email_addr.replace(">", "")

    def handle_db_lookup(self):
        """ Go to the DB and look up the user.
        """
        if DEBUG:
            print("DB lookup:\n{}".format(self.context['email']))
        email_addr = str(self.context['email'])
        if "mailto" in email_addr:
            email_addr = self.cleanup_email(email_addr)
        if DEBUG:
            print("DB.\n email_addr:{}\n".format(email_addr))
        user_data = self.cloudant_online_store.find_customer(email_addr)
        if DEBUG:
            print("DB.\n user_data:{}\n".format(user_data))

        if not user_data:
            return True
        # Merge data from DB with existing context
        self.context = self.context_merge(self.context, user_data)
        if DEBUG:
            print("DB.\n context:{}\n".format(self.context))
        return False

    def handle_lookupAndAddEmail(self):
        """ Verify email is not in DB and add to DB.
        """
        email_addr = str(self.context['email'])
        if "mailto" in email_addr:
            email_addr = self.cleanup_email(email_addr)
        if DEBUG:
            print("DB.\n email_addr:{}\n".format(email_addr))
        existing_user = self.cloudant_online_store.find_customer(email_addr)
        if DEBUG:
            print("DB.\n existing_user:{}\n".format(existing_user))
        if existing_user:
            # return some error
            return False

        # start to create the customer, add to DB when complete
        self.customer = OnlineStoreCustomer(email=email_addr)

        return True

    def handle_AddName(self):
        """ Add User Name to existing OnlineStoreCustomer
        """
        full_name = str(self.context['full_name'])
        first, last = full_name.split()
        self.customer.first_name = first
        self.customer.last_name = last

        # TODO continue to ask for favorites and remove next lines, maybe,
        #  but not for now.
        self.customer.logged_in = True
        self.context['logged_in'] = False
        # logged_in = {'logged_in': True}
        self.context = self.context_merge(self.context, logged_in)
        if DEBUG:
            print("AddName context:\n{}".format(self.context))
        self.cloudant_online_store.add_customer_obj(self.customer)

        return True

    # replace with markstur branch add_discovery_query
    def get_fake_discovery_response(self, input_text):
        ret_string = {'discovery_result': ' blah blah blah'}
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

            if 'text' in result:
                text = result['text']
                text = text if len(text) < DISCOVERY_TRUNCATE else (
                    "%s ..." % text[:DISCOVERY_TRUNCATE])
                output.append(text)

            if 'blekko' not in result:
                output.append("todo - missing expected result key")
            else:
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

    def handle_message(self, message, channel):
        """ Handler for messages.
            param: message from UI (slackbot)
            param: channel

            returns True if UI(slackbot) input is required
            returns False if we want app processing and no input
        """

        watson_response = self.get_watson_response(message)
        if DEBUG:
            print("watson_response:\n{}\n".format(watson_response))
        self.context = watson_response['context']

        response = ''
        for text in watson_response['output']['text']:
            response += text + "\n"

        self.post_to_slack(response, channel)

        if ('send_no_input' in self.context.keys() and
            self.context['send_no_input'] == 'yes' and
            'email' in self.context.keys() and
                self.context['email']):
            return self.handle_db_lookup()

        if ('intent' in self.context.keys() and
            self.context['intent'] == 'CreateUserAccount' and
            'state' in self.context.keys() and
                self.context['state'] == 'lookupAndAddEmail'):
            return self.handle_lookupAndAddEmail()

        if ('intent' in self.context.keys() and
            self.context['intent'] == 'CreateUserAccount' and
            'state' in self.context.keys() and
                self.context['state'] == 'AddName'):
            return self.handle_AddName()

        if ('discovery_string' in self.context.keys() and
            self.context['discovery_string'] and
            # remove next line when tested:
                True):
            # add next line when tested
            # self.discovery_client):
            return self.handle_DiscoveryQuery()

        if ('send_no_input' in self.context.keys() and
                self.context['send_no_input'] == 'yes'):
            return False

        return True

    def add_test_users_to_DB(self):
        molly = OnlineStoreCustomer(email="molly@gmail.com",
                                    first_name="Molly",
                                    last_name="DA",
                                    purchase_history="abc123",
                                    favorites="shoes",
                                    logged_in=True)
        self.cloudant_online_store.add_customer_obj(molly)
        scott = OnlineStoreCustomer(email="scott@gmail.com",
                                    first_name="Scott",
                                    last_name="Smith",
                                    purchase_history="cba321",
                                    favorites="pants",
                                    logged_in=True)
        self.cloudant_online_store.add_customer_obj(scott)
        mark = OnlineStoreCustomer(email="mark@gmail.com",
                                   first_name="Mark",
                                   last_name="Jones",
                                   purchase_history="xyz123",
                                   favorites="shirts",
                                   logged_in=True)
        self.cloudant_online_store.add_customer_obj(mark)

    def run(self):
        # make sure DB exists
        self.cloudant_online_store.init()
        # add some test users
        self.add_test_users_to_DB()

        if self.slack_client.rtm_connect():
            print("Watson Online Store bot is connected and running!")
            get_slack = True
            while True:
                slack_output = self.slack_client.rtm_read()
                if DEBUG and slack_output:
                    print("slack output\n:{}\n".format(slack_output))
                message, channel = self.parse_slack_output(slack_output)
                if DEBUG and message:
                    print("message:\n %s\n channel:\n %s\n" %
                          (message, channel))
                if message and channel:
                    get_slack = self.handle_message(message, channel)
                    while not get_slack:
                        get_slack = self.handle_message(message, channel)

                time.sleep(self.delay)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")
