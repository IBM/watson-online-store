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

import logging
from cloudant.query import Query

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)


class CloudantOnlineStore(object):

    def __init__(self, client, db_name):
        """Creates a new instance of CloudantOnlineStore.

        :param Cloudant client: instance of cloudant client to connect to
        :param str db_name: name of the database to use
        """
        self.client = client
        self.db_name = db_name

    def init(self):
        """Creates and initializes the database.
        """
        try:
            self.client.connect()
            LOG.info('Getting database...')
            if self.db_name not in self.client.all_dbs():
                LOG.info('Creating database {}...'.format(self.db_name))
                self.client.create_database(self.db_name)
            else:
                LOG.info('Database {} exists.'.format(self.db_name))
        finally:
            self.client.disconnect()

    # User

    def add_customer_obj(self, customer):
        """Adds a new customer to DB unless they already exist.

        :param str email: ID of the customer (email address)
        :param str first_name: first name of the customer
        :param str last_name: last name of the customer
        :param list shopping_cart: items in customer's shopping cart

        """
        customer_doc = {
            'type': 'customer',
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'shopping_cart': customer.shopping_cart
        }

        self.add_doc_if_not_exists(customer_doc, 'email')

    def find_customer(self, customer_str):
        """Finds the customer based on the specified customerStr in Cloudant.

        :param str customer_str: customer (email addr)

        :returns: document with customer info
        :rtype: dict
        """
        return self.find_doc('customer', 'email', customer_str)

    def list_shopping_cart(self, customer_str):
        """Get shopping cart info for a given customer.

        :param str customer_str: customer (email addr)

        :returns: shopping cart
        :rtype: list
        """
        doc = self.find_customer(customer_str)
        if doc:
            return doc['shopping_cart']
        return doc  # None

    def add_to_shopping_cart(self, customer_str, item):
        """Adds item to shopping cart for customer.

        :param str customer_str: customer (email addr)
        :param str item: item to add
        """
        user_doc = self.find_doc(
            'customer', 'email', customer_str)
        try:
            self.client.connect()
            current_doc = self.client[self.db_name][user_doc['_id']]
            if current_doc:
                current_doc['shopping_cart'].append(item)
                current_doc.save()
        except Exception:
            LOG.exception("Cloudant DB exception:")

        finally:
            self.client.disconnect()

    def delete_item_shopping_cart(self, customer_str, item):
        """Deletes item from shopping cart for customer.
        :param str customer_str: The customer specified by the user
        :param str item: item to delete
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
        except Exception:
            LOG.exception("Cloudant DB exception:")

        finally:
            self.client.disconnect()

    # Cloudant Helper Methods

    def find_doc(self, doc_type, property_name, property_value):
        """Finds a doc in Cloudant DB

        :param str doc_type: type value of the document stored in Cloudant
        :param str property_name: property name to search for
        :param str property_value: value that should match for the specified
                                   property name

        :returns: doc from query or None
        :rtype: dict, None
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
        except Exception:
            LOG.exception("Cloudant DB exception:")
        finally:
            self.client.disconnect()

    def add_doc_if_not_exists(self, doc, unique_property_name):
        """Adds a new doc to Cloudant if a doc with the same value for
        unique_property_name does not exist.

        :param dict doc: document to add
        :param str unique_property_name:name of the property used to search for
                               an existing document (value will be extracted
                               from the doc provided)
        """
        doc_type = doc['type']
        property_value = doc[unique_property_name]
        existing_doc = self.find_doc(
            doc_type, unique_property_name, property_value)
        if existing_doc is not None:
            LOG.debug('Existing {} doc where {}={}:\n{}'.format(
                doc_type, unique_property_name, property_value, existing_doc))
        else:
            LOG.debug('Creating {} doc where {}={}'.format(
                doc_type, unique_property_name, property_value))
            try:
                self.client.connect()
                db = self.client[self.db_name]
                db.create_document(doc)
            except Exception:
                LOG.exception("Cloudant DB exception:")
            finally:
                self.client.disconnect()


    def make_cloudant_url_compatible_with_py3(url):
        """ if the url is in the pattern https://username:password@*-bluemix.cloudant.com
        then strip out the username:password to make it py3.6 friendly
        ex: https://*-bluemix.cloudant.com
        """
        newUrl=''
        if url and len(url) > 0:
            urlFragments = url.split("@")
            if len(urlFragments) == 2:
                newUrl = 'https://' + urlFragments.pop()
                LOG.info("New cloudant URL: {}".format(newUrl))
            else:
                LOG.exception("Malformed Cloudant URL")        
        return newUrl

