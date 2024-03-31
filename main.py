
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, abort

import hmac
import hashlib

def is_valid_signature(x_hub_signature : str, data, private_key):
    # x_hub_signature and data are from the webhook payload
    # private key is your webhook secret
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

app = Flask(__name__)
W_SECRET = os.environ['SECRET_KEY']

@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':

        x_hub_signature = request.headers.get('X-Hub-Signature')

        if not is_valid_signature(x_hub_signature, request.data, W_SECRET):
            return f'Deploy signature failed: {x_hub_signature}', 418

        repo = git.Repo('/home/martinsavc/SpendingLog/')
        origin = repo.remotes.origin

        origin.pull()

        return 'Updated PythonAnywhere successfully', 200
    else:
        return 'Wrong event type', 400

@app.route('/')
def hello_world():
    return 'Hello from Flask!'

