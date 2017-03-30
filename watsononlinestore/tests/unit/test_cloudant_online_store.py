import unittest

import ddt
import mock

from watsononlinestore.database import cloudant_online_store
from watsononlinestore.watson_online_store import OnlineStoreCustomer

CUSTOMER_DOC = {
            'type': 'customer',
            'email': 'scott@gmail.com',
            'first_name': 'Scott',
            'last_name': 'Jones',
            'shopping_cart': ['foo', 'bar'],
            '_id': {'shopping_car': ['foo', 'bar']}
        }


class MockQuery(mock.MagicMock):
    def __init__(self, db, selector=None):
        pass

    def __call__(self):

        ret = {
            'docs': [{
                     'type': 'customer',
                     'email': 'scott@gmail.com',
                     'first_name': 'Scott',
                     'last_name': 'Jones',
                     'shopping_cart': ['foo', 'bar'],
                     '_id': {'shopping_car': ['foo', 'bar']}
                     }]
        }
        return ret


@ddt.ddt
class COSTestCase(unittest.TestCase):

    def setUp(self):
        self.client = mock.MagicMock()
        self.db_name = "cloudant_online_store"

        self.cloudantDB = cloudant_online_store.CloudantOnlineStore(
            self.client,
            self.db_name)
        cloudant_online_store.Query = MockQuery

    def test_init(self):

        self.cloudantDB.init()

    @ddt.data(('moe@gmail.com', 'Moe', 'Howard', ['item1', 'item2']),
              ('curly@gmail.com', 'Curly', 'Howard', []))
    def test_add_customer_obj(self, cust):
        customer = OnlineStoreCustomer(cust)

        self.cloudantDB.create_document = mock.Mock()
        self.cloudantDB.add_customer_obj(customer)

    def test_find_customer(self):
        expected = CUSTOMER_DOC
        actual = self.cloudantDB.find_customer('scott@gmail.com')
        self.assertEqual(expected, actual)

    def test_list_shopping_cart(self):
        expected = ['foo', 'bar']
        actual = self.cloudantDB.list_shopping_cart('scott@gmail.com')
        self.assertEqual(expected, actual)

    def test_add_to_shopping_cart(self):
        self.cloudantDB.add_to_shopping_cart('scott@gmail.com', 'dog')
        assert MockQuery.called
        assert self.client.connect.called
        assert self.client.disconnect.called

    def test_delete_item_shopping_cart(self):
        self.cloudantDB.delete_item_shopping_cart('scott@gmail.com', 'dog')
        assert MockQuery.called
        assert self.client.connect.called
        assert self.client.disconnect.called
