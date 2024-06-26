
import hmac
import hashlib
import os
from datetime import datetime, timedelta

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
    labels = get_all_labels()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    expenses = get_expenses_between_dates(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    return render_template('index.html', labels=labels, expenses=expenses)

@app.route('/submit_expense', methods=['POST'])
def submit_expense():
    if not session.get('logged_in'):
        return redirect('/login')
    # Get the data from the form
    item_names = request.form.getlist('item_name[]')
    prices = request.form.getlist('price[]')
    dates = request.form.getlist('date[]')
    labels = request.form.getlist('labels[]')

    # Insert expenses into the database
    for item_name, price, date, label in zip(item_names, prices, dates, labels):
        expense = Expense(item_name=item_name, price=price, date=date)
        update_labels_in_database(expense, label)
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

def get_expenses_between_dates(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    expenses = Expense.query.filter(Expense.date >= start_date, Expense.date <= end_date).all()
    return expenses

def get_all_labels():
    return Label.query.all()

def update_labels_in_database(expense, label_str):
    expense.labels.clear()
    labels_list = [lbl.strip() for lbl in label_str.split(',')]
    for lbl in labels_list:
        existing_label = Label.query.filter_by(name=lbl).first()
        if existing_label is None:
            new_label = Label(name=lbl)
            db.session.add(new_label)
            db.session.commit()
            expense.labels.append(new_label)
        else:
            expense.labels.append(existing_label)


@app.route('/expenses_list', methods=['GET', 'POST'])
def expenses_list():
    if not session.get('logged_in'):
        return redirect('/login')
    if request.method == 'POST':
        # Handle filtering expenses by dates
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        expenses = get_expenses_between_dates(start_date, end_date)  
    else:
        # Render the page without filtering by default
        expenses = []
    labels = get_all_labels()  
    return render_template('expenses_list.html', expenses=expenses, labels=labels)

@app.route('/update_labels', methods=['POST'])
def update_labels():
    if not session.get('logged_in'):
        return redirect('/login')
    expense_id = request.form['expense_id']
    labels = request.form['labels']
    expense = Expense.query.get(expense_id)
    update_labels_in_database(expense, labels)
    db.session.commit()
    return redirect('/expenses_list')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect('/')

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    if not session.get('logged_in'):
        return redirect('/login')
    session.clear()  # Clear the session
    return redirect('/login')  # Redirect to the login page