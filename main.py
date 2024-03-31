
# A very simple Flask Hello World app for you to get started with...

import hmac
import hashlib
import os

import git
from flask import Flask, abort, request, render_template, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from data_models import Expense, Label, ExpenseLabel, Base


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
USERNAME=os.environ['SITE_USERNAME']
PASSWORD=os.environ['SITE_PASSWORD']
app.secret_key = os.environ['SITE_SECRET']

mysql_host = os.environ['MYSQL_HOST']
mysql_user = os.environ['MYSQL_USER']
mysql_password = os.environ['MYSQL_PASSWORD']
mysql_db = os.environ['MYSQL_DB']

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle' : 280}
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}'
db = SQLAlchemy(app, model_class=Base)


# Check if the DB connection was successful
try:
    db.engine.connect()
    print("Connection to the database was successful.")
except Exception as e:
    print(f"Failed to connect to the database: {str(e)}")

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
    if not session.get('logged_in'):
        return redirect('/login')
    labels = Label.query.all()
    return render_template('index.html', labels=labels)

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect('/')

    return render_template('login.html')
