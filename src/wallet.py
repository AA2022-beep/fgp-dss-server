
import requests
import json
import time
import os
import shutil
import uuid
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wallet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

TEMP_FOLDER = os.path.join(app.root_path, 'temp')
ASSETS_FOLDER = os.path.join(app.root_path, 'assets')

login_manager = LoginManager()
login_manager.init_app(app)

# --- Database Models ---
# These models need to be defined here to make this a self-contained application.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    addresses = db.relationship('Address', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    command_logs = db.relationship('CommandLog', backref='user', lazy=True)
    wallets = db.relationship('Wallet', backref='user', lazy=True)
    invoices = db.relationship('Invoice', backref='user', lazy=True)
    assets = db.relationship('Asset', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(100), unique=True, nullable=False)
    label = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txid = db.Column(db.String(256), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    confirmations = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    address = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class CommandLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.String(256), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AddressBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    tx_type = db.Column(db.String(10), nullable=False)
    last_amount = db.Column(db.Float, nullable=False, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'address', name='_user_address_uc'),)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    asset = db.Column(db.String(50), nullable=False, default='RVN')
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Unpaid')
    recipient_address = db.Column(db.String(100), nullable=False)

class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    node_name = db.Column(db.String(100), nullable=False)
    coin = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=False, unique=True)
    host = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    in_circulation = db.Column(db.Float, nullable=True)
    max_circulation = db.Column(db.Float, nullable=True)
    mined_so_far = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Offline')

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subtype = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    divisibility = db.Column(db.Integer, nullable=False)
    ipfs_hash = db.Column(db.String(200))
    reissuable = db.Column(db.Boolean, default=True)
    txid = db.Column(db.String(256))
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)




# Set the login view after app is fully configured
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

NODE_RPC_URL = "http://127.0.0.1:8765"

def call_node_rpc(method, params=None):
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "1.0",
        "id": "flask-wallet",
        "method": method,
        "params": params or []
    }
    try:
        response = requests.post(NODE_RPC_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Try to parse the JSON error from the response body if it's an HTTP error
        try:
            return e.response.json()
        except json.JSONDecodeError:
            # If response is not JSON, return the plain text error
            return {"error": {"code": e.response.status_code, "message": e.response.text}}
    except requests.exceptions.RequestException as e:
        # For other request errors (like connection refused)
        print(f"RPC call failed: {e}")
        return {"error": {"code": -1, "message": f"Connection to node failed: {e}"}}

@app.route('/')
@login_required
def wallet_dashboard():
    # Fetch real-time data from the mock node
    balance_response = call_node_rpc("getbalance")
    if balance_response and not balance_response.get("error"):
        balance_data = balance_response["result"]
        available_rvn = balance_data["balance"]
        pending_rvn = balance_data["unconfirmed_balance"]
        total_rvn = balance_data["total"]
    else:
        # Fallback to mock data if RPC fails
        available_rvn = 0.0
        pending_rvn = 0.0
        total_rvn = 0.0

    # Fetch transactions from the database for the current user
    recent_transactions_db = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
    recent_transactions = []
    for tx in recent_transactions_db:
        recent_transactions.append({
            'id': tx.txid,
            'type': tx.category.capitalize(),
            'amount': f"{tx.amount:.8f} RVN",
            'date': tx.timestamp.strftime('%Y-%m-%d %H:%M'),
            'confirmations': tx.confirmations
        })

    # Fetch recently sent addresses from the database for the current user
    recently_sent_addresses_db = Address.query.filter_by(user_id=current_user.id).limit(5).all()
    recently_sent_addresses = []
    for addr_obj in recently_sent_addresses_db:
        # For simplicity, we're not fetching amount/confirmations from node for these mock addresses
        recently_sent_addresses.append({'address': addr_obj.address, 'amount': 'N/A', 'confirmations': 'N/A'})

    # Get a list of new addresses for receiving (from mock node)
    receiving_addresses = []
    for _ in range(10):
        new_address_response = call_node_rpc("getnewaddress")
        if new_address_response and not new_address_response.get("error"):
            receiving_addresses.append(new_address_response["result"])

    # Set a default wallet address if the list is not empty
    wallet_address = receiving_addresses[0] if receiving_addresses else "ERROR_FETCHING_ADDRESS"


    # Fetch address book entries
    address_book_entries = AddressBook.query.filter_by(user_id=current_user.id).order_by(AddressBook.timestamp.desc()).limit(4).all()
    address_book = []
    for entry in address_book_entries:
        address_book.append({
            'label': entry.label,
            'tx_type': entry.tx_type,
            'last_amount': entry.last_amount,
            'address': entry.address
        })

    # Fetch invoices
    invoices_db = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.date.desc()).all()
    invoices = []
    for inv in invoices_db:
        invoices.append({
            'id': inv.id,
            'date': inv.date.strftime('%Y-%m-%d %H:%M'),
            'description': inv.description,
            'asset': inv.asset,
            'amount': f"{inv.amount:.8f}",
            'status': inv.status
        })

    title_stats = {
        'total_rvn': f"{total_rvn:.2f} RVN",
        'available_rvn': f"{available_rvn:.2f} RVN",
        'pending_rvn': f"{pending_rvn:.2f} RVN",
    }

    wallet_data = {
        'balance_rvn': {'value': f"{available_rvn:.8f}", 'unit': 'RVN'},
        'pending_rvn': {'value': f"{pending_rvn:.8f}", 'unit': 'RVN'},
        'total_rvn': {'value': f"{total_rvn:.8f}", 'unit': 'RVN'},
    }

    return render_template('wallet.html',
                           title_stats=title_stats,
                           wallet_data=wallet_data,
                           recent_transactions=recent_transactions,
                           recently_sent_addresses=recently_sent_addresses,
                           address_book=address_book,
                           wallet_address=wallet_address,
                           receiving_addresses=receiving_addresses,
                           invoices=invoices)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('wallet_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Add sample address book data for the new user
        sample_addresses = [
            AddressBook(user_id=new_user.id, label="Coffee Shop", address="RBrCHHQHHUWB1hk23ggLAEU8a4brcYhg5P", tx_type="sent", last_amount=-5.50, timestamp=datetime.utcnow()),
            AddressBook(user_id=new_user.id, label="Trading Bot", address="RWDRRLjBD1Bs9Yx9y4texuHCDDG1NhwfMJ", tx_type="sent", last_amount=-250.0, timestamp=datetime.utcnow()),
            AddressBook(user_id=new_user.id, label="Gift from Family", address="RKm6M4BYM1URDUcJGNKYHP4gtMMSQnx8BK", tx_type="received", last_amount=100.0, timestamp=datetime.utcnow()),
            AddressBook(user_id=new_user.id, label="Freelance Payment", address="RPbCHHQHHUWB1hk23ggLAEU8a4brcYhg5P", tx_type="received", last_amount=350.75, timestamp=datetime.utcnow()),
            AddressBook(user_id=new_user.id, label="Sydney", address="RRRSYDtLncpr2rNxbJV4hJFY1RfEjpRzEr", tx_type="sent", last_amount=-5000.0, timestamp=datetime.utcnow()),
            AddressBook(user_id=new_user.id, label="Mine", address="REhjCARvGEbuP91hoU996RFSRt9RsCbgga", tx_type="received", last_amount=1250.0, timestamp=datetime.utcnow()),
        ]
        db.session.add_all(sample_addresses)

        # Add sample transaction data for the new user
        sample_transactions = [
            Transaction(user_id=new_user.id, txid='tx_sample_1', category='receive', amount=1250.0, confirmations=15, address='REhjCARvGEbuP91hoU996RFSRt9RsCbgga', timestamp=datetime.utcnow()),
            Transaction(user_id=new_user.id, txid='tx_sample_2', category='send', amount=-5.50, confirmations=30, address='RBrCHHQHHUWB1hk23ggLAEU8a4brcYhg5P', timestamp=datetime.utcnow()),
            Transaction(user_id=new_user.id, txid='tx_sample_3', category='receive', amount=100.0, confirmations=10, address='RKm6M4BYM1URDUcJGNKYHP4gtMMSQnx8BK', timestamp=datetime.utcnow()),
            Transaction(user_id=new_user.id, txid='tx_sample_4', category='send', amount=-250.0, confirmations=5, address='RWDRRLjBD1Bs9Yx9y4texuHCDDG1NhwfMJ', timestamp=datetime.utcnow()),
        ]
        db.session.add_all(sample_transactions)

        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('auth.html', active_tab='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('wallet_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('wallet_dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('auth.html', active_tab='login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/send_rvn', methods=['POST'])
@login_required
def send_rvn():
    data = request.json
    address = data.get('address')
    amount = data.get('amount')
    label = data.get('label', '')

    if not address or not amount:
        return jsonify({"status": "error", "message": "Address and amount are required."}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"status": "error", "message": "Amount must be positive."}), 400

        # Call mock node RPC to send transaction
        rpc_params = [address, amount, label, label] # Raven Core sendtoaddress format
        response = call_node_rpc("sendtoaddress", rpc_params)

        if response and not response.get("error"):
            txid = response["result"]["txid"]
            # Record transaction in our local database
            new_transaction = Transaction(txid=txid, category='send', amount=-amount, address=address, user_id=current_user.id)
            db.session.add(new_transaction)
            # Also save the address if it's new for this user
            existing_address = Address.query.filter_by(address=address, user_id=current_user.id).first()
            if not existing_address:
                new_address_obj = Address(address=address, label=label, user_id=current_user.id)
                db.session.add(new_address_obj)

            # Add or update address book entry
            book_entry = AddressBook.query.filter_by(user_id=current_user.id, address=address).first()
            if book_entry:
                # If entry exists, update its last transaction details and label if provided
                book_entry.last_amount = -amount
                book_entry.tx_type = 'sent'
                if label: book_entry.label = label
                book_entry.timestamp = datetime.utcnow() # Update timestamp
            elif label: # Only create new entry if a label is provided
                book_entry = AddressBook(user_id=current_user.id, label=label, address=address, tx_type='sent', last_amount=-amount, timestamp=datetime.utcnow())
                db.session.add(book_entry)
            db.session.commit()
            return jsonify({"status": "success", "txid": txid})
        else:
            return jsonify({"status": "error", "message": response["error"]["message"]}), 500
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid amount format."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_to_address_book', methods=['POST'])
@login_required
def add_to_address_book():
    data = request.json
    address = data.get('address')
    label = data.get('label')

    if not address or not label:
        return jsonify({"status": "error", "message": "Address and Label are required."}), 400

    # Check if this address already exists for the user
    existing_entry = AddressBook.query.filter_by(user_id=current_user.id, address=address).first()
    if existing_entry:
        return jsonify({"status": "error", "message": "This address is already in your address book."}), 400

    try:
        # For manually added entries, we can use a specific type
        new_entry = AddressBook(user_id=current_user.id, label=label, address=address, tx_type='saved', last_amount=0)
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"status": "success", "message": "Address added to book successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/save_invoice', methods=['POST'])
@login_required
def save_invoice():
    data = request.json
    address = data.get('address')
    amount_str = data.get('amount')
    description = data.get('label')

    if not address or not amount_str or not description:
        return jsonify({"status": "error", "message": "Address, Amount, and Label (for description) are required."}), 400

    try:
        amount = float(amount_str)
        if amount <= 0:
            return jsonify({"status": "error", "message": "Amount must be positive."}), 400

        new_invoice = Invoice(
            user_id=current_user.id,
            recipient_address=address,
            amount=amount,
            description=description,
            asset='RVN', # Defaulting to RVN
            status='Unpaid'
        )
        db.session.add(new_invoice)

        # Also save/update the address book entry
        book_entry = AddressBook.query.filter_by(user_id=current_user.id, address=address).first()
        if book_entry:
            # If entry exists, update its label and timestamp
            book_entry.label = description
            book_entry.timestamp = datetime.utcnow()
        else:
            # If it's a new address, create a new entry
            new_book_entry = AddressBook(user_id=current_user.id, label=description, address=address, tx_type='saved', last_amount=0, timestamp=datetime.utcnow())
            db.session.add(new_book_entry)

        db.session.commit()

        # Return the created invoice data for dynamic UI update
        invoice_data = {'id': new_invoice.id, 'date': new_invoice.date.strftime('%Y-%m-%d %H:%M'), 'description': new_invoice.description, 'asset': new_invoice.asset, 'amount': f"{new_invoice.amount:.8f}", 'status': new_invoice.status}
        return jsonify({"status": "success", "message": "Invoice saved successfully.", "invoice": invoice_data})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid amount format."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pay_invoice/<int:invoice_id>', methods=['POST'])
@login_required
def pay_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)

    if not invoice:
        return jsonify({"status": "error", "message": "Invoice not found."}), 404

    if invoice.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized."}), 403

    try:
        invoice.status = 'Paid'
        db.session.commit()
        return jsonify({"status": "success", "message": "Invoice marked as paid."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/upload_temp', methods=['POST'])
@login_required
def upload_temp():
    if 'filepond' not in request.files:
        return 'No file part', 400
    file = request.files['filepond']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        filename = secure_filename(file.filename)
        # Generate a unique ID for the temporary file
        server_id = str(uuid.uuid4())
        temp_path = os.path.join(TEMP_FOLDER, server_id)
        file.save(temp_path)
        # FilePond expects the server ID back as plain text
        return server_id, 200
    return 'Error', 500

@app.route('/create_asset', methods=['POST'])
@login_required
def create_asset():
    data = request.json
    asset_name = data.get('name')

    if not asset_name:
        return jsonify({"status": "error", "message": "Asset name is required."}), 400

    # Check for duplicate asset name
    if Asset.query.filter_by(name=asset_name).first():
        return jsonify({"status": "error", "message": f"An asset with the name '{asset_name}' already exists."}), 400

    try:
        # Create new asset in the database
        new_asset = Asset(
            user_id=current_user.id,
            name=asset_name,
            category=data.get('category'),
            subtype=data.get('subtype'),
            quantity=float(data.get('quantity', 1)),
            divisibility=int(data.get('divisibility', 0)),
            ipfs_hash=data.get('ipfs_hash')
        )
        db.session.add(new_asset)

        # Handle file moving
        uploaded_files = data.get('files', [])
        if uploaded_files:
            asset_folder_path = os.path.join(ASSETS_FOLDER, secure_filename(asset_name))
            os.makedirs(asset_folder_path, exist_ok=True)

            for server_id in uploaded_files:
                temp_file_path = os.path.join(TEMP_FOLDER, server_id)
                if os.path.exists(temp_file_path):
                    # This needs the original filename, which FilePond doesn't send by default.
                    # For simplicity, we'll just move the file with its server_id as the name.
                    # A more robust solution would store metadata about the upload.
                    shutil.move(temp_file_path, os.path.join(asset_folder_path, server_id))

        db.session.commit()
        return jsonify({"status": "success", "message": "Asset created successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/fgp-node')
@login_required
def fgp_node_dev():
    recent_commands_db = CommandLog.query.filter_by(user_id=current_user.id).order_by(CommandLog.timestamp.desc()).limit(10).all()
    recent_commands = [{'command': cmd.command, 'timestamp': cmd.timestamp.strftime('%Y-%m-%d %H:%M:%S')} for cmd in recent_commands_db]
    
    # Fetch wallets for the current user
    user_wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    # If no wallets, create a default one for demonstration
    if not user_wallets:
        default_wallet = Wallet(name='Default Wallet', user_id=current_user.id)
        db.session.add(default_wallet)
        db.session.commit()
        user_wallets = [default_wallet]

    return render_template('fgp-node-dev.html', recent_commands=recent_commands, wallets=user_wallets)

@app.route('/rpc', methods=['POST'])
@login_required
def rpc_handler():
    data = request.json
    method = data.get('method')
    params = data.get('params', [])
    command_str = f"{method} {' '.join(map(str, params))}"

    # Log the command
    try:
        new_log = CommandLog(command=command_str, user_id=current_user.id)
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        # Log error but don't fail the RPC call
        print(f"Error logging command: {e}")
        db.session.rollback()

    # Call the actual node RPC
    response = call_node_rpc(method, params)

    return jsonify(response)

@app.route('/add_wallet', methods=['POST'])
@login_required
def add_wallet():
    data = request.json
    wallet_name = data.get('name')

    if not wallet_name:
        return jsonify({"status": "error", "message": "Wallet name cannot be empty."}), 400

    # Check if a wallet with the same name already exists for this user
    existing_wallet = Wallet.query.filter_by(name=wallet_name, user_id=current_user.id).first()
    if existing_wallet:
        return jsonify({"status": "error", "message": "A wallet with this name already exists."}), 400

    try:
        new_wallet = Wallet(name=wallet_name, user_id=current_user.id)
        db.session.add(new_wallet)
        db.session.commit()
        return jsonify({"status": "success", "message": "Wallet created successfully.", "wallet": {"id": new_wallet.id, "name": new_wallet.name}})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

def setup_folders():
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    os.makedirs(ASSETS_FOLDER, exist_ok=True)

def create_initial_nodes():
    """Creates the initial node entries if they don't exist."""
    if Node.query.first() is None:
        nodes = [
            Node(node_name='Raven Node', coin='Ravencoin', symbol='RVN', host='127.0.0.1', port=8766, in_circulation=13988755000, max_circulation=21000000000, mined_so_far=13988755000, status='Online'),
            Node(node_name='FGP Node', coin='FGP Coin', symbol='FGP', host='127.0.0.1', port=8765, in_circulation=0, max_circulation=100000000, mined_so_far=0, status='Offline'),
            Node(node_name='Bitcoin Node', coin='Bitcoin', symbol='BTC', host='127.0.0.1', port=8332, in_circulation=19700000, max_circulation=21000000, mined_so_far=19700000, status='Offline'),
            Node(node_name='Ethereum Node', coin='Ethereum', symbol='ETH', host='127.0.0.1', port=8545, in_circulation=120200000, max_circulation=None, mined_so_far=120200000, status='Offline')
        ]
        db.session.add_all(nodes)
        db.session.commit()
        print("Initial nodes created.")

if __name__ == '__main__':
    # Since wallet.py is run as the main entry point for the web UI,
    # we need to create the database tables from this context.
    with app.app_context():
        setup_folders()
        db.create_all()
        create_initial_nodes()
    app.run(host='0.0.0.0', port=5889, debug=True)
