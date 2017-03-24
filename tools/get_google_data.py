import urllib
import json

# Assign keys - the following are for an example only
# Google custom search engine api key
cs_key = "AIzaSyAD4c_JwlXRhtAFcA0rcGpTkBPT1Uc3iEw"
# Custom search engine ID
cx_id = "015276035841364447158:qfhlzj7z0gk"

# Use google custom search engine to perform searches on items for our store
# get 20 results per item.

# The google custom search engine setup is where you specify which web sites
# to include in your search. For this app, the site is "amazon.com".

# WARNING - the google cse base version has limits on how many searches you
# can do. You will have to create a new instance of you reach your max.

# Search for pants, shirts, and shoes
urls = [
    "https://www.googleapis.com/customsearch/v1?key=" + cs_key + "&cx=" +
    cx_id + "&q=%27pants%27",
    "https://www.googleapis.com/customsearch/v1?key=" + cs_key + "&cx=" +
    cx_id + "&q=%27pants%27&start=11",
    "https://www.googleapis.com/customsearch/v1?key=" + cs_key + "&cx=" +
    cx_id + "&q=%27shirts%27",
    "https://www.googleapis.com/customsearch/v1?key=" + cs_key + "&cx=" +
    cx_id + "&q=%27shirts%27&start=11",
    "https://www.googleapis.com/customsearch/v1?key=" + cs_key + "&cx=" +
    cx_id + "&q=%27nike%20air%20max%27",
    "https://www.googleapis.com/customsearch/v1?key=" + cs_key + "&cx=" +
    cx_id + "&q=%27nike%20air%20max%27&start=11"
]

# Convert results into json
jsonResps = []
for url in urls:
    print("Getting search results for: " + url)
    resp = urllib.urlopen(url).read()
    print("Converting to JSON")
    jsonResp = json.loads(resp)
    jsonResps.append(jsonResp)
    print("Done")

results = []
counter = 0

# Prccess each result
for resp in jsonResps:
    if 'items' in resp:
        items = resp['items']
        for item in items:
            link = item['link']
            # Only process links to product web pages (not lists)
            if '/dp/' in link:
                print("Processing: " + link)
                counter += 1
                html = urllib.urlopen(link).read()
                file_object = open(str(counter) + '.html', 'w')
                # Store the page url at the bottom of the file
                html = html + "<a href=" + link.encode('utf8') + ">"
                file_object.write(html)
                file_object.close()
