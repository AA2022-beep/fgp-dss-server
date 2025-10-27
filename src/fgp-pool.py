
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

    # The render_template function passes the data to the HTML file.
    return render_template(
        'fgp-pool.html',
        title_stats=title_stats,
        home_content=home_content
    )

if __name__ == '__main__':
    # The application will run on port 5888 and be accessible from any device on the network.
    app.run(host='0.0.0.0', port=5888, debug=True)
