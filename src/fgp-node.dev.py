
import json
import uuid
import time
import random
from flask import Flask, render_template, request, jsonify

# --- Configuration ---
# The port on which the mock FGP Node and dashboard will listen.
NODE_RPC_PORT = 8765

# --- Mock Wallet Data ---
# This dictionary simulates the state of the Raven wallet.
# In a real node, this data would come from the blockchain and wallet database.
mock_wallet_data = {
    "balance": 15000.00000000, # Total available balance
    "unconfirmed_balance": 0.00000000, # Balance from unconfirmed transactions
    "immature_balance": 0.00000000, # Balance from newly mined blocks (not yet spendable)
    "addresses": {
        "RVN_WALLET_ADDRESS_EXAMPLE_12345ABCDEF": {
            "label": "Main Wallet",
            "balance": 14924.3499239,
            "pending": 2492.349843,
            "transactions": [] # List of transaction IDs
        },
        "RVN_ADDRESS_1": {"label": "Friend A", "balance": 0.0, "pending": 0.0, "transactions": []},
        "RVN_ADDRESS_2": {"label": "Exchange X", "balance": 0.0, "pending": 0.0, "transactions": []},
        "RVN_ADDRESS_3": {"label": "Mining Payout", "balance": 0.0, "pending": 0.0, "transactions": []},
    },
    "transactions": [] # Global list of all transactions
}

# Populate initial mock transactions
mock_wallet_data["transactions"] = [
    {'txid': 'tx123abc', 'category': 'receive', 'amount': 100.0, 'confirmations': 12, 'time': int(time.time()) - 3600, 'address': 'RVN_WALLET_ADDRESS_EXAMPLE_12345ABCDEF'},
    {'txid': 'tx456def', 'category': 'send', 'amount': -50.0, 'confirmations': 24, 'time': int(time.time()) - 7200, 'address': 'RVN_ADDRESS_1'},
    {'txid': 'tx789ghi', 'category': 'receive', 'amount': 200.0, 'confirmations': 6, 'time': int(time.time()) - 10800, 'address': 'RVN_WALLET_ADDRESS_EXAMPLE_12345ABCDEF'},
]

# --- Helper Functions for Mock RPC Logic ---
def generate_new_address():
    """Generates a mock new Raven address."""
    return "RVN_NEW_ADDRESS_" + uuid.uuid4().hex[:10].upper()

def get_balance_mock(address=None):
    """
    Returns mock balance data.
    In a real node, this would query the blockchain for the actual balance.
    """
    if address and address in mock_wallet_data["addresses"]:
        addr_data = mock_wallet_data["addresses"][address]
        return {
            "balance": addr_data["balance"],
            "unconfirmed_balance": addr_data["pending"],
            "immature_balance": 0.0,
            "total": addr_data["balance"] + addr_data["pending"]
        }
    else:
        # Return overall wallet balance if no specific address is given
        total_available = sum(data["balance"] for data in mock_wallet_data["addresses"].values())
        total_pending = sum(data["pending"] for data in mock_wallet_data["addresses"].values())
        return {
            "balance": total_available,
            "unconfirmed_balance": total_pending,
            "immature_balance": 0.0,
            "total": total_available + total_pending
        }

def send_to_address_mock(to_address, amount, comment="", comment_to=""):
    """
    Simulates sending RVN to an address.
    In a real node, this would create and broadcast a transaction.
    """
    if amount <= 0 or amount > mock_wallet_data["balance"]:
        return {"error": "Invalid amount or insufficient funds"}

    txid = "tx" + uuid.uuid4().hex[:10]
    timestamp = int(time.time())

    # Deduct from main balance
    mock_wallet_data["balance"] -= amount

    # Add a mock transaction
    mock_wallet_data["transactions"].insert(0, {
        'txid': txid,
        'category': 'send',
        'amount': -amount,
        'confirmations': 0, # Initially unconfirmed
        'time': timestamp,
        'address': to_address,
        'comment': comment,
        'comment_to': comment_to
    })
    print(f"Mock transaction created: {txid} for {amount} RVN to {to_address}")
    return {"txid": txid}

def list_transactions_mock(count=10, skip=0, include_watchonly=False):
    """
    Returns a mock list of recent transactions.
    """
    # Sort by time descending (most recent first)
    sorted_txs = sorted(mock_wallet_data["transactions"], key=lambda x: x['time'], reverse=True)
    
    # Apply skip and count
    return sorted_txs[skip : skip + count]

# --- Flask Application ---
app = Flask(__name__)

@app.route('/', methods=['GET'])
def dashboard():
    """Serves the mock node dashboard."""
    return render_template('fgp-node-dev.html')

@app.route('/', methods=['POST'])
def rpc_handler():
    """Handles JSON-RPC requests."""
    request_json = request.get_json()
    method = request_json.get('method')
    params = request_json.get('params', [])
    req_id = request_json.get('id', None)

    result = None
    error = None

    print(f"Received RPC call: {method} with params {params}")

    # --- Dispatch RPC Methods ---
    if method == "getbalance":
        # params can be [min_conf] or [account, min_conf]
        address = params[0] if params and isinstance(params[0], str) else None
        result = get_balance_mock(address)
    elif method == "sendtoaddress":
        if len(params) >= 2:
            to_address = params[0]
            amount = float(params[1])
            comment = params[2] if len(params) > 2 else ""
            comment_to = params[3] if len(params) > 3 else ""
            result = send_to_address_mock(to_address, amount, comment, comment_to)
        else:
            error = {"code": -1, "message": "Invalid params for sendtoaddress"}
    elif method == "listtransactions":
        count = params[0] if params and len(params) > 0 else 10
        skip = params[1] if params and len(params) > 1 else 0
        result = list_transactions_mock(count, skip)
    elif method == "getnewaddress":
        result = generate_new_address()
    else:
        error = {"code": -32601, "message": f"Method not found: {method}"}

    response_payload = {
        "jsonrpc": "1.0",
        "id": req_id,
        "result": result,
        "error": error
    }
    return jsonify(response_payload)

# --- Main Execution Block ---
if __name__ == "__main__":
    print(f"Mock FGP Node Dashboard and RPC Server running on http://127.0.0.1:{NODE_RPC_PORT}")
    app.run(host='0.0.0.0', port=NODE_RPC_PORT, debug=True)
