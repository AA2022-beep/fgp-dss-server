
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    pool_stats = {
        'clore_price': '0.02 USD',
        'pool_hashrate': '2.5 GH/s',
        'current_block_info': '#345678',
        'block_reward': '1000 CLORE',
        'min_payout': '100 CLORE',
        'total_blocks_mined': 3456,
        'blocks_mined_24h': 25,
        'total_miners': 200,
        'total_workers': 400,
        'share_rate_hr': '2000 shares/hr'
    }
    
    miners_online = [
        {'name': 'miner1', 'luck': '108%', 'min_payout': '100 CLORE', 'status': 'Active'},
        {'name': 'miner2', 'luck': '96%', 'min_payout': '100 CLORE', 'status': 'Active'},
    ]
    
    recent_blocks = [
        {'height': 345678, 'hash': '0000...qrst', 'timestamp': '2025-10-26 12:00:00', 'reward': '1000 CLORE'},
        {'height': 345677, 'hash': '0000...uvwx', 'timestamp': '2025-10-26 11:55:00', 'reward': '1000 CLORE'},
    ]

    connection_details = {
        'stratum_host': 'stratum.clore.ai',
        'stratum_port': '3333',
        'username': 'YOUR_CLORE_ADDRESS.worker_name',
        'password': 'x'
    }

    hash_power = [
        {'provider': 'NiceHash', 'price': '0.1 BTC/TH/day'},
        {'provider': 'MiningRigRentals', 'price': '0.09 BTC/TH/day'},
    ]

    how_to_links = [
        {'title': 'How to start mining Clore.ai', 'url': '#'},
        {'title': 'How to configure your miner', 'url': '#'},
        {'title': 'How to create a Clore.ai wallet', 'url': '#'},
    ]

    return render_template('clore_pool.html', 
                           title='Clore.ai Private Mining Pool',
                           pool_stats=pool_stats,
                           miners_online=miners_online,
                           recent_blocks=recent_blocks,
                           connection_details=connection_details,
                           hash_power=hash_power,
                           how_to_links=how_to_links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10002, debug=True)
