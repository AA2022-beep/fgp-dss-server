import os, time, json, uuid, requests, random, binascii, socket
from pathlib import Path
from threading import Thread, Lock
from datetime import datetime
from queue import Queue, Empty
from collections import deque
from flask import Flask, render_template, request, jsonify
from multiprocessing.managers import SyncManager

# Import the new Stratum client
from stratum_client import StratumClient, Job

# --- App & Helpers --- 48e5a4pxT5TLVjdQMGPPTLGD4JkSBfpSK2EnfULWvsWJ7mz7fLZk5QCLFivAqAg4D61EUiEy4bzyHHdZ4divYtDJK1CFb65
app = Flask(__name__, template_folder=str(Path(__file__).parent/'templates'), static_folder=str(Path(__file__).parent/'static'))
# Silence Flask's default GET/POST logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

DATA_DIR = os.path.join(str(Path(__file__).parents[1]),'_data'); WALLET_FILE=os.path.join(DATA_DIR,'wallet.txt')
DEFAULT_WALLET="REhjCARvGEbuP91hoU996RFSRt9RsCbgga" # Replace with a valid  address for testing

def read_wallet(): return open(WALLET_FILE,'r').read().strip() if os.path.exists(WALLET_FILE) else DEFAULT_WALLET
def save_wallet(addr): os.makedirs(DATA_DIR,exist_ok=True);open(WALLET_FILE,'w').write(addr)
class SyncManager(SyncManager): pass

# --- Main Distributor Class ---
class Distributor():
    def __init__(self, sync_addr:tuple, auth:str) -> None:
        self.registry={}; self.registry_lock=Lock(); self.sync_addr=sync_addr; self.auth=auth.encode('utf-8')
        self.get_q, self.res_q, self.mon_q = None, None, None # Add monitor queue
        self.max_q=5; self.jobs, self.results=0,0
        self.activity=deque(maxlen=20); self.server_running = False
        self.wallet=read_wallet()
        
        # Stratum Client Integration
        self.stratum_client = None
        self.latest_pool_job = None # New: Stores the latest job from the stratum client
        self.pool_hosts = {
            'nanopool': ('xmr-us-west1.nanopool.org', 10300),
            'nanopool_rvn': ('rvn-eu1.nanopool.org', 10400),
            'gulf_moneroocean': ('gulf.moneroocean.stream', 10128),
            '2miners_rvn': ('us-rvn.2miners.com', 6060),
            'p2pool': ('mini.p2pool.observer', 3333),
            'p2pool_mini': ('mini.p2pool.observer', 3333),
            'p2pool_main': ('p2pool.observer', 3333)
        }
        # Default to gulf.moneroocean.stream
        self.current_pool = 'nanopool'
        self.p2pool_host, self.p2pool_port = self.pool_hosts[self.current_pool]
        self.server_id = f"SERVER-{os.getpid()}"
        self.server_id = f"SERVER-{os.getpid()}"

    def start_server(self):
        if not self.server_running:
            self.server_running=True
            Thread(target=self.run_bg_tasks,daemon=True).start()
            self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":"Server starting...","is_event":True})

    def stop_server(self):
        if self.server_running: 
            self.server_running=False
            if self.stratum_client: self.stratum_client.connected = False
            
            # Unregister from the shared client list
            try:
                m = SyncManager(address=self.sync_addr, authkey=self.auth)
                m.register('get_clients')
                m.connect()
                client_list = m.get_clients()
                # Use a loop for safe removal from proxy object
                for i in range(len(client_list)):
                    if client_list[i] == self.server_id:
                        del client_list[i]
                        break
            except Exception as e:
                print(f"Could not unregister from sync server: {e}")

            self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":"Server stopped","is_event":True})
    
    def run_bg_tasks(self):
        if self.connect_to_sync_server():
            # Use on_job callback for realtime job delivery
            self.stratum_client = StratumClient(self.p2pool_host, self.p2pool_port, self.wallet, on_job=self._on_stratum_job)
            if not self.stratum_client.connected:
                self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":f"Failed to connect to {self.p2pool_host}","is_event":True})
                self.server_running = False
                return

            self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":f"Connected to P2Pool node at {self.p2pool_host}","is_event":True})
            Thread(target=self.process_client_shares,daemon=True).start()

    def connect_to_sync_server(self):
        max_retries = 5
        retry_delay = 2  # seconds
        for attempt in range(max_retries):
            try:
                SyncManager.register('get_queue'); SyncManager.register('result_queue'); SyncManager.register('monitor_queue'); SyncManager.register('get_clients')
                m=SyncManager(address=self.sync_addr,authkey=self.auth); m.connect()
                self.get_q,self.res_q,self.mon_q=m.get_queue(),m.result_queue(),m.monitor_queue()
                
                # Register the server as a connected client
                client_list = m.get_clients()
                client_list.append(self.server_id)
                
                return True
            except Exception as e:
                self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":f"Sync server connection failed (attempt {attempt+1}/{max_retries})...","is_event":True})
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":f"Error: Could not start sync server after {max_retries} attempts.","is_event":True})
                    self.server_running = False
                    return False


    def _normalize_job(self, job: Job) -> dict:
        """Convert a Job object into a client-friendly dictionary."""
        if not job or not job.is_valid():
            return {}
            
        return {
            'job_id': job.id,
            'blob': job.blob,
            'target': hex(job.target)[2:].zfill(64), # Ensure target is hex string
            'height': job.height,
            'seed_hash': job.seed_hash,
            'algo': job.algo,
            'nonce_offset': job.get_nonce_offset(),
            'nonce_size': job.get_nonce_size()
        }

    def _on_stratum_job(self, job: Job):
        """Callback from StratumClient when a new job is received.

        Updates the latest_pool_job and logs the event.
        """
        try:
            self.latest_pool_job = job
            self.activity.appendleft({
                "time": datetime.now().strftime('%H:%M:%S'),
                "node": f"New job {job.id[:8]}... received from pool"
            })
        except Exception as e:
            print(f"Error processing realtime job: {e}")

    def process_client_shares(self):
        while self.server_running:
            try:
                msg = self.res_q.get(timeout=1)
                
                # Handle client registration and heartbeats as before
                if msg.get('lodging'): self.register_client(msg)
                elif msg.get('type') == 'disconnect': self.unregister_client(msg)
                elif msg.get('type') == 'heartbeat': self.handle_heartbeat(msg)

                # Handle real share submissions
                elif 'result' in msg and self.stratum_client:
                    # Send to monitor queue before processing
                    if self.mon_q: self.mon_q.put(f"SHARE RECEIVED from {msg.get('client_id','')[:8]}: {msg}")
                    
                    self.stratum_client.submit_share(msg['job_id'], msg['nonce'], msg['hash'])
                    self.results += 1 # Count submitted shares
                    self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":f"Client {msg['client_id'][:8]} submitted share."})
                    
                    # After submitting a share, provide the latest job to the client
                    if self.latest_pool_job:
                        try:
                            client_job = self._normalize_job(self.latest_pool_job)
                            self.get_q.put(client_job)
                            self.jobs += 1
                            # Send to monitor queue
                            if self.mon_q: self.mon_q.put(f"JOB SENT to {msg.get('client_id','')[:8]}: {client_job}")
                            self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'), "node": f"Job {client_job.get('job_id','')[:8]}... sent to client {msg['client_id'][:8]}... after share submission."})
                        except Exception as e:
                            self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'), "node": f"Failed to send new job to client {msg['client_id'][:8]}...: {e}", "is_event": True})
            
            except Empty:
                continue
            except (ConnectionResetError, BrokenPipeError, EOFError):
                self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":"Connection to sync server lost. Shutting down...","is_event":True})
                print("Connection to sync server lost. Shutting down...")
                self.stop_server()
                break # Exit the loop
            except Exception as e:
                print(f"Error processing client shares: {e}")

    # Client management functions (register, unregister, heartbeat) remain largely the same
    def register_client(self, data):
        cid=data.get('client_id')
        with self.registry_lock:
            if cid not in self.registry:
                self.registry[cid]={"node":data['client_node'],"jobs_completed":0,"last_seen":time.time(),"hashrate":0.0}
                print(f"Client Registered: {cid[:8]}")
                # Immediately provide the latest job to the new client if available
                if self.latest_pool_job:
                    try:
                        client_job = self._normalize_job(self.latest_pool_job)
                        self.get_q.put(client_job)
                        self.jobs += 1
                        # Send to monitor queue
                        if self.mon_q: self.mon_q.put(f"JOB SENT to {cid[:8]}: {client_job}")
                        self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'), "node": f"Job {client_job.get('job_id','')[:8]}... sent to new client {cid[:8]}..."})
                    except Exception as e:
                        self.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'), "node": f"Failed to send job to new client {cid[:8]}...: {e}", "is_event": True})
    def unregister_client(self, data):
        cid=data.get('client_id')
        with self.registry_lock:
            if cid and cid in self.registry: del self.registry[cid]; print(f"Client Unregistered: {cid[:8]}")
    def handle_heartbeat(self, data):
        cid=data.get('client_id')
        with self.registry_lock:
            if cid in self.registry: self.registry[cid].update({"last_seen":time.time(),"hashrate":data.get('hashrate',0)})

# --- Flask Routes ---
@app.route('/')
def index():
    if not distributor:
        return "Distributor not initialized.", 500
    
    try:
        with distributor.registry_lock:
            clients=[{"id":cid, "node":c['node'][1], "hashrate":c.get('hashrate',0), "active":(time.time()-c["last_seen"])<5.1} for cid, c in distributor.registry.items()]
        
        stratum_client = distributor.stratum_client
        stratum_status = {
            "connected": stratum_client.connected if stratum_client else False,
            "last_job": stratum_client.current_job.id[:8] if stratum_client and stratum_client.current_job else None,
            "pool": distributor.current_pool,
            "host": distributor.p2pool_host,
            "port": distributor.p2pool_port
        }
        
        stats={
            "running": distributor.server_running,
            "jobs_distributed": distributor.jobs,
            "jobs_in_queue": distributor.get_q.qsize() if distributor.get_q else 0,
            "shares_submitted": distributor.results,
            "client_count": len(clients),
            "p2p_connected": stratum_status["connected"],
            "current_pool": distributor.current_pool,
            "stratum": stratum_status
        }
        return render_template('index.html', stats=stats, activity=list(distributor.activity), wallet=distributor.wallet, p2p_host=distributor.p2pool_host, clients=clients, available_pools=distributor.pool_hosts)

    except (ConnectionResetError, BrokenPipeError, EOFError):
        distributor.activity.appendleft({"time":datetime.now().strftime('%H:%M:%S'),"node":"Sync server connection lost. Shutting down server.","is_event":True})
        print("Sync server connection lost. Shutting down server.")
        distributor.stop_server()
        # Return a simple "disconnected" page
        return "<h1>Connection to Sync Server Lost</h1><p>The DSS Server has been stopped. Please restart the sync server and then restart this server.</p>", 503
    except Exception as e:
        print(f"An error occurred in the index route: {e}")
        return "An internal error occurred.", 500

@app.route('/start_server', methods=['POST'])
def start_server(): distributor.start_server(); return jsonify({"status":"ok"})
@app.route('/stop_server', methods=['POST'])
def stop_server(): distributor.stop_server(); return jsonify({"status":"ok"})

@app.route('/switch_pool', methods=['POST'])
def switch_pool():
    pool = request.json.get('pool')
    if pool in distributor.pool_hosts:
        if distributor.server_running:
            distributor.stop_server()
            time.sleep(1)  # Give time for cleanup
            
        distributor.current_pool = pool
        distributor.p2pool_host, distributor.p2pool_port = distributor.pool_hosts[pool]
        
        distributor.activity.appendleft({
            "time": datetime.now().strftime('%H:%M:%S'),
            "node": f"Switched to pool: {pool} ({distributor.p2pool_host}:{distributor.p2pool_port})",
            "is_event": True
        })
        
        return jsonify({"status": "ok", "pool": pool})
    return jsonify({"status": "error", "message": "Invalid pool selection"}), 400


@app.route('/save_wallet', methods=['POST'])
def save_wallet():
    data = request.json or {}
    addr = data.get('wallet')
    if not addr:
        return jsonify({"status":"error","message":"No wallet provided"}), 400
    try:
        save_wallet(addr)
        distributor.wallet = addr
        distributor.activity.appendleft({
            "time": datetime.now().strftime('%H:%M:%S'),
            "node": f"Wallet updated: {addr[:12]}...",
            "is_event": True
        })
        return jsonify({"status":"ok","wallet":addr})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@app.route('/get_pools', methods=['GET'])
def get_pools():
    return jsonify({
        "current_pool": distributor.current_pool,
        "available_pools": {
            name: {"host": host, "port": port}
            for name, (host, port) in distributor.pool_hosts.items()
        }
    })

# --- Global Distributor Instance ---
distributor = Distributor(sync_addr=('127.0.0.1',8625), auth="769ac424-adb6-5a73-83b0-d22eb27e543b")

if __name__ == '__main__':
    # The distributor is now created globally above.
    app.run(host='0.0.0.0', port=8080, debug=False)
