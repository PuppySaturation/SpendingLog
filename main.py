
# A very simple Flask Hello World app for you to get started with...

import hmac
import hashlib
import os

import git
from flask import Flask, abort, request, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import Expense, Label, ExpenseLabel


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

# will need later for simple authentication
#username=os.environ['SITE_USERNAME']
#password=os.environ['SITE_PASSWORD']

mysql_host = os.environ['MYSQL_HOST']
mysql_user = os.environ['MYSQL_USER']
mysql_password = os.environ['MYSQL_PASSWORD']
mysql_db = os.environ['MYSQL_DB']

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}'
db = SQLAlchemy(app)

# Handle MySQL connection errors
@app.errorhandler(500)
def internal_server_error(e):
    return "Error: Unable to connect to MySQL database", 500

@app.route('/update_server', methods=['POST', 'GET'])
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
def index():
    return send_from_directory('static', 'index.html')

@app.route('/submit_expense', methods=['POST'])
def submit_expense():
    # Get the data from the form
    item_names = request.form.getlist('item_name[]')
    prices = request.form.getlist('price[]')
    dates = request.form.getlist('date[]')
    labels = request.form.getlist('labels[]')

    # Insert expenses into the database
    for item_name, price, date, label in zip(item_names, prices, dates, labels):
        expense = Expense(item_name=item_name, price=price, date=date)
        labels_list = [lbl.strip() for lbl in label.split(',')]
        for lbl in labels_list:
            existing_label = Label.query.filter_by(name=lbl).first()
            if existing_label is None:
                new_label = Label(name=lbl)
                db.session.add(new_label)
                db.session.commit()
                expense.labels.append(new_label)
            else:
                expense.labels.append(existing_label)
        db.session.add(expense)
        db.session.commit()

    return jsonify({'message': 'Expenses submitted successfully'})


