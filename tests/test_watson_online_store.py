from watsononlinestore import watson_online_store
import mock


def test_0():

    conv_client = mock.Mock()
    conv_client.message.return_value = {
        'context': {'send_no_input': 'no'},
        'output': {'text': 'fake output text'},
    }
    slack_client = mock.Mock()
    cloudant_store = mock.Mock()

    wosbot = watson_online_store.WatsonOnlineStore('botid', slack_client,
                                                    conv_client, cloudant_store)
    wosbot.handle_message("this is a test", "this is a channel")

    conv_client.assert_has_calls([
        mock.call.message(context={'send_no_input': 'no', 'email': None, 'logged_in': False},
                          message_input={'text': 'this is a test'},
                          workspace_id=mock.ANY)
    ])
    slack_client.assert_has_calls([
        mock.call.api_call(
            'chat.postMessage',
            as_user=True,
            channel='this is a channel',
            text='f\na\nk\ne\n \no\nu\nt\np\nu\nt\n \nt\ne\nx\nt\n')
    ])

