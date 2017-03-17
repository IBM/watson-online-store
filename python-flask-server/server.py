import os

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit

from run import WatsonEnv, MISSING_ENV_VARS

async_mode = "threading"
app = Flask(__name__, static_url_path='')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None

namespace = '/test'


# Initialize the store with its Bluemix services
watson = WatsonEnv.get_watson_online_store()


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route('/')
def index():
    return render_template('index.html', async_mode=async_mode)


class WebSocketSender:
    """ Wrap send_message with a class to use with watson.handle_message()."""

    def __init__(self):
        pass

    def send_message(self, message):
        """Function to send a message to the web-ui."""
        emit('my_response', {'data': message})


sender = WebSocketSender()


@socketio.on('my_event', namespace=namespace)
def do_message(message):

    if not watson:
        sender.send_message(MISSING_ENV_VARS)

    elif message['data']:
        message = message['data']
        done = watson.handle_message(message, sender)
        while not done:
            done = watson.handle_message(message, sender)


@socketio.on('connect', namespace=namespace)
def do_connect():
    emit('my_response', {'data': 'Hello!'})


@socketio.on('disconnect', namespace=namespace)
def do_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    port = os.environ.get("PORT")

    if watson:
        # Run the slack bot in the background if env setup succeeded
        socketio.start_background_task(watson.run)
    else:
        print('Slack integration is not started because of missing environment'
              ' variables.')

    # Run the web app
    socketio.run(app, host='0.0.0.0', port=port)
