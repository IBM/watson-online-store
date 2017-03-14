from cloudant.query import Query


class CloudantOnlineStore(object):

    def __init__(self, client, db_name):
        """
        Creates a new instance of CloudantOnlineStore.
        Parameters
        ----------
        client - The instance of cloudant client to connect to
        db_name - The name of the database to use
        """
        self.client = client
        self.db_name = db_name

    def init(self):
        """
        Creates and initializes the database.
        """
        try:
            self.client.connect()
            print('Getting database...')
            if self.db_name not in self.client.all_dbs():
                print('Creating database {}...'.format(self.db_name))
                self.client.create_database(self.db_name)
            else:
                print('Database {} exists.'.format(self.db_name))
        finally:
            self.client.disconnect()

    # User

    def add_customer_obj(self, customer):
        """
        Adds a new customer to Cloudant if a customer with the specified ID
        does not already exist.

        Parameters
        ----------
        email - The ID of the customer (typically the email address)
        first_name - First name of the customer
        last_name - Last name of the customer
        purchase_history - Array of purchase_id
        favorites - Array of strings for favorite purchases
        """
        customer_doc = {
            'type': 'customer',
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'shopping_cart': customer.shopping_cart,
            'logged_in': customer.logged_in
        }
        return self.add_doc_if_not_exists(customer_doc, 'email')

    def find_customer(self, customer_str):
        """
        Finds the customer based on the specified customerStr in Cloudant.
        Parameters
        ----------
        customer_str - The customer specified by the user
        """
        return self.find_doc('customer', 'email', customer_str)

    def list_shopping_cart(self, customer_str):
        """
        Gets shopping cart for customer.
        Parameters
        ----------
        customer_str - The customer specified by the user
        Returns - shopping cart as a list
        """
        doc = self.find_customer(customer_str)
        if doc:
            return doc['shopping_cart']
        return doc  # None
        
    def add_to_shopping_cart(self, customer_str, item):
        """
        Adds item to shopping cart for customer.
        Parameters
        ----------
        customer_str - The customer specified by the user
        item - string representing item to add
        """
        user_doc = self.find_doc(
            'customer', 'email', customer_str)
        try:
            self.client.connect()
            current_doc = self.client[self.db_name][user_doc['_id']]
            if current_doc:
                current_doc['shopping_cart'].append(item)
                current_doc.save()
                return 1
            return 0

        finally:
            self.client.disconnect()

    def delete_item_shopping_cart(self, customer_str, item):
        """
        Deletes item from shopping cart for customer.
        Parameters
        ----------
        customer_str - The customer specified by the user
        item - string representing item to delete 
        """
        user_doc = self.find_doc(
            'customer', 'email', customer_str)
        try:
            self.client.connect()
            current_doc = self.client[self.db_name][user_doc['_id']]
            if current_doc:
                if item in current_doc['shopping_cart']:
                    current_doc['shopping_cart'].remove(item)
                    current_doc.save()
                    return 1
            return 0

        finally:
            self.client.disconnect()

    # Cloudant Helper Methods

    def find_doc(self, doc_type, property_name, property_value):
        """
        Finds a doc based on the specified doc_type, property_name, and
        property_value.

        Parameters
        ----------
        doc_type - The type value of the document stored in Cloudant
        property_name - The property name to search for
        property_value - The value that should match for the specified
                         property name
        """
        try:
            self.client.connect()
            db = self.client[self.db_name]
            selector = {
                '_id': {'$gt': 0},
                'type': doc_type,
                property_name: property_value
            }
            query = Query(db, selector=selector)
            for doc in query()['docs']:
                return doc
            return None
        finally:
            self.client.disconnect()

    def add_doc_if_not_exists(self, doc, unique_property_name):
        """
        Adds a new doc to Cloudant if a doc with the same value for
        unique_property_name does not exist.

        Parameters
        ----------
        doc - The document to add
        unique_property_name - The name of the property used to search for an
                               existing document (the value will be extracted
                               from the doc provided)
        """
        doc_type = doc['type']
        property_value = doc[unique_property_name]
        existing_doc = self.find_doc(
            doc_type, unique_property_name, property_value)
        if existing_doc is not None:
            print('Returning {} doc where {}={}'.format(
                doc_type, unique_property_name, property_value))
            return existing_doc
        else:
            print('Creating {} doc where {}={}'.format(
                doc_type, unique_property_name, property_value))
            try:
                self.client.connect()
                db = self.client[self.db_name]
                return db.create_document(doc)
            finally:
                self.client.disconnect()
