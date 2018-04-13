#!/usr/bin/env python

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
import os

import metrics_tracker_client
from cloudant.client import Cloudant
from dotenv import load_dotenv
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1
from watson_developer_cloud import DiscoveryV1

from watsononlinestore.database.cloudant_online_store import \
    CloudantOnlineStore
from watsononlinestore.watson_online_store import WatsonOnlineStore


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

        # Use these env vars first if set
        bot_id = os.environ.get("BOT_ID")
        slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
        conversation_username = os.environ.get("CONVERSATION_USERNAME")
        conversation_password = os.environ.get("CONVERSATION_PASSWORD")
        conversation_url = os.environ.get("CONVERSATION_URL")
        cloudant_username = os.environ.get("CLOUDANT_USERNAME")
        cloudant_password = os.environ.get("CLOUDANT_PASSWORD")
        cloudant_url = os.environ.get("CLOUDANT_URL")
        cloudant_db_name = os.environ.get(
            "CLOUDANT_DB_NAME") or 'watson_online_store'
        discovery_username = os.environ.get('DISCOVERY_USERNAME')
        discovery_password = os.environ.get('DISCOVERY_PASSWORD')
        discovery_url = os.environ.get('DISCOVERY_URL')

        # If the CLOUDANT_USERNAME env var was not set then use
        # VCAP_SERVICES like a WatsonService would.
        if not cloudant_username:
            vcap_services = os.environ.get("VCAP_SERVICES")
            vcap_env = json.loads(vcap_services) if vcap_services else None
            if vcap_env:
                cloudant_creds = WatsonEnv.get_vcap_credentials(
                    vcap_env, 'cloudantNoSQLDB')
                if cloudant_creds:
                    cloudant_url = cloudant_creds['url']  # overrides default
                    if 'username' in cloudant_creds:
                        cloudant_username = cloudant_creds['username']
                    if 'password' in cloudant_creds:
                        cloudant_password = cloudant_creds['password']

        # Instantiate Watson Assistant client.
        # - only give a url if we have one (don't override the default)
        conversation_kwargs = {
            'version': '2017-05-26',
            'username': conversation_username,
            'password': conversation_password
        }
        if conversation_url:
            conversation_kwargs['url'] = conversation_url

        conversation_client = ConversationV1(**conversation_kwargs)

        # Instantiate Cloudant DB.
        cloudant_online_store = CloudantOnlineStore(
            Cloudant(
                cloudant_username,
                cloudant_password,
                url=CloudantOnlineStore.optimize_cloudant_url(cloudant_url),
                connect=True
            ),
            cloudant_db_name
        )

        # Instantiate Watson Discovery client.
        # - only give a url if we have one (don't override the default)
        discovery_kwargs = {
            'version': '2017-09-01',
            'username': discovery_username,
            'password': discovery_password
        }
        if discovery_url:
            discovery_kwargs['url'] = discovery_url

        discovery_client = DiscoveryV1(**discovery_kwargs)

        # Instantiate Slack chatbot.
        if not slack_bot_token or 'placeholder' in slack_bot_token:
            print("SLACK_BOT_TOKEN needs to be set correctly. "
                  "It is currently set to '%s'." % slack_bot_token)
            print("Only the web UI will be available.")
            slack_client = None
        else:
            slack_client = SlackClient(slack_bot_token)
            # If BOT_ID wasn't set, we can get it using SLACK_BOT_USER.
            if not bot_id:
                bot_id = WatsonEnv.get_slack_user_id(slack_client)
                if not bot_id:
                    print("Error: Missing BOT_ID or invalid SLACK_BOT_USER.")
                    return None

        # Start Watson Online Store app.
        watsononlinestore = WatsonOnlineStore(bot_id,
                                              slack_client,
                                              conversation_client,
                                              discovery_client,
                                              cloudant_online_store)
        return watsononlinestore


if __name__ == "__main__":
    metrics_tracker_client.track()

    watsononlinestore = WatsonEnv.get_watson_online_store()

    if watsononlinestore:
        watsononlinestore.run()
