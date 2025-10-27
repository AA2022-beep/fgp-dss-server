
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    pool_stats = {
        'xna_price': '0.003 USD',
        'pool_hashrate': '500 GH/s',
        'current_block_info': '#234567',
        'block_reward': '5000 XNA',
        'min_payout': '100 XNA',
        'total_blocks_mined': 2345,
        'blocks_mined_24h': 20,
        'total_miners': 150,
        'total_workers': 300,
        'share_rate_hr': '1500 shares/hr'
    }
    
    miners_online = [
        {'name': 'miner1', 'luck': '105%', 'min_payout': '100 XNA', 'status': 'Active'},
        {'name': 'miner2', 'luck': '98%', 'min_payout': '100 XNA', 'status': 'Active'},
    ]
    
    recent_blocks = [
        {'height': 234567, 'hash': '0000...wxyz', 'timestamp': '2025-10-26 11:00:00', 'reward': '5000 XNA'},
        {'height': 234566, 'hash': '0000...stuv', 'timestamp': '2025-10-26 10:55:00', 'reward': '5000 XNA'},
    ]

    connection_details = {
        'stratum_host': 'stratum.neuraipool.com',
        'stratum_port': '3333',
        'username': 'YOUR_XNA_ADDRESS.worker_name',
        'password': 'x'
    }

    hash_power = [
        {'provider': 'NiceHash', 'price': '0.1 BTC/TH/day'},
        {'provider': 'MiningRigRentals', 'price': '0.09 BTC/TH/day'},
    ]

    how_to_links = [
        {'title': 'How to start mining NeurAI', 'url': '#'},
        {'title': 'How to configure your miner', 'url': '#'},
        {'title': 'How to create a NeurAI wallet', 'url': '#'},
    ]

    return render_template('Neurai_pool.html', 
                           title='NeurAI Private Mining Pool',
                           pool_stats=pool_stats,
                           miners_online=miners_online,
                           recent_blocks=recent_blocks,
                           connection_details=connection_details,
                           hash_power=hash_power,
                           how_to_links=how_to_links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10001, debug=True)
