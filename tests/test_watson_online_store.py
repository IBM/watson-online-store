from watsononlinestore import watson_online_store
import ddt
import mock
import unittest


@ddt.ddt
class WOSTestCase(unittest.TestCase):

    def setUp(self):
        self.slack_client = mock.Mock()
        self.conv_client = mock.Mock()
        self.cloudant_store = mock.Mock()
        self.discovery_client = mock.Mock()

        self.wosbot = watson_online_store.WatsonOnlineStore(
            'botid',
            self.slack_client,
            self.conv_client,
            self.discovery_client,
            self.cloudant_store)

    def test_0(self):

        fake_channel = "fake channel"
        fake_response = "this is a fake response"

        self.conv_client.message.return_value = {
            'context': {'send_no_input': 'no'},
            'output': {'text': [fake_response]},
        }

        self.wosbot.handle_message("this is a test", fake_channel)

        self.conv_client.assert_has_calls([
            mock.call.message(context={'email': None,
                                       'logged_in': False},
                              message_input={'text': 'this is a test'},
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
            AssertionError, self.wosbot.init_customer, no_user_id)

    def test_init_customer_slack_fail(self):
        self.slack_client.api_call = mock.Mock(side_effect=Exception("Boom"))
        user = "testuser"

        self.wosbot.init_customer(user)

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

        self.wosbot.init_customer(user)

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

        self.wosbot.init_customer(user)

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

        self.wosbot.init_customer(user)

        self.slack_client.api_call.assert_called_once_with(
            'users.info', user=user)
        self.cloudant_store.find_customer.assert_called_once_with(
            test_email_addr)
