#!/usr/bin/env python

import json
import os
import time
from cloudant.client import Cloudant
from dotenv import load_dotenv
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1

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

  watsononlinestore = WatsonOnlineStore(bot_id,
                                  slack_client,
                                  conversation_client,
                                  cloudant_online_store)

  watsononlinestore.run()
