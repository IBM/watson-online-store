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

from cloudant.client import Cloudant
from dotenv import load_dotenv
from slackclient import SlackClient
from ibm_watson import AssistantV1
from ibm_watson import DiscoveryV1
from ibm_cloud_sdk_core import get_authenticator_from_environment

from watsononlinestore.database.cloudant_online_store import \
    CloudantOnlineStore
from watsononlinestore.watson_online_store import WatsonOnlineStore


class WatsonEnv:

    def __init__(self):
        pass

    @staticmethod
    def get_vcap_credentials(vcap_env, service):
        if service in vcap_env:
            vcap_instance_list = vcap_env[service]
            if isinstance(vcap_instance_list, list):
                first = vcap_instance_list[0]
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
        cloudant_account = os.environ.get("CLOUDANT_USERNAME")
        cloudant_iam_apikey = os.environ.get("CLOUDANT_IAM_APIKEY")
        cloudant_db_name = os.environ.get(
            "CLOUDANT_DB_NAME") or 'watson_online_store'
        discovery_url = os.environ.get('DISCOVERY_URL')

        # If the CLOUDANT_USERNAME env var was not set then use
        # VCAP_SERVICES like a WatsonService would.
        if not cloudant_iam_apikey:
            vcap_services = os.environ.get("VCAP_SERVICES")
            vcap_env = json.loads(vcap_services) if vcap_services else None
            if vcap_env:
                cloudant_creds = WatsonEnv.get_vcap_credentials(
                    vcap_env, 'cloudantNoSQLDB')
                if cloudant_creds:
                    if 'apikey' in cloudant_creds:
                        cloudant_iam_apikey = cloudant_creds['apikey']
                    if 'username' in cloudant_creds:
                        cloudant_account = cloudant_creds['username']

        # Instantiate Watson Assistant client.
        # - only give a url if we have one (don't override the default)
        assistant_client = AssistantV1(
            version='2018-09-20',
        )
        # Instantiate Cloudant DB.
        cloudant_online_store = CloudantOnlineStore(
            Cloudant.iam(
                cloudant_account,
                cloudant_iam_apikey,
                connect=True
            ),
            cloudant_db_name
        )

        # Instantiate Watson Discovery client.
        # - only give a url if we have one (don't override the default)
        discovery_client = DiscoveryV1(
            version='2019-11-22',
        )
        discovery_client.set_service_url(discovery_url)
        print(discovery_url)
        discovery_client.set_disable_ssl_verification(True)

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
                                              assistant_client,
                                              discovery_client,
                                              cloudant_online_store)
        return watsononlinestore


if __name__ == "__main__":

    watsononlinestore = WatsonEnv.get_watson_online_store()

    if watsononlinestore:
        watsononlinestore.run()
