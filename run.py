#!/usr/bin/env python

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
    def get_watson_online_store():
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

        # Get all the required environment vars
        bot_id = os.environ.get("BOT_ID")
        slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
        conversation_username = os.environ.get("CONVERSATION_USERNAME")
        conversation_password = os.environ.get("CONVERSATION_PASSWORD")
        cloudant_username = os.environ.get("CLOUDANT_USERNAME")
        cloudant_password = os.environ.get("CLOUDANT_PASSWORD")
        cloudant_url = os.environ.get("CLOUDANT_URL")
        cloudant_db_name = os.environ.get("CLOUDANT_DB_NAME")
        if not all((bot_id,
                    slack_bot_token,
                    conversation_username,
                    conversation_password,
                    cloudant_username,
                    cloudant_password,
                    cloudant_url,
                    cloudant_db_name)):
            print(MISSING_ENV_VARS)
            return None

        slack_client = SlackClient(slack_bot_token)

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
        discovery_username = os.environ.get('DISCOVERY_USERNAME')
        discovery_password = os.environ.get('DISCOVERY_PASSWORD')
        discovery_environment_id = os.environ.get('DISCOVERY_ENVIRONMENT_ID')
        discovery_collection_id = os.environ.get('DISCOVERY_COLLECTION_ID')
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
