
# stratum_pool_server.py
import socketserver
import threading
import time
import json
import uuid

# --- Configuration ---
# This is the address and port the mock stratum server will listen on.
# '0.0.0.0' means it will accept connections from any network interface.
HOST, PORT = '0.0.0.0', 3333

# --- Mock Job Factory ---
# This class is responsible for creating new, random mining jobs.
# In a real pool, this component would communicate with a coin's node
# to get real block templates.
class JobFactory:
    def __init__(self):
        self.height = 1000

    def create_job(self):
        """
        Generates a new mock job template.
        """
        self.height += 1
        job_id = str(uuid.uuid4())
        # The 'blob' is a hexadecimal string representing the block header data
        # that miners will hash. Here, it's just random data.
        blob = uuid.uuid4().hex
        # The 'target' defines the difficulty. Hashes must be below this value.
        target = "ffff0000" + "00" * 28 # Low difficulty for demonstration
        
        print(f"Created new job {job_id[:8]}... at height {self.height}")
        
        return {
            "id": job_id,
            "blob": blob,
            "target": target,
            "height": self.height,
            "job_id": job_id # Some clients expect job_id at the top level
        }

# --- Stratum Request Handler ---
# This class handles the communication with a single connected client (like dssserver).
# An instance of this class is created for each client that connects.
class StratumTCPHandler(socketserver.BaseRequestHandler):
    
    def handle(self):
        """
        This method is called once for each client connection.
        It handles the entire lifecycle of the client's session.
        """
        print(f"Client connected from {self.client_address[0]}:{self.client_address[1]}")
        self.server.add_client(self)
        self.is_connected = True

        try:
            # The main loop to process incoming messages from the client.
            while self.is_connected:
                # Read data from the client, up to 1024 bytes.
                # The .strip() removes any leading/trailing whitespace.
                data = self.request.recv(1024).strip()
                if not data:
                    # If no data is received, the client has likely disconnected.
                    break

                # Messages are expected to be JSON, separated by newlines.
                for line in data.decode('utf-8').split('\\n'):
                    if not line:
                        continue
                    
                    message = json.loads(line)
                    print(f"Received from client: {message}")

                    # Handle the message based on its 'method' field.
                    method = message.get('method')
                    if method == 'login':
                        self.handle_login(message)
                    elif method == 'submit':
                        self.handle_submit(message)

        except (ConnectionResetError, BrokenPipeError):
            print(f"Client {self.client_address[0]} disconnected unexpectedly.")
        except Exception as e:
            print(f"An error occurred with client {self.client_address[0]}: {e}")
        finally:
            # This block ensures that cleanup happens even if errors occur.
            print(f"Closing connection to {self.client_address[0]}")
            self.is_connected = False
            self.server.remove_client(self)

    def handle_login(self, message):
        """
        Handles the initial login request from the client.
        In a real pool, this would authenticate the user's wallet address.
        """
        # Respond with a success message. The client needs this to confirm the connection.
        response = {
            "id": message.get('id'),
            "jsonrpc": "2.0",
            "result": {
                "id": "session-" + uuid.uuid4().hex,
                "job": self.server.job_factory.create_job(),
                "status": "OK"
            }
        }
        self.send(response)

    def handle_submit(self, message):
        """
        Handles a share submission from the client.
        In a real pool, this would validate the hash and check if it meets the target.
        """
        # For this mock server, we'll just accept every share as valid.
        print(f"Accepted share for job {message.get('params', {}).get('job_id', '')[:8]}...")
        response = {
            "id": message.get('id'),
            "jsonrpc": "2.0",
            "result": {"status": "OK"}
        }
        self.send(response)

    def send(self, data):
        """
        Serializes a Python dictionary to a JSON string and sends it to the client.
        A newline character is appended, as this is standard for the Stratum protocol.
        """
        try:
            message = json.dumps(data) + '\\n'
            self.request.sendall(message.encode('utf-8'))
        except (ConnectionResetError, BrokenPipeError):
            # If the client disconnects while we're trying to send,
            # we update the connection status to stop the send loop.
            self.is_connected = False


# --- Threaded TCP Server ---
# This class extends the standard library's TCPServer to add features like
# client tracking and periodic job broadcasting.
class StratumPoolServer(socketserver.ThreadingTCPServer):
    
    def __init__(self, server_address, RequestHandlerClass):
        # Call the parent class's constructor.
        super().__init__(server_address, RequestHandlerClass)
        # Allow the server to reuse the address quickly after being shut down.
        self.allow_reuse_address = True
        # A list to keep track of all connected clients.
        self.clients = []
        # A lock to prevent race conditions when multiple threads access the client list.
        self.client_lock = threading.Lock()
        # An instance of our mock job creator.
        self.job_factory = JobFactory()
        # A flag to control the main server loop.
        self.is_running = False

    def add_client(self, client):
        """Adds a client to the list of active clients."""
        with self.client_lock:
            self.clients.append(client)

    def remove_client(self, client):
        """Removes a client from the list."""
        with self.client_lock:
            if client in self.clients:
                self.clients.remove(client)

    def broadcast_job(self):
        """
        Creates a new job and sends it to all connected clients.
        This simulates the pool sending out new work when a new block is found on the network.
        """
        new_job = self.job_factory.create_job()
        message = {
            "jsonrpc": "2.0",
            "method": "job",
            "params": new_job
        }
        
        # We iterate over a copy of the list because a client might disconnect
        # during the broadcast, which would modify the list and cause an error.
        with self.client_lock:
            for client in list(self.clients):
                if client.is_connected:
                    client.send(message)
                else:
                    # Clean up any clients that are no longer connected.
                    self.remove_client(client)

    def start(self):
        """
        Starts the server and the periodic job broadcast thread.
        """
        self.is_running = True
        # The main server loop is run in a separate thread so it doesn't block
        # the rest of the script (like the broadcast loop).
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Mock Stratum Pool Server listening on {HOST}:{PORT}")

        # This loop will run in the main thread, broadcasting a new job every 10 seconds.
        while self.is_running:
            try:
                time.sleep(10)
                self.broadcast_job()
            except KeyboardInterrupt:
                # This allows us to shut down the server gracefully with Ctrl+C.
                print("\\nShutting down server...")
                self.is_running = False
                self.shutdown()
                self.server_close()
                break

# --- Main Execution Block ---
if __name__ == "__main__":
    # This block is executed when the script is run directly.
    server = StratumPoolServer((HOST, PORT), StratumTCPHandler)
    server.start()
