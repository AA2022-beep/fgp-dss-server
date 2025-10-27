
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    pool_stats = {
        'meow_price': '0.0001 USD',
        'pool_hashrate': '500 MH/s',
        'current_block_info': '#567890',
        'block_reward': '100000 MEOW',
        'min_payout': '10000 MEOW',
        'total_blocks_mined': 5678,
        'blocks_mined_24h': 40,
        'total_miners': 300,
        'total_workers': 600,
        'share_rate_hr': '3000 shares/hr'
    }
    
    miners_online = [
        {'name': 'miner1', 'luck': '112%', 'min_payout': '10000 MEOW', 'status': 'Active'},
        {'name': 'miner2', 'luck': '97%', 'min_payout': '10000 MEOW', 'status': 'Active'},
    ]
    
    recent_blocks = [
        {'height': 567890, 'hash': '0000...ghij', 'timestamp': '2025-10-26 14:00:00', 'reward': '100000 MEOW'},
        {'height': 567889, 'hash': '0000...cdef', 'timestamp': '2025-10-26 13:55:00', 'reward': '100000 MEOW'},
    ]

    connection_details = {
        'stratum_host': 'stratum.meowcoin.com',
        'stratum_port': '3333',
        'username': 'YOUR_MEOW_ADDRESS.worker_name',
        'password': 'x'
    }

    hash_power = [
        {'provider': 'NiceHash', 'price': '0.1 BTC/TH/day'},
        {'provider': 'MiningRigRentals', 'price': '0.09 BTC/TH/day'},
    ]

    how_to_links = [
        {'title': 'How to start mining MeowCoin', 'url': '#'},
        {'title': 'How to configure your miner', 'url': '#'},
        {'title': 'How to create a MeowCoin wallet', 'url': '#'},
    ]

    return render_template('meow_coin_pool.html', 
                           title='MeowCoin Private Mining Pool',
                           pool_stats=pool_stats,
                           miners_online=miners_online,
                           recent_blocks=recent_blocks,
                           connection_details=connection_details,
                           hash_power=hash_power,
                           how_to_links=how_to_links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10004, debug=True)
