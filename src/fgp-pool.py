
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    """
    Renders the main page of the FGP Pool.
    """
    # Mock data for the main title block stats.
    title_stats = {
        "total_paid": "1,234.56 XMR",
        "miners_online": 128,
        "pool_hashrate": "15.7 GH/s",
        "blocks_found": 842
    }

    # Mock data for the 'Home' tab content.
    home_content = {
        "welcome_message": "Welcome to FGP Pool, your reliable and high-performance mining partner.",
        "pool_features": [
            "Stable & High-Performance Servers",
            "Real-time Payouts (PPLNS)",
            "Detailed Miner Statistics",
            "Active Community Support"
        ],
        "news": [
            {"date": "2025-10-27", "title": "Pool software upgraded to the latest version for improved stability."},
            {"date": "2025-10-25", "title": "Community vote on the next coin to be added has begun."}
        ]
    }

    # Data from raven_pool.py for the three-column layout
    pool_stats = {
        'rvn_price_value': '0.03', 'rvn_price_unit': 'USD',
        'pool_hashrate_value': '1.5', 'pool_hashrate_unit': 'GH/s',
        'current_block_info_value': '#123456', 'current_block_info_unit': '',
        'block_reward_value': '2500', 'block_reward_unit': 'RVN',
        'min_payout_value': '50', 'min_payout_unit': 'RVN',
        'total_blocks_mined_value': 1234, 'total_blocks_mined_unit': '',
        'blocks_mined_24h_value': 15, 'blocks_mined_24h_unit': '(last 24 hrs)',
        'total_miners_value': 100, 'total_miners_unit': '',
        'total_workers_value': 250, 'total_workers_unit': '',
        'share_rate_hr_value': '1000', 'share_rate_hr_unit': '/hr'
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

    # Mock data for the pool hashrate chart
    hashrate_chart_data = {
        'labels': ['10:00', '10:15', '10:30', '10:45', '11:00', '11:15', '11:30'],
        'data': [1.2, 1.3, 1.5, 1.4, 1.6, 1.5, 1.7]
    }

    # The render_template function passes the data to the HTML file.
    return render_template(
        'fgp-pool.html',
        title_stats=title_stats,
        home_content=home_content,
        pool_stats=pool_stats,
        miners_online=miners_online,
        recent_blocks=recent_blocks,
        connection_details=connection_details,
        hash_power=hash_power,
        how_to_links=how_to_links,
        hashrate_chart_data=hashrate_chart_data
    )

if __name__ == '__main__':
    # The application will run on port 5888 and be accessible from any device on the network.
    app.run(host='0.0.0.0', port=5888, debug=True)
