
import socket
import json
import time
from threading import Thread
from job import Job

class StratumClient:
    def __init__(self, host, port, wallet, on_job=None):
        self.host = host
        self.port = port
        self.wallet = wallet

        self.socket = None
        self.request_id = 1
        self.connected = False
        self.current_job = None
        # optional callback(job_params) called when a new job arrives
        self.on_job = on_job

        # Tracking subscription and auth states
        self.subscription_id = None
        self.auth_id = None
        self.waiting_subscribe = False
        self.subscription_response = None

        self.connect()

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True

            listen_thread = Thread(target=self.listen, daemon=True)
            listen_thread.start()

            self.login()
            
            print(f"Successfully connected to Stratum server at {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to connect to Stratum server: {e}")
            self.connected = False

    def login(self):
        # Send mining.subscribe and wait for response
        print("\nSending mining.subscribe request...")
        subscribe_payload = {
            "id": self.request_id,
            "method": "mining.subscribe",
            "params": ["DSS-Miner/0.1"]
        }
        self.send(subscribe_payload)
        
        # Store the subscription ID to track its response
        self.subscription_id = self.request_id
        self.request_id += 1
        
        # Wait for subscription confirmation before proceeding
        self.waiting_subscribe = True
        while self.waiting_subscribe and self.socket:
            time.sleep(0.1)
        
        if not self.socket:
            print("Connection lost while waiting for subscription response")
            return
            
        print("\nSending mining.authorize request...")
        # Then send mining.authorize
        auth_payload = {
            "id": self.request_id,
            "method": "mining.authorize",
            "params": [
                self.wallet,
                "dss-pool"
            ]
        }
        self.send(auth_payload)
        self.auth_id = self.request_id
        self.request_id += 1

    def send(self, payload):
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}] Sending request:")
            print(json.dumps(payload, indent=2))
            self.socket.sendall((json.dumps(payload) + '\n').encode('utf-8'))
        except Exception as e:
            print(f"Error sending data: {e}")
            self.connected = False

    def listen(self):
        partial = ''
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    time.sleep(0.1)
                    continue
                buffer = data.decode('utf-8', errors='ignore')
                partial += buffer
                while '\n' in partial:
                    line, partial = partial.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        self.handle_message(msg)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding server message: {e} -- line: {line}")
                        continue
            except Exception as e:
                print(f"Error in listen loop: {e}")
                self.connected = False
                break

    def handle_message(self, message):
        # Print all incoming messages with timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Received message:")
        print(json.dumps(message, indent=2))

        method = message.get('method')
        params = message.get('params')
        msg_id = message.get('id')
        
        if method in ('job', 'mining.notify', 'notify'):
            # Create a new job object
            job = Job(nicehash=True)  # MoneroOcean uses nicehash protocol
            
            # Set algorithm if present in the message
            algo = message.get('algo')
            if algo:
                job.set_algo(algo)

            if isinstance(params, dict):
                # Handle dictionary-based job params (RandomX)
                if not job.set_id(params.get('job_id', '')):
                    print("Error: Invalid job ID")
                    return
                    
                if not job.set_blob(params.get('blob', '')):
                    print("Error: Invalid blob")
                    return
                    
                if not job.set_target(params.get('target', '')):
                    print("Error: Invalid target")
                    return
                    
                job.set_height(params.get('height', 0))
                job.set_seed_hash(params.get('seed_hash', ''))

            elif isinstance(params, list):
                # Handle list-based job params (KawPow)
                if len(params) < 7:
                    print("Error: Invalid job parameters for KawPow")
                    return
                
                job.set_id(params[0])
                # For KawPow, the "blob" is constructed from several parts
                header_hash = params[1]
                seed_hash = params[2]
                target = params[3]
                job.set_height(params[5])
                
                # The mining blob for kawpow is header_hash + seed_hash
                # The nonce is appended by the miner at the end.
                job.set_blob(header_hash + seed_hash)
                job.set_target(target)
                job.set_seed_hash(seed_hash)

            else:
                print("Error: Job parameters are not in a recognized format")
                return

            if job.is_valid():
                print(f"\n[{timestamp}] New valid job received:")
                print(f"Job ID: {job.id}")
                print(f"Algorithm: {job.algo}")
                print(f"Height: {job.height}")
                print(f"Target: {job.target} (diff: {job.diff})")
                print(f"Blob size: {job.size} bytes")
                
                self.current_job = job
                try:
                    if callable(self.on_job):
                        self.on_job(job)
                except Exception as e:
                    print(f"Error in on_job callback: {e}")
            else:
                print("Error: Invalid job parameters")
        elif 'result' in message:
            print(f"\n[{timestamp}] Server response (success) for request {msg_id}:")
            print(json.dumps(message['result'], indent=2))
            
            # Handle subscription response
            if msg_id == self.subscription_id:
                if isinstance(message['result'], list):
                    print(f"\n=== Subscription Response Analysis ===")
                    print(f"Response ID: {msg_id}")
                    print(f"Content: {json.dumps(message['result'], indent=2)}")
                    self.subscription_response = message['result']
                    print(f"=== End Subscription Analysis ===\n")
                    print(f"Subscription successful, proceeding with authorization...")
                    self.waiting_subscribe = False
                    
            # Handle authorization response
            elif msg_id == self.auth_id:
                if message['result'] is True:
                    print(f"\n=== Authorization Successful ===")
                    print(f"Pool accepted our login")
                    print(f"Connection fully established")
                    print(f"Waiting for mining jobs...\n")
                    self.connected = True
                else:
                    print(f"\n=== Authorization Failed ===")
                    print(f"Pool rejected our login")
                    self.connected = False
        
        elif 'error' in message:
            print(f"\n[{timestamp}] Server response (error):")
            print(json.dumps(message['error'], indent=2))
            if msg_id in (1, 2):  # If error during subscribe or authorize
                print("Connection setup failed")
                self.connected = False

    def get_job(self):
        return self.current_job

    def submit_share(self, job_id, nonce, result_hash):
        """Submit a share to the pool
        
        Args:
            job_id (str): The ID of the job being submitted
            nonce (str): The nonce that resulted in a valid share (hex encoded)
            result_hash (str): The proof of work result hash (hex encoded)
        """
        # Validate inputs
        if not job_id or not nonce or not result_hash:
            print("Error: Invalid share submission parameters")
            return
            
        if not isinstance(self.current_job, Job) or self.current_job.id != job_id:
            print("Error: Share submitted for invalid/expired job")
            return
            
        # XMRig/Stratum standard: params as array [worker_id, job_id, nonce, result]
        payload = {
            "method": "submit",
            "params": ["dss-client", job_id, nonce, result_hash],
            "id": self.request_id
        }
        self.send(payload)
        self.request_id += 1
        
        print(f"Submitting share for job {job_id}")
        print(f"Nonce: {nonce}")
        print(f"Result: {result_hash}")

if __name__ == '__main__':
    print("\n=== Stratum Client Test ===")
    print("Connecting to moneroocean pool...")
    
    # Pool configuration
    pool_host = 'gulf.moneroocean.stream'
    pool_port = 10128
    wallet = '48e5a4pxT5TLVjdQMGPPTLGD4JkSBfpSK2EnfULWvsWJ7mz7fLZk5QCLFivAqAg4D61EUiEy4bzyHHdZ4divYtDJK1CFb65'

    def on_new_job(job):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Job callback triggered:")
        if isinstance(job, dict):
            print("Job details:")
            for key in ['job_id', 'blob', 'target', 'height', 'seed_hash']:
                if key in job:
                    print(f"  {key}: {job[key]}")
        else:
            print(f"Raw job data: {job}")

    # Create client with job callback
    client = StratumClient(pool_host, pool_port, wallet, on_job=on_new_job)
    
    print("\nClient running. Press Ctrl+C to stop.")
    print("Displaying all stratum protocol messages...")
    
    try:
        while True:
            time.sleep(1)
            if not client.connected:
                print("\nConnection lost. Exiting...")
                break
    except KeyboardInterrupt:
        print("\nStopping client...")


