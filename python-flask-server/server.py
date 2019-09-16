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

import os
import sys

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), '..'))
from run import WatsonEnv  # noqa

# Async mode allows us to run the Slack chatbot along with the web UI.
async_mode = "threading"

app = Flask(__name__, static_url_path='', template_folder='static')

# Generate your SECRET_KEY with os.random an paste it into your secure code.
# See: http://flask.pocoo.org/docs and go to "Quickstart" and "Sessions".
# Look for the "How to generate good secret keys" section for more explanation.
app.config['SECRET_KEY'] = ('\xc4\x0b\xd0\x98\x97\n\x8e\x82\xae\xe5\xa1C\x83'
                            '\xd3\xa4\x03h\x0e0\xea\x90\x92u\xc7')
socketio = SocketIO(app, async_mode=async_mode)
thread = None
namespace = '/wos'


@app.route('/')
def index():
    """Render our WOS web UI using a template.

    The web UI interacts with Python via Flask SocketIO.
    And uses HTML/CSS/Javascript for formatting.
    """
    return render_template('index.html', async_mode=async_mode)


class WebSocketSender:
    """Wrap send_message with a class to use with watson.handle_conversation().

    This is one implementation of a UI. The Slack integration is another.
    """

    def __init__(self):
        pass

    def send_message(self, message):
        """Function to send a message to the web-ui via Flask SocketIO."""
        lines = message.split('\n')
        for line in lines:
            image = None
            if 'output_format[png]' in line:
                line, http_tail = line.split('http', 1)
                image = 'http' + http_tail

            emit('my_response', {'data': line.strip(), 'image': image})

    def get_user_json(self, user_id):
        """Get user information from user_id.

        :param str user_id: user ID to look up.
        """
        # First impl of web-ui user is just user_id, for now.
        return {'user': {'profile': {
            'first_name': user_id,
            'last_name': user_id,
            'email': user_id,
        }}}


sender = WebSocketSender()
user = 'web user'  # TODO: Add login for web users.


@socketio.on('my_event', namespace=namespace)
def do_message(message):
    """This is a message from the web UI user."""
    if not watson:
        # Report incomplete setup.
        sender.send_message(
            "Sorry. The Watson Online Store is closed (failed to initialize).")

    elif message['data']:
        # Send message to WatsonOnlineStore and start a conversation loop.
        message = message['data']
        watson.handle_conversation(message, sender, user)


@socketio.on('connect', namespace=namespace)
def do_connect():
    """On web UI connect, do something here."""
    # On web UI connect, send a generic greeting via Flask SocketIO.
    # Uncomment for debugging. Not great for normal use case.
    # emit('my_response', {'data': 'Hello!'})
    pass


@socketio.on('disconnect', namespace=namespace)
def do_disconnect():
    """On disconnect, print to stdout. Just FYI."""
    print('Client disconnected')


# This script is intended to run from the command-line.
if __name__ == '__main__':

    # Initialize the store with its Bluemix services for the web UI
    watson = WatsonEnv.get_watson_online_store()

    if watson:
        # If env setup succeeded, get another instance to use for slack.
        # Separate instances to keep the web UI identity separate from
        # the slack user.
        slack_wos = WatsonEnv.get_watson_online_store()
        socketio.start_background_task(slack_wos.run)
    else:
        # Note: Failure during Slack setup does not cause a fail. The web UI
        # is running and will report an error message.
        print('Slack integration is not started because of missing environment'
              ' variables.')

    # The Bluemix port is passed in with a PORT environment variable.
    # This allows Bluemix health check to work. Otherwise the default
    # port for a Flask server is 5000.
    port = os.environ.get("PORT") or os.environ.get("VCAP_APP_PORT") or 5000

    # Run the web app.
    # Use 0.0.0.0 to allow remote connections.
    # Use PORT environment variable (set above) to set the port.
    socketio.run(app, host='0.0.0.0', port=int(port))
