
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    # This dictionary will eventually be populated with real data
    pool_stats = {
        'rvn_price': '0.03 USD',
        'pool_hashrate': '1.5 GH/s',
        'current_block_info': '#123456',
        'block_reward': '2500 RVN',
        'min_payout': '50 RVN',
        'total_blocks_mined': 1234,
        'blocks_mined_24h': 15,
        'total_miners': 100,
        'total_workers': 250,
        'share_rate_hr': '1000 shares/hr'
    }
    
    miners_online = [
        {'name': 'miner1', 'luck': '110%', 'min_payout': '50 RVN', 'status': 'Active'},
        {'name': 'miner2', 'luck': '95%', 'min_payout': '50 RVN', 'status': 'Active'},
        {'name': 'miner3', 'luck': '102%', 'min_payout': '100 RVN', 'status': 'Inactive'},
    ]
    
    recent_blocks = [
        {'height': 123456, 'hash': '0000...abcd', 'timestamp': '2025-10-26 10:00:00', 'reward': '2500 RVN'},
        {'height': 123455, 'hash': '0000...efgh', 'timestamp': '2025-10-26 09:55:00', 'reward': '2500 RVN'},
    ]

    connection_details = {
        'stratum_host': 'stratum.ravencoin.flypool.org',
        'stratum_port': '3333',
        'username': 'YOUR_RVN_ADDRESS.worker_name',
        'password': 'x'
    }

    hash_power = [
        {'provider': 'NiceHash', 'price': '0.1 BTC/TH/day'},
        {'provider': 'MiningRigRentals', 'price': '0.09 BTC/TH/day'},
    ]

    how_to_links = [
        {'title': 'How to start mining Ravencoin', 'url': '#'},
        {'title': 'How to configure your miner', 'url': '#'},
        {'title': 'How to create a Ravencoin wallet', 'url': '#'},
    ]

    return render_template('raven_pool.html', 
                           title='Raven Private Mining Pool',
                           pool_stats=pool_stats,
                           miners_online=miners_online,
                           recent_blocks=recent_blocks,
                           connection_details=connection_details,
                           hash_power=hash_power,
                           how_to_links=how_to_links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
