# Integrating FGP Coin - a New Coin with a Local Node and Stratum Pool Server

This document provides a detailed guide on how to integrate a new cryptocurrency into the DSS Server ecosystem. The process involves running a node for the new coin, setting up a stratum pool server to communicate with that node, and configuring the DSS Server to connect to your new pool.

## Process Overview

The `dssserver.py` script acts as a **job distributor** or **proxy**. It is designed to connect to an existing mining pool (like Nanopool or 2Miners), retrieve mining jobs, and distribute them to its own connected miners.

To support a new coin for which you are running a local node, you need a bridge component: a **stratum pool server**. This software connects to your coin's node to get block templates and then exposes a standard Stratum protocol interface that `dssserver.py` can connect to.

The data flow is as follows:

`[New Coin's Node]` <--> `[Stratum Pool Server]` <--> `[dssserver.py]` <--> `[Individual Miners]`

---

## Step 1: Run the Coin Node

This is the foundational requirement. Before you can set up a pool, you must have a running, fully synchronized node for the cryptocurrency you wish to support.

### Requirements:
- **Fully Synced:** The node must be fully synchronized with the coin's network blockchain.
- **RPC Enabled:** The node must be configured to allow RPC (Remote Procedure Call) connections. This is how the stratum pool server will request block templates and submit found blocks. You will typically need to set an RPC address, port, username, and password in the coin's configuration file (e.g., `bitcoin.conf` or `ravencoin.conf`).

---

## Step 2: Set Up a Stratum Pool Server

This is the most critical new component in the setup. The stratum pool server's job is to poll your coin node for new block templates and convert them into mining jobs that can be sent to miners using the Stratum protocol.

### Popular Pool Software:
- **node-open-mining-portal (NOMP):** A popular, open-source pool server written in Node.js. It's highly customizable and supports a wide range of coins.
- **python-stratum-mining:** A Python-based framework for building stratum servers.

### Configuration:
Once you have chosen and installed your pool software, you will need to configure it with the following details:
1.  **Daemon Connection:** The RPC address, port, username, and password for your coin node (from Step 1).
2.  **Payout Address:** A wallet address for the new coin where all block rewards will be sent when your pool successfully mines a block.
3.  **Stratum Port:** The network port that your pool server will listen on for incoming connections from miners (and from your `dssserver`). A common choice is `3333`.

---

## Step 3: Integrate the New Pool into `dssserver.py`

After your stratum pool server is running, you can add it to the DSS Server's list of available pools. From the perspective of `dssserver.py`, your local pool is just another remote server to connect to.

1.  Open `src/dssserver.py` (or a copy like `dssserver-fgstrat.py`).
2.  Locate the `self.pool_hosts` dictionary inside the `Distributor` class's `__init__` method.
3.  Add a new entry for your local pool. If the pool server is running on the same machine as `dssserver.py`, you can use the local loopback address (`127.0.0.1`).

#### Example Code Change:
```python
# Inside the Distributor class in dssserver.py

class Distributor():
    def __init__(self, sync_addr:tuple, auth:str) -> None:
        # ... other initializations ...
        self.pool_hosts = {
            # --- Add your new local pool here ---
            'my_new_coin_pool': ('127.0.0.1', 3333), # Connects to your local stratum server on port 3333

            # --- Existing pools ---
            'nanopool': ('xmr-us-west1.nanopool.org', 10300),
            'nanopool_rvn': ('rvn-eu1.nanopool.org', 10400),
            'gulf_moneroocean': ('gulf.moneroocean.stream', 10128),
            '2miners_rvn': ('us-rvn.2miners.com', 6060),
        }
        # ... rest of the __init__ method ...
```

---

## Step 4 (Advanced): Algorithm and Job Compatibility

The `stratum_client.py` file handles the logic for parsing job payloads from the pool and formatting share submissions. While the Stratum protocol is standardized, different coins and algorithms can have minor variations.

- **Hashing Algorithm:** If your new coin uses a unique hashing algorithm not already supported by your miners, the miners themselves will need to be updated.
- **Job Payload:** If the job data sent by your new pool (e.g., the `blob` or `target` format) is significantly different, you may need to modify `stratum_client.py` to correctly parse it into a `Job` object. For many standard coins, the existing logic may work without changes.

---

## Step 5: Running the Mock Server (A Practical Example)

To demonstrate this process without a real coin node, we have created `stratum_pool_server.py`. This script simulates a real stratum server by broadcasting fake mining jobs on a local port.

### How to Run the Mock Setup:
1.  **Start the Mock Pool Server:**
    Open a terminal and run the mock server. It will start listening for connections.
    ```sh
    python src/stratum_pool_server.py
    ```
    *Output: `Mock Stratum Pool Server listening on 0.0.0.0:3333`*

2.  **Start the Sync Server:**
    In a second terminal, run the sync server as usual. This server manages the job and result queues.
    ```sh
    python src/syncserver.py
    ```

3.  **Start the DSS Server:**
    In a third terminal, run the specially configured `dssserver-fgstrat.py`, which is set to connect to the mock pool by default.
    ```sh
    python src/dssserver-fgstrat.py
    ```

Now, when you open the DSS dashboard, it will be connected to your own local mock stratum pool. The server will receive and distribute the fake jobs generated by `stratum_pool_server.py`, simulating a complete, self-hosted pool environment.
