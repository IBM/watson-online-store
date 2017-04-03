[![Build Status](https://travis-ci.org/IBM/watson-online-store.svg?branch=master)](https://travis-ci.org/IBM/watson-online-store)

# Creating a Retail Chatbot using Watson Conversation, Discovery and Database Services

In this developer journey we will create a Watson Conversation based chatbot
that allows a user to: 1) find items to purchase using Watson Discovery, and
2) add and remove items from their cart by updating a Cloudant NoSQL Database.

When the reader has completed this journey, they will understand how to:

* Create a chatbot dialog with Watson Conversation
* Dynamically store and update a Cloudant NoSQL database based on chatbot results
* Seed data into Watson Discovery and leverage its natural language capabilities
* Manage and customize a Slack group to add a chatbot

![Flow](doc/source/images/architecture.png)

## Included Components
- Bluemix Watson Conversation
- Bluemix Watson Discovery
- Bluemix Cloudant NoSQL DB
- Slack
- Python

# Steps

**NOTE:** Perform steps 1-6 **OR** click the **Deploy to Bluemix** button and jump to step 5.

[![Deploy to Bluemix](https://bluemix.net/deploy/button.png)](https://bluemix.net/deploy?repository=https://github.com/ibm/watson-online-store)

1. [Clone the repo](#1-clone-the-repo)
2. [Create Bluemix services](#2-create-bluemix-services)
3. [Configure Watson Conversation](#3-configure-watson-conversation)
4. [Configure Watson Discovery](#4-configure-watson-discovery)
5. [Configure Slack](#5-configure-slack)
6. [Run the application](#6-run-the-application)

## 1. Clone the repo

Clone the `watson-online-store` locally. In a terminal, run:

  `$ git clone https://github.com/ibm/watson-online-store`

We’ll be using the file [`data/workspace.json`](data/workspace.json) and the folder
[`data/ibm_store_html/`](data/ibm_store_html)

## 2. Create Bluemix services

Create the following services:

  * [**Watson Conversation**](https://console.ng.bluemix.net/catalog/services/conversation)
  * [**Watson Discovery**](https://console.ng.bluemix.net/catalog/services/discovery)
  * [**Cloudant NoSQL DB**](https://console.ng.bluemix.net/catalog/services/cloudant-nosql-db/)

## 3. Configure Watson Conversation

Launch the **Watson Conversation** tool. Use the **import** icon button on the right

<p align="center">
  <img width="400" height="55" src="doc/source/images/import_conversation_workspace.png">
</p>

Find the local version of [`data/workspace.json`](data/workspace.json) and select
**Import**. Find the **Workspace ID** by clicking on the context menu of the new
workspace and select **View details**. Save this ID for later.

<p align="center">
  <img width="400" height="250" src="doc/source/images/open_conversation_menu.png">
</p>

*Optionally*, to view the conversation dialog select the workspace and choose the
**Dialog** tab, here's a snippet of the dialog:

![](doc/source/images/dialog.png)

## 4. Configure Watson Discovery

Launch the **Watson Conversation** tool. Create a **new data collection** and give the data
collection a unique name.

<p align="center">
  <img width="400" height="300" src="doc/source/images/name_discovery.png">
</p>

Seed the content by selecting **Add data to this collection** in the dialog,
choose the HTML files under [`data/ibm_store_html/`](data/ibm_store_html). When
completed, save the **environment_id** and **collection_id**.

<p align="center">
  <img width="800" height="225" src="doc/source/images/view_discovery_ids.png">
</p>

## 5. Configure Slack

[Create a slack group](https://slack.com/create) or use an existing one if you
have sufficient authorization. (Refer to [Slack's how-to](https://get.slack.help/hc/en-us/articles/206845317-Create-a-Slack-team)
on creating new groups.) To add a new bot, go to the Slack group’s application settings
by navigating to `https://<slack_group>.slack.com/apps/manage` and selecting the
**Custom Integrations** menu on the left.

![](doc/source/images/manage_slack_settings.png)

Give the bot a fun name. Once created save the **API Token** that is generated
![](doc/source/images/view_bot_token.png)

Run `/invite <botame>` in a channel to invite the bot, or message it directly.

<p align="center">
  <img width="400" height="125" src="doc/source/images/invite_bot.png">
</p>

## 6. Run the application

### If you used the Deploy to Bluemix button...

If you used ``Deploy to Bluemix``, most of the setup is automatic, but not
quite all of it. We have to update a few environment variables.

In the Bluemix dashboard find the App that was created. Click on ``Runtime`` on the menu and navigate to the ``Environment variables`` tab.

![](doc/source/images/env_vars.png)

Update the three environment variables:

  * Set ``SLACK_BOT_TOKEN`` to the token you saved in Step 5
  * Set ``SLACK_BOT_USER`` to the name of your bot
  * It's probably OK to leave ``CLOUDANT_DB_NAME`` set to ``watson-online-store``

Save the new values and restart the application, watch the logs for errors.

### If you decided to run the app locally...

Copy the [`env.sample`](env.sample) to `.env`, edit it with the necessary IDs
and run the application.

The `USERNAME`, `PASSWORD`, and `URL` settings for each service can be obtained
from the `Service Credentials` tab in BlueMix. The other settings were collected
during the earlier setup steps.

```
$ cp env.sample .env
### edit .env
$ python run.py
```

# Sample output

Start a conversation with your bot:

![](doc/source/images/convo_init.png)

Add an item to your cart:

![](doc/source/images/convo_add.png)

# Troubleshooting

* Help! I'm seeing errors in my log

This is expected during the first run. The app tries to start before the Discovery
service is fully created. Allow a minute or two to pass, the following message
should appear:

``Watson Online Store bot is connected and running!``

* Setting environment variables for a local run

> NOTE: This only needs to be set if the application is running locally.

The credentials for Bluemix services (Conversation, Cloudant, and Discovery), can
be found in the ``Services`` menu in Bluemix, and selecting the ``Service Credentials``
option.

```
# Watson conversation
CONVERSATION_USERNAME=<add_conversation_username>
CONVERSATION_PASSWORD=<add_conversation_password>
WORKSPACE_ID=<add_conversation_workspace>

# Cloudant DB
CLOUDANT_USERNAME=<add_cloudant_username>
CLOUDANT_PASSWORD=<add_cloudant_password>
CLOUDANT_DB_NAME=watson_online_store
CLOUDANT_URL=<add_cloudant_url>

# Watson Discovery
DISCOVERY_USERNAME=<add_discovery_username>
DISCOVERY_PASSWORD=<add_discovery_password>
DISCOVERY_ENVIRONMENT_ID=<add_discovery_environment>
DISCOVERY_COLLECTION_ID=<add_discovery_collection>

# Slack
SLACK_BOT_TOKEN=<add_slack_bot_token>
SLACK_BOT_USER=wos
```

# License

[Apache 2.0](LICENSE)
