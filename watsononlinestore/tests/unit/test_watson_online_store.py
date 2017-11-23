import unittest

import ddt
import mock

from watsononlinestore import watson_online_store


@ddt.ddt
class WOSTestCase(unittest.TestCase):

    def setUp(self):
        mock.Mock(watson_online_store.os.environ, return_value={})
        self.slack_client = mock.Mock()
        self.conv_client = mock.Mock()
        self.fake_workspace_id = 'fake workspace id'
        self.conv_client.list_workspaces.return_value = {
            'workspaces': [{'workspace_id': self.fake_workspace_id,
                            'name': 'watson-online-store'}]}
        self.cloudant_store = mock.Mock()
        self.discovery_client = mock.Mock()
        self.fake_data_source = 'IBM_STORE'
        self.fake_environment_id = 'fake env id'
        self.fake_collection_id = "fake collection id"
        self.discovery_client.get_environment.return_value = {
            'environment_id': self.fake_environment_id}
        self.discovery_client.list_environments.return_value = {
            'environments': [{'environment_id': self.fake_environment_id,
                              'read_only': False,
                              'name': 'ibm-logo-store'}]}
        self.discovery_client.get_collection.return_value = {
            'collection_id': self.fake_collection_id}
        self.discovery_client.list_collections.return_value = {
            'collections': [{'collection_id': self.fake_collection_id,
                             'name': 'ibm-logo-store'}]}

        self.wos = watson_online_store.WatsonOnlineStore(
            'UBOTID',
            self.slack_client,
            self.conv_client,
            self.discovery_client,
            self.cloudant_store)

        self.sender = watson_online_store.SlackSender(
            self.slack_client, 'sender-channel')

    def test_0(self):

        fake_channel = "fake channel"
        sender = watson_online_store.SlackSender(
            self.slack_client, fake_channel)
        fake_response = "this is a fake response"

        self.conv_client.message.return_value = {
            'context': {'send_no_input': 'no'},
            'output': {'text': [fake_response]},
        }

        self.wos.handle_message("this is a test", sender)

        self.conv_client.assert_has_calls([
            mock.call.message(context={},
                              input={'text': 'this is a test'},
                              workspace_id=mock.ANY)
        ])
        self.slack_client.api_call.assert_has_calls([
            mock.call(
                'chat.postMessage',
                as_user=True,
                channel=fake_channel,
                text=fake_response + '\n')
        ])

    @ddt.data(None, "", False)
    def test_init_customer_no_user_id(self, no_user_id):

        self.assertRaises(
            AssertionError, self.wos.init_customer, 'ignore', no_user_id)

    def test_init_customer_slack_fail(self):
        self.slack_client.api_call = mock.Mock(side_effect=Exception("Boom"))
        user = "testuser"

        self.wos.init_customer(self.sender, user)

        self.slack_client.api_call.assert_called_once_with(
            'users.info', user=user)

    @ddt.data(None, "", False, {},
              {'ok': False, 'error': 'yes'},
              {'user': {'profile': {'no-email': 'e@mail'}}},
              {'user': {'profile': {'email': None}}},
              {'user': {'profile': {'email': ''}}}
              )
    def test_init_customer_slack_unusable(self, ret):
        self.slack_client.api_call = mock.Mock(return_value=ret)
        user = "testuser"

        self.wos.init_customer(self.sender, user)

        self.slack_client.api_call.assert_called_once_with(
            'users.info', user=user)

    def test_init_customer_slack_user_old(self):
        test_email_addr = 'e@mail'
        self.slack_client.api_call = mock.Mock(return_value={
            'user': {'profile': {'email': test_email_addr}}})
        self.cloudant_store.find_customer = mock.Mock(return_value={
            'email': 'test-email',
            'first_name': 'test-first-name',
            'last_name': 'test-last-name',
        })
        user = "testuser"

        self.wos.init_customer(self.sender, user)

        self.slack_client.api_call.assert_called_once_with(
            'users.info', user=user)
        self.cloudant_store.find_customer.assert_called_once_with(
            test_email_addr)

    def test_init_customer_slack_new(self):
        test_email_addr = 'e@mail'
        self.slack_client.api_call = mock.Mock(
            return_value={'user': {'profile': {'email': test_email_addr,
                                               'first_name': 'first-name',
                                               'last_name': 'last-name',
                                               }}})
        self.cloudant_store.find_customer = mock.Mock(return_value={})
        user = "testuser"

        self.wos.init_customer(self.sender, user)

        self.slack_client.api_call.assert_called_once_with(
            'users.info', user=user)
        self.cloudant_store.find_customer.assert_called_once_with(
            test_email_addr)

    def test_init_customer_slack_no_name(self):
        test_email_addr = 'e@mail'
        self.slack_client.api_call = mock.Mock(
            return_value={'user': {'profile': {'email': test_email_addr,
                                               'first_name': '',
                                               'last_name': '',
                                               }}})
        self.cloudant_store.find_customer = mock.Mock(return_value={})
        user = "testuser"

        self.wos.init_customer(self.sender, user)

        self.slack_client.api_call.assert_called_once_with(
            'users.info', user=user)
        self.cloudant_store.find_customer.assert_called_once_with(
            test_email_addr)

    @ddt.data(
        ([{'text': '<@UBOTID> suFFix', 'channel': 'C', 'user': 'U'}],
         ('suffix', 'C', 'U')),
        ([{'text': 'prefix <@UBOTID> Suffix', 'channel': 'C', 'user': 'U'}],
         ('prefix  suffix', 'C', 'U')),
        ([{'text': 'prefix <@UBOTID> Suffix<@UBOTID>Tail',
           'channel': 'C', 'user': 'U'}],
         ('prefix  suffixtail', 'C', 'U')),
        ([{'text': 'prefix <@UBOTID> suffix', 'channel': 'DXXX', 'user': 'U'}],
         ('prefix  suffix', 'DXXX', 'U')),
        ([{'text': 'this is a dm', 'channel': 'DXXX', 'user': 'U'}],
         ('this is a dm', 'DXXX', 'U')))
    @ddt.unpack
    def test_parse_slack_output(self, output_list, expected):
        actual = self.wos.parse_slack_output(output_list)
        self.assertEqual(expected, actual)

    @ddt.data([{},  # no text
               {'text': '<@UBOTID> hi', 'user_profile': 'x'},  # has profile
               {'text': 'hello world', 'channel': 'NOTDM'}  # no at and not DM
               ])
    def test_parse_slack_output_to_skip(self, output_list):
        expected = (None, None, None)
        actual = self.wos.parse_slack_output(output_list)
        self.assertEqual(expected, actual)

    def test_setup_conversation_workspace_by_name_default(self):
        test_environ = {}
        expected_workspace_id = 'this is the one'
        self.conv_client.list_workspaces = mock.Mock(return_value={
            'workspaces': [{'workspace_id': 'other', 'name': 'foo'},
                           {'workspace_id': expected_workspace_id,
                            'name': 'watson-online-store'}]})

        wos = watson_online_store.WatsonOnlineStore
        actual = wos.setup_conversation_workspace(self.conv_client,
                                                  test_environ)

        self.conv_client.list_workspaces.assert_called_once()
        self.assertEqual(expected_workspace_id, actual)

    def test_setup_conversation_workspace_by_name_env(self):
        test_environ = {'WORKSPACE_NAME': 'foo name'}
        expected_workspace_id = 'this is the one'
        self.conv_client.list_workspaces = mock.Mock(return_value={
            'workspaces': [{'workspace_id': 'other', 'name': 'foo'},
                           {'workspace_id': expected_workspace_id,
                            'name': test_environ['WORKSPACE_NAME']}]})

        wos = watson_online_store.WatsonOnlineStore
        actual = wos.setup_conversation_workspace(self.conv_client,
                                                  test_environ)

        self.conv_client.list_workspaces.assert_called_once()
        self.assertEqual(expected_workspace_id, actual)

    def test_setup_conversation_workspace_by_id(self):
        expected_workspace_id = 'testing with a ws ID'
        test_environ = {'WORKSPACE_ID': expected_workspace_id}
        self.conv_client.list_workspaces = mock.Mock(return_value={
            'workspaces': [{'workspace_id': 'other'},
                           {'workspace_id': expected_workspace_id,
                            'name': 'foo'}]})

        wos = watson_online_store.WatsonOnlineStore
        actual = wos.setup_conversation_workspace(
            self.conv_client, test_environ)

        self.conv_client.list_workspaces.assert_called_once()
        self.assertEqual(expected_workspace_id, actual)

    def test_setup_conversation_workspace_by_id_not_found(self):
        expected_workspace_id = 'testing with a ws ID'
        test_environ = {'WORKSPACE_ID': expected_workspace_id}
        self.conv_client.list_workspaces = mock.Mock(return_value={
            'workspaces': [{'workspace_id': 'other'},
                           {'workspace_id': 'wrong again'}]})

        wos = watson_online_store.WatsonOnlineStore
        self.assertRaises(Exception,
                          wos.setup_conversation_workspace,
                          self.conv_client,
                          test_environ)

        self.conv_client.list_workspaces.assert_called_once()

    def test_setup_conversation_workspace_create(self):
        expected_workspace_id = 'this was created'
        expected_workspace_name = 'and this was its name'
        test_environ = {'WORKSPACE_NAME': expected_workspace_name}
        self.conv_client.list_workspaces = mock.Mock(return_value={
            'workspaces': [{'workspace_id': 'other', 'name': 'any'}]})
        self.conv_client.create_workspace = mock.Mock(return_value={
            'workspace_id': expected_workspace_id})
        wos = watson_online_store.WatsonOnlineStore
        ws_json = {
            'counterexamples': 'c',
            'intents': 'i',
            'entities': 'e',
            'dialog_nodes': 'd',
            'metadata': 'm',
            'language': 'en',
        }
        wos.get_workspace_json = mock.Mock(return_value=ws_json)

        actual = wos.setup_conversation_workspace(
            self.conv_client, test_environ)

        self.conv_client.list_workspaces.assert_called_once()
        self.conv_client.create_workspace.assert_called_once_with(
            expected_workspace_name,
            'Conversation workspace created by watson-online-store.',
            ws_json['language'],
            intents=ws_json['intents'],
            entities=ws_json['entities'],
            dialog_nodes=ws_json['dialog_nodes'],
            counterexamples=ws_json['counterexamples'],
            metadata=ws_json['metadata'])
        self.assertEqual(expected_workspace_id, actual)

    def test_setup_discovery_environment_by_id(self):
        expected_environment_id = 'testing with a env ID'
        expected_collection_id = 'testing with a coll ID'
        test_environ = {'DISCOVERY_ENVIRONMENT_ID': expected_environment_id,
                        'DISCOVERY_COLLECTION_ID': expected_collection_id}

        self.discovery_client.get_environment = mock.Mock(return_value={
            'environment_id': expected_environment_id})
        self.discovery_client.get_collection = mock.Mock(return_value={
            'collection_id': expected_collection_id})

        wos = watson_online_store.WatsonOnlineStore
        actual_env, actual_coll = (
            wos.setup_discovery_collection(self.discovery_client,
                                           self.fake_data_source,
                                           test_environ))

        self.discovery_client.get_environment.assert_called_once()
        self.discovery_client.get_collection.assert_called_once()
        self.assertEqual(expected_environment_id, actual_env)
        self.assertEqual(expected_collection_id, actual_coll)

    def test_setup_discovery_environment_by_name_default(self):
        test_environ = {}
        expected_environment_id = 'this is the env'
        expected_collection_id = 'this is the coll'
        self.discovery_client.list_environments = mock.Mock(return_value={
            'environments': [{'environment_id': 'other',
                              'name': 'foo',
                              'read_only': False},
                             {'environment_id': expected_environment_id,
                              'read_only': False,
                              'name': 'watson-online-store'}]})
        self.discovery_client.list_collections = mock.Mock(return_value={
            'collections': [{'collection_id': 'other', 'name': 'foo'},
                            {'collection_id': expected_collection_id,
                             'name': 'ibm-logo-store'}]})

        wos = watson_online_store.WatsonOnlineStore
        actual_env, actual_coll = (
            wos.setup_discovery_collection(self.discovery_client,
                                           self.fake_data_source,
                                           test_environ))

        self.discovery_client.list_environments.assert_called_once()
        self.discovery_client.list_collections.assert_called_once()
        self.assertEqual(expected_environment_id, actual_env)
        self.assertEqual(expected_collection_id, actual_coll)

    def test_format_ibm_store_output(self):
        ibm_product_name = "IBM Shirt"
        ibm_product_id = "012345"
        ibm_image_tag = '<a class="jqzoom" href="'
        ibm_image_url = 'https://www.test.xxx/scale[50]'
        ibm_product_tag = "/ProductDetail.aspx?pid="
        ibm_product_url = ("http://www.logostore-globalid.us" +
                           ibm_product_tag)
        ibm_expected_response = [{
            'cart_number': "1",
            'name': ibm_product_name,
            'url': ibm_product_url + ibm_product_id,
            'image': ibm_image_url
        }, ]

        wos = watson_online_store.WatsonOnlineStore

        # Test IBM Store formatting.
        # Note: use "XXX" to simulate that these tags are not at [0]
        ibm_results = [{
            'text': "XXXProduct:" + ibm_product_name + " Category:",
            'html': ("XXX" + ibm_product_tag + ibm_product_id +
                     ibm_image_tag + ibm_image_url + '"')
        }, ]
        ibm_response = {'results': ibm_results}
        output = wos.format_discovery_response(ibm_response, "IBM_STORE")
        self.assertEqual(ibm_expected_response, output)

    def test_format_amazon_store_output(self):
        amz_product_name = "Amazon Shirt"
        amz_product_tag = '<a href='
        amz_product_url = 'http://www.test.xxx'
        amz_expected_response = [{
            'cart_number': "1",
            'name': amz_product_name,
            'url': amz_product_url,
            'image': amz_product_url
        }, ]

        wos = watson_online_store.WatsonOnlineStore

        # Test Amazon Store formatting.
        # Note: use "XXX" to simulate that these tags are not at [0]
        amz_results = [{
            'extracted_metadata': {
                'title': amz_product_name
            },
            'html': "XXX" + amz_product_tag + " " + amz_product_url + ' >'
        }, ]
        amz_response = {'results': amz_results}
        output = wos.format_discovery_response(amz_response, "AMAZON")
        self.assertEqual(amz_expected_response, output)
