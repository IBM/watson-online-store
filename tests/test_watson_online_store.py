from watsononlinestore import watson_online_store
import mock


def test_0():

    fake_channel = "fake channel"
    fake_response = "this is a fake response"

    conv_client = mock.Mock()
    conv_client.message.return_value = {
        'context': {'send_no_input': 'no'},
        'output': {'text': [fake_response]},
    }
    discovery_client = None
    slack_client = mock.Mock()
    cloudant_store = mock.Mock()
    sender = watson_online_store.SlackSender(slack_client, fake_channel)

    wosbot = watson_online_store.WatsonOnlineStore('botid',
                                                   slack_client,
                                                   conv_client,
                                                   discovery_client,
                                                   cloudant_store)
    wosbot.handle_message("this is a test", sender)

    conv_client.assert_has_calls([
        mock.call.message(context={'send_no_input': 'no',
                                   'email': None,
                                   'logged_in': False},
                          message_input={'text': 'this is a test'},
                          workspace_id=mock.ANY)
    ])
    slack_client.assert_has_calls([
        mock.call.api_call(
            'chat.postMessage',
            as_user=True,
            channel=fake_channel,
            text=fake_response + '\n')
    ])
