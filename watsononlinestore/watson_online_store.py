import os
import time

DEBUG=True

class WatsonOnlineStore:
    def __init__(self, bot_id, slack_client,
                 conversation_client, cloudant_online_store):
        self.bot_id = bot_id

        self.slack_client = slack_client
        self.conversation_client = conversation_client
        self.cloudant_online_store = cloudant_online_store

        self.at_bot = "<@" + bot_id + ">"
        self.delay = 0.5  # second
        self.workspace_id = os.environ.get("WORKSPACE_ID")

        self.context = {}
        self.context['email'] = None
        self.context['send_no_input'] = 'no'
        self.context['logged_in'] = False

    #stub method for DB call
    def get_fake_user(self, email):
        fake1={"user":"Scott",
               "suggestion":"You seem to like shoes. Want to look at our selection",
               "logged_in": True
              }
        return fake1

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
                    return output['text'].split(self.at_bot)[1].strip().lower(), \
                           output['channel']
        return None, None


    def post_to_slack(self, response, channel):
        self.slack_client.api_call("chat.postMessage",
                                   channel=channel,
                                   text=response, as_user=True)


    def cleanup_email(self, slack_response):
        email_addr = slack_response.split("|")[1]
        return email_addr.replace(">","")

    def handle_message(self, message, channel):
        watson_response = self.conversation_client.message(
            workspace_id=self.workspace_id,
            message_input={'text': message},
            context=self.context)

        if DEBUG:
            print("watson_response:\n{}\n".format(watson_response))
        self.context = watson_response['context']

        response = ''
        for text in watson_response['output']['text']:
            response += text + "\n"

        self.post_to_slack(response, channel)

        if ((watson_response['context']['send_no_input'] == 'yes') and
           watson_response['context']['email']):
            #Here's where we go to the DB and look up the user
            #user_data = self.get_fake_user(watson_response['context']['email'])
            if DEBUG:
                print("DB lookup:\n{}".format(str(watson_response['context']['email'])))
            email_addr = str(watson_response['context']['email'])
            if "mailto" in email_addr:
                email_addr = self.cleanup_email(email_addr)
            if DEBUG:
                print("DB.\n email_addr:{}\n".format(email_addr))
            user_data = self.cloudant_online_store.find_customer(email_addr)
            if DEBUG:
                print("DB.\n user_data:{}\n".format(user_data))

            if not user_data:
                return True
            #Merge data from DB with existing context
            self.context = self.context_merge(watson_response['context'], user_data)
            if DEBUG:
                print("DB.\n context:{}\n".format(self.context))
            return False

        return True


    def add_test_users_to_DB(self):
        self.cloudant_online_store.add_customer("scott@gmail.com","Scott","DA","foo","bar")
        self.cloudant_online_store.add_customer("rich@gmail.com","Rich","Hagarty","foo","bar")
        self.cloudant_online_store.add_customer("mark@gmail.com","Mark","Stur","foo","bar")
        self.cloudant_online_store.add_customer("steve@gmail.com","Steve","Martinelli","foo","bar")

    def run(self):
        # make sure DB exists
        self.cloudant_online_store.init() 
        # add some test users
        self.add_test_users_to_DB()

        if self.slack_client.rtm_connect():
            print("Watson Online Store bot is connected and running!")
            while True:
                slack_output = self.slack_client.rtm_read()
                if DEBUG and slack_output:
                    print("slack output\n:{}\n".format(slack_output))
                message, channel = self.parse_slack_output(slack_output)
                if DEBUG and message:
                    print("message:\n {}\n channel:\n {}\n".format(message, channel))
                if message and channel:
                    wait_for_input = self.handle_message(message, channel)
                    if not wait_for_input:
                        self.handle_message(message, channel)

                time.sleep(self.delay)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")
