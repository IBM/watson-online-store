import urllib

# Grab select items from IBM Logo Store
items = []

# Shirts
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=206347",
    "title": "Applique Crew Sweatshirt",
    "category": "shirt/shirts/sweatshirts"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=131644",
    "title": "Be Essential T-Shirt",
    "category": "shirt/shirts/tees"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=131636",
    "title": "Eye-Bee-M Sweatshirt",
    "category": "shirt/shirts/sweatshirts"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=131634",
    "title": "Eye-Bee-M T-Shirt",
    "category": "shirt/shirts/tees"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=131622",
    "title": "Fairway and Greene Polo Shirt",
    "category": "shirt/shirts/polos"
})

# Hats
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=131628",
    "title": "Eye-Bee-M Cap",
    "category": "cap/caps/hat/hats"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=211897",
    "title": "Performance Cap",
    "category": "cap/caps/hat/hats"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=132258",
    "title": "Quadrant Logo Cap",
    "category": "cap/caps/hat/hats"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=131626",
    "title": "THINK Cap",
    "category": "cap/caps/hat/hats"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=122465",
    "title": "PureSystems Cap",
    "category": "cap/caps/hat/hats"
})

# Mugs
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=190450",
    "title": "11oz Mug-Watson Health",
    "category": "mug/mugs/cup/cups"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=176572",
    "title": "IBM C-Handle Mug 11oz.",
    "category": "mug/mugs/cup/cups"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=190447",
    "title": "Wason 11oz. C-Handle Mug",
    "category": "mug/mugs/cup/cups"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=132294",
    "title": "Be Essential Mug",
    "category": "mug/mugs/cup/cups"
})
items.append({
    "url": "http://www.logostore-globalid.us/ProductDetail.aspx?pid=132254",
    "title": "THINK Mug",
    "category": "mug/mugs/cup/cups"
})

# Build HTML files as input to Watson Discovery Service
counter = 1
for item in items:
    url = item['url']
    title = item['title']
    category = item['category']
    print "Getting search results for: " + url

    # Add product title and category to help seed Watson results
    resp = urllib.urlopen(url).read()
    resp = resp.replace("IBM Logostore", "IBM Logostore\nProduct:" + title +
                        "\nCategory:" + category + "\n")
    # Remove "upsell" tab which contains references to other products
    sidx = resp.find('<div id="tabs" class="Upselltabs">')
    eidx = resp.find('<script type="text/javascript">', sidx, len(resp))
    resp1 = resp[:sidx]
    resp2 = resp[eidx:]
    resp = resp1 + resp2

    file_object = open(str(counter) + '.html', 'w')
    print "      title = " + title
    file_object.write(resp)
    file_object.close()

    counter += 1
