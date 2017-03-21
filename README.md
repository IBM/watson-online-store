[![Deploy to Bluemix](https://bluemix.net/deploy/button.png)](https://bluemix.net/deploy?repository=https://github.com/ibm/watson-online-store)

[![Build Status](https://travis-ci.org/IBM/watson-online-store.svg?branch=master)](https://travis-ci.org/IBM/watson-online-store)

Creating a Retail Chatbot using Watson Conversation, Discovery and Database Services
====================================================================================

In this developer journey we will create a Watson Conversation based chatbot
that allows a user to: 1) find items to purchase using Watson Discovery, and
2) add and remove items from their cart by updating a Cloudant NoSQL Database.

When the reader has completed this journey, they will understand how to:

* Create a chatbot dialog with Watson Conversation
* Dynamically store and update a Cloudant NoSQL database based on chatbot results
* Seed data into Watson Discovery and leverage its natural language capabilities
* Manage and customize a Slack group to add a chatbot


Install and deploy
------------------

1. Log into Bluemix or create a Bluemix account

2. Clone [the watson-online-store repository](https://github.com/ibm/watson-online-store) locally

  * In a terminal, run: `$ git clone https://github.com/ibm/watson-online-store`

  * We’ll be using the file `workspace.json` and the folder `data/ibm_store_html/`

3. Create various Bluemix services

  <div style="text-align:center"><img src="doc/source/images/create_service.png" width="50%" align="middle"></div>

  * Create a **Watson Conversation** service

  * Click on **Service Credentials** and save the **username** and **password**

    <img src="doc/source/images/create_conversation_service.png">

  * Create a **Watson Discovery** service

  * Click on **Service Credentials** and save the **username** and **password**

    <img src="doc/source/images/create_discovery_service.png">

  * Create a **Cloudant NoSQL DB** service

  * Click on **Service Credentials** and save the **username**, **password**, and **url**

    <img src="doc/source/images/create_cloudant_service.png">

4. Configure **Watson Conversation**

  * Launch the **Watson Conversation** tool

  <img src="doc/source/images/launch_conversation.png">

  * Use the **import** icon button on the right

  <div style="text-align:center"><img src="doc/source/images/import_conversation_workspace.png" width="50%"></div>

  * Find the local version of `workspace.json` and select **Import**

  <div style="text-align:center"><img src="doc/source/images/find_conversation_workspace.png" width="75%"></div>

  * Find the **Workspace ID** by clicking on the context menu of the new
  workspace, and selecting **View details**, save this ID

  <div style="text-align:center"><img src="doc/source/images/open_conversation_menu.png" width="75%"></div>

  <div style="text-align:center"><img src="doc/source/images/view_conversation_workspace_id.png" width="75%"></div>

  * *Optionally*, to view the conversation dialog select the workspace and
  choose the **Dialog** tab, here's a snippet of the dialog:

  <img src="doc/source/images/dialog.png">

5. Configure **Watson Discovery**

  * Launch the **Watson Conversation** tool
<img src="doc/source/images/launch_discovery.png">

  * Create a new data collection

  <div style="text-align:center"><img src="doc/source/images/create_discovery.png" width="50%"></div>

  * Give the data collection a unique name

  <div style="text-align:center"><img src="doc/source/images/name_discovery.png" width="50%"></div>

  * Seed the content by selecting dialog in **Add data to this collection**

  <div style="text-align:center"><img src="doc/source/images/add_data_to_discovery.png" width="50%"></div>

  * Select the HTML files under `data/ibm_store_html/`

  <img src="doc/source/images/select_files_for_discovery.png">

  * When completed, save the **environment_id** and **configuration_id**

  <div style="text-align:center"><img src="doc/source/images/view_discovery_ids.png" width="75%">

6. Configure **Slack**

  * [Create a slack group](https://slack.com/create), or use an existing one
    if you have sufficient authorization. Refer to [Slack's how-to]
    (https://get.slack.help/hc/en-us/articles/206845317-Create-a-Slack-team) on creating new groups.

  * Go to the Slack group’s application settings and add a new bot. The
    application settings can be accessed by navigating to
    `https://<slack_group>.slack.com/apps/manage`. To add a bot, select
    the **Custom Integrations** menu on the left.

  <img src="doc/source/images/manage_slack_settings.png">

  * Give the bot a fun name and select **Add bot integration**

  <img src="doc/source/images/name_bot.png">

  * Once created save the **API Token** that is generated

  <img src="doc/source/images/view_bot_token.png">

  * Run `/invite <botame>` in a channel to invite the bot, or message it directly.

  <div style="text-align:center"><img src="doc/source/images/invite_bot.png" width="50%"></div>

7. Run the application locally

  * Copy `env.sample` to `.env` by running: `$ cp env.sample .env`
  * Edit `.env` with the IDs we noted earlier
  * Run the application by running: `$ python run.py`
  * If there are no issues the only output you'll see is:
    *Watson Online Store bot is connected and running!*

Sample .env
-----------

```
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
```

Sample output
-------------

*this is placeholder text until we get screenshots or a gif*

Start a conversation with your bot by searching for an item:

  `@wosbot I’d like to search for a mug`

Add an item to your cart:

  `@wosbot I’d like to buy item 1`

Remove an item from your cart:

  `@wosbot I’d like remove item 4`
