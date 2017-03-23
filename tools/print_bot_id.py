#!/usr/bin/env python
import logging
import os
from slackclient import SlackClient

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)

BOT_NAME = "wos"

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

if __name__ == "__main__":
    api_call = slack_client.api_call("users.list")
    if api_call.get('ok'):
        # retrieve all users so we can find our bot
        users = api_call.get('members')
        for user in users:
            if 'name' in user and user.get('name') == BOT_NAME:
                print("Bot ID for '" + user['name'] + "' is " + user.get('id'))
                break
        else:
            print("could not find bot user with the name " + BOT_NAME)

    else:
        print("could not find bot user because api_call did not return 'ok'")
