[![Deploy to Bluemix](https://bluemix.net/deploy/button.png)](https://bluemix.net/deploy?repository=https://github.com/ibm/watson-online-store)
[![Build Status](https://travis-ci.org/IBM/watson-online-store.svg?branch=master)](https://travis-ci.org/IBM/watson-online-store)

Creating a Retail Chatbot using Watson Conversation, Discovery and Database Services
====================================================================================

How to install and deploy
-------------------------

1. Log into Bluemix or create a Bluemix account

2. Create various Bluemix services
  ![](doc/source/images/create_service.png)

  1. Create a Watson Conversation service
  ![](doc/source/images/create_conversation_service.png)

  2. Create a Watson Discovery service
  ![](doc/source/images/create_discovery_service.png)

  3. Create a Cloudant NoSQL DB service
  ![](doc/source/images/create_cloudant_service.png)

3. Clone the repository: git clone https://github.com/ibm/watson-online-store
  * We’ll be using workspace.json and data/ibm_store_html/

4. Upload workspace.json to Watson Conversation
  ![](doc/source/images/import_conversation_workspace.png)
  ![](doc/source/images/find_conversation_workspace.png)
  * Note the WORKSPACE_ID
      ![](doc/source/images/open_conversation_menu.png)
      ![](doc/source/images/view_conversation_workspace_id.png)

5. Optionally, view the conversation dialog
  ![](doc/source/images/dialog.png)

5. Create a new data collection in Watson Discovery
  ![](doc/source/images/launch_discovery.png)
  ![](doc/source/images/create_discovery.png)
  ![](doc/source/images/name_discovery.png)

6. Add the files from data/ibm_store_html/ to the collection
  ![](doc/source/images/add_data_to_discovery.png)
  ![](doc/source/images/select_files_for_discovery.png)
  ![](doc/source/images/process_discovery.png)
  * Note the DISCOVERY_ENVIRONMENT_ID and DISCOVERY_CONFIGURATION_ID
    ![](doc/source/images/view_discovery_ids.png)

7. Create a slack group (or use an existing one)

8. Go to your slack group’s app settings (https://wjd-test.slack.com/apps/manage) and add a new bot:
  ![](doc/source/images/manage_slack_settings.png)

  * Give the bot a cool name
    ![](doc/source/images/name_bot.png)

  * Note the TOKEN that is generated
    ![](doc/source/images/view_bot_token.png)

9. Run /invite <botame> in the channel to invite the bot
   ![](doc/source/images/invite_bot.png)

10. Copy the sample env to .env and edit the file with the IDs we noted earlier
  * $ cp env.sample .env

11. Run the app locally, in a terminal run:
  * $ python run.py
  * If no problems: “Watson Online Store bot is connected and running!”

Sample .env
-----------

::

    # Watson conversation
    CONVERSATION_USERNAME=e6ca86f1-302a-4803-b408-7949c7abaa1a
    CONVERSATION_PASSWORD=PQ6fjelpPyPx
    WORKSPACE_ID=19849a01-19e4-47ad-bg3f-6cafe376aeed

    # Cloudant DB
    CLOUDANT_USERNAME="715ac810-921f-4290-92fc-061642ee4b3a-bluemix"
    CLOUDANT_PASSWORD="25fdf0c1411d2584b693c9f8aeda9b260b23656ec32c0da0839ed1cf7c2bd594"
    CLOUDANT_DB_NAME="cloudant_online_store"
    CLOUDANT_URL="https://715ac810-921f-4290-92fc-061642ee4b3a-bluemix.cloudant.com"

    # Watson Discovery
    DISCOVERY_USERNAME=03c25743-4728-448e-b3ed-3b198e6edd65
    DISCOVERY_PASSWORD=4LDhpX27q7QZ
    DISCOVERY_ENVIRONMENT_ID=a2e0e223-aec9-458e-95b5-d4d618e1ae6d
    DISCOVERY_COLLECTION_ID=d06e9ddf-7c27-4dce-b80f-dca8768a72d8

    # Slack
    SLACK_BOT_TOKEN=xoxb-cbe837f60865-bjgftpFM6tnJXTvZzIw8Ihui
    SLACK_BOT_NAME=hal

Sample output
-------------

*this is placeholder text until we get screenshots or a gif*

Start a conversation with your bot by searching for an item::

    @wosbot I’d like to search for a mug

Add an item to your cart::

    @wosbot I’d like to buy item 1

Remove an item from your cart::

    @wosbot I’d like remove item 4
