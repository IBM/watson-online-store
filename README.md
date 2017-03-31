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

Perform steps 1-6 OR perform step 1 then click the **Deploy to Bluemix** button and jump to step 4.

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

### Deployed to Bluemix

If you used ``Deploy to Bluemix``, most of the setup is automatic, but not
quite all of it.

1. Add SLACK_BOT_TOKEN
* Use your Bluemix dashboard and click on the App. that was created.
* Click on ``Runtime`` on the left.
* Click on the ``Environment variables`` tab.
* Scroll-down to see 3 environment variables:
    * Set SLACK_BOT_TOKEN to the token you saved during Slack setup.
    * Set SLACK_BOT_USER to the name of your bot.
    * CLOUDANT_DB_NAME is probably OK to leave as watson-online-store.
* Hit ``Save``.
* Hit the restart icon and watch the logs for errors.

2. There currently a work-around before the Discovery collection can be
automatically created.
* Use your Bluemix dashboard and click on the wos-discovery-service.
* Click on the ``Service credentials`` tab.
* If there are no service credentials, click ``New credential`` and ``Add``.
* Click on the ``Manage`` tab and click ``Launch Tool``.
* Click on the gear icon. If it prompts you to create a Private Storage
Environment, then create one.

Restart your App. and start chatting with your bot.

### Run local
Copy the [`env.sample`](env.sample) to `.env`, edit it with the necessary IDs and run the application.

```
$ cp env.sample .env
$ # edit .env
$ python run.py
```

# Sample output

Start a conversation with your bot:

![](doc/source/images/convo_init.png)

Add an item to your cart:

![](doc/source/images/convo_add.png)

# Troubleshooting

* Sample .env to use:

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
  SLACK_BOT_USER=wos
```

# License

[Apache 2.0](LICENSE)
