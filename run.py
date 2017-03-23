#!/usr/bin/env python

import json
import os
from cloudant.client import Cloudant
from dotenv import load_dotenv
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1
from watson_developer_cloud import DiscoveryV1

from watsononlinestore.watson_online_store import WatsonOnlineStore
from database.cloudant_online_store import CloudantOnlineStore

MISSING_ENV_VARS = "ERROR: Required environment variables are not set."


class WatsonEnv:

    def __init__(self):
        pass

    @staticmethod
    def get_vcap_credentials(vcap_env, service):
        if service in vcap_env:
            vcap_conversation = vcap_env[service]
            if isinstance(vcap_conversation, list):
                first = vcap_conversation[0]
                if 'credentials' in first:
                    return first['credentials']

    @staticmethod
    def get_slack_user_id(slack_client):
        """Get slack bot user ID from SLACK_BOT_USER or BOT_ID env vars.

        Use the original BOT_ID if found, but now we can instead take the
        SLACK_BOT_USER (familiar bot name) and look-up the ID.
        This should be called after env is loaded when using dotenv.
        """
        slack_bot_user = os.environ.get('SLACK_BOT_USER')
        print("Looking up BOT_ID for '%s'" % slack_bot_user)

        api_call = slack_client.api_call("users.list")
        if api_call.get('ok'):
            # retrieve all users so we can find our bot
            users = api_call.get('members')
            for user in users:
                if 'name' in user and user.get('name') == slack_bot_user:
                    bot_id = user.get('id')
                    print("Found BOT_ID=" + bot_id)
                    return bot_id
            else:
                print("could not find user with the name " + slack_bot_user)
        else:
            print("could not find user because api_call did not return 'ok'")
        return None

    @staticmethod
    def get_watson_online_store():
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

        print("+++++++DUMPENV++++++++++++++++++++++++++++++++==")
        print(os.environ)
        print("+++++++DUMPENV++++++++++++++++++++++++++++++++==")

        # Use these env vars first if set
        bot_id = os.environ.get("BOT_ID")
        slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
        conversation_username = os.environ.get("CONVERSATION_USERNAME")
        conversation_password = os.environ.get("CONVERSATION_PASSWORD")
        cloudant_username = os.environ.get("CLOUDANT_USERNAME")
        cloudant_password = os.environ.get("CLOUDANT_PASSWORD")
        cloudant_url = os.environ.get("CLOUDANT_URL")
        cloudant_db_name = os.environ.get("CLOUDANT_DB_NAME")

        # TODO: It looks like we'll want to make discovery required too.
        discovery_username = os.environ.get('DISCOVERY_USERNAME')
        discovery_password = os.environ.get('DISCOVERY_PASSWORD')
        discovery_environment_id = os.environ.get('DISCOVERY_ENVIRONMENT_ID')
        discovery_collection_id = os.environ.get('DISCOVERY_COLLECTION_ID')

        if not all((conversation_username,
                    conversation_password,
                    cloudant_username,
                    cloudant_password,
                    cloudant_url,
                    discovery_username,
                    discovery_password)):
            # If some of the service env vars are not set get them from VCAP
            vcap_env = None
            vcap_services = os.environ.get("VCAP_SERVICES")
            print('===========================================')
            print("VCAP_SERVICES")
            print('===========================================')
            print(vcap_services)
            print('===========================================')
            if vcap_services:
                vcap_env = json.loads(vcap_services)
                print(vcap_env)
            print('===========================================')
            if vcap_env:
                conversation_creds = WatsonEnv.get_vcap_credentials(
                    vcap_env, 'conversation')
                conversation_username = \
                    conversation_username or conversation_creds['username']
                conversation_password = \
                    conversation_password or conversation_creds['password']

                cloudant_creds = WatsonEnv.get_vcap_credentials(
                    vcap_env, 'cloudantNoSQLDB')
                cloudant_username = \
                    cloudant_username or cloudant_creds['username']
                cloudant_password = \
                    cloudant_password or cloudant_creds['password']
                cloudant_url = cloudant_url or cloudant_creds['url']

                discovery_creds = WatsonEnv.get_vcap_credentials(
                    vcap_env, 'discovery')
                discovery_username = \
                    discovery_username or discovery_creds['username']
                discovery_password = \
                    discovery_password or discovery_creds['password']

        # If we still don't have all the above plus a few, then no WOS.
        if not all((slack_bot_token,
                    conversation_username,
                    conversation_password,
                    cloudant_username,
                    cloudant_password,
                    cloudant_url,
                    cloudant_db_name)):
            print(MISSING_ENV_VARS)
            return None

        # If BOT_ID wasn't set, we can get it using SlackClient and user ID.
        slack_client = SlackClient(slack_bot_token)
        if not bot_id:
            bot_id = WatsonEnv.get_slack_user_id(slack_client)
            if not bot_id:
                print("Error: Missing BOT_ID or invalid SLACK_BOT_USER.")
                return None

        conversation_client = ConversationV1(
            username=conversation_username,
            password=conversation_password,
            version='2016-07-11')

        cloudant_online_store = CloudantOnlineStore(
            Cloudant(
                cloudant_username,
                cloudant_password,
                url=cloudant_url,
                connect=True
            ),
            cloudant_db_name
        )
        #
        # Init Watson Discovery only if all the env vars are set.
        #
        discovery_client = None
        if all((discovery_username,
                discovery_password,
                discovery_environment_id,
                discovery_collection_id)):
            discovery_client = DiscoveryV1(
                version='2016-11-07',
                username=discovery_username,
                password=discovery_password)
        watsononlinestore = WatsonOnlineStore(bot_id,
                                              slack_client,
                                              conversation_client,
                                              discovery_client,
                                              cloudant_online_store)
        return watsononlinestore


if __name__ == "__main__":
    watsononlinestore = WatsonEnv.get_watson_online_store()

    watsononlinestore.run()
