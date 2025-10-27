
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    pool_stats = {
        'neoxa_price': '0.001 USD',
        'pool_hashrate': '1.2 TH/s',
        'current_block_info': '#456789',
        'block_reward': '10000 NEOX',
        'min_payout': '500 NEOX',
        'total_blocks_mined': 4567,
        'blocks_mined_24h': 30,
        'total_miners': 250,
        'total_workers': 500,
        'share_rate_hr': '2500 shares/hr'
    }
    
    miners_online = [
        {'name': 'miner1', 'luck': '103%', 'min_payout': '500 NEOX', 'status': 'Active'},
        {'name': 'miner2', 'luck': '99%', 'min_payout': '500 NEOX', 'status': 'Active'},
    ]
    
    recent_blocks = [
        {'height': 456789, 'hash': '0000...mnop', 'timestamp': '2025-10-26 13:00:00', 'reward': '10000 NEOX'},
        {'height': 456788, 'hash': '0000...ijkl', 'timestamp': '2025-10-26 12:55:00', 'reward': '10000 NEOX'},
    ]

    connection_details = {
        'stratum_host': 'stratum.neoxa.net',
        'stratum_port': '3333',
        'username': 'YOUR_NEOX_ADDRESS.worker_name',
        'password': 'x'
    }

    hash_power = [
        {'provider': 'NiceHash', 'price': '0.1 BTC/TH/day'},
        {'provider': 'MiningRigRentals', 'price': '0.09 BTC/TH/day'},
    ]

    how_to_links = [
        {'title': 'How to start mining Neoxa', 'url': '#'},
        {'title': 'How to configure your miner', 'url': '#'},
        {'title': 'How to create a Neoxa wallet', 'url': '#'},
    ]

    return render_template('neoxa_pool.html', 
                           title='Neoxa Private Mining Pool',
                           pool_stats=pool_stats,
                           miners_online=miners_online,
                           recent_blocks=recent_blocks,
                           connection_details=connection_details,
                           hash_power=hash_power,
                           how_to_links=how_to_links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10003, debug=True)
