## Developer Tips

This page contains helpful tips and greater detail about specific portions of our journey.


### How to create HTML files for Watson Discovery

The IBM Watson Discovery service is a cognitive search and content analytics engine that identifies
patterns and trends hidden in unstructured data.

The input to Watson Discovery can be in the form of:
* HTML files
* Word documents
* JSON files
* PDF files

For our retail chatbot journey, we have chosen to seed Discovery with HTML product pages found on the
[IBM Logo Store](http://logostore-globalid.us/) webiste.

To keep our journey simple, we selected 15 items from the web store, and the items we chose were limited
to some shirts, caps, and mugs. In order to get these pages into the right format for Discovery, we wrote
a simple Python script, [`get_data_ibm_store.py`](tools/get_data_ibm_store.py), that read in each of the
URL pages, added some simple descriptive tags to the HTML, and then wrote each of them back out to an HTML
file. Generated HTML files can be found in our [`data directory`](data/ibm_store_html).

This example of interacting with the Watson Discovery service is simply an introduction, detailing how a
user can deploy, configure and interact with it. Look for future journeys where we will dive deeper into
the full power and capabilities of the Watson Discovery service.
