#!/usr/bin/env python

import os
from cloudant.client import Cloudant
from dotenv import load_dotenv
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1
from watson_developer_cloud import DiscoveryV1

from watsononlinestore.watson_online_store import WatsonOnlineStore
from database.cloudant_online_store import CloudantOnlineStore

if __name__ == "__main__":
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    bot_id = os.environ.get("BOT_ID")

    slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

    conversation_client = ConversationV1(
        username=os.environ.get("CONVERSATION_USERNAME"),
        password=os.environ.get("CONVERSATION_PASSWORD"),
        version='2016-07-11')

    cloudant_online_store = CloudantOnlineStore(
        Cloudant(
            os.environ.get("CLOUDANT_USERNAME"),
            os.environ.get("CLOUDANT_PASSWORD"),
            url=os.environ.get("CLOUDANT_URL"),
            connect=True
        ),
        os.environ.get("CLOUDANT_DB_NAME")
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

    watsononlinestore.run()
