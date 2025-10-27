import socket 
import os, sys, time
from queue import Queue, Empty
from multiprocessing.managers import SyncManager
from threading import Thread
from flask import Flask, render_template

# --- Flask App for Dashboard ---
app = Flask(__name__)
# Silence Flask's default GET/POST logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- Global Placeholders ---
job_queue = None
result_queue = None
monitor_queue = None
connected_clients = None

@app.route('/')
def index():
    """Renders the sync server dashboard."""
    
    def get_queue_snapshot(q):
        """Safely gets a snapshot of a multiprocessing queue."""
        if not q:
            return []
        
        items = [] 
        try:
            # Get up to 5 items without blocking
            for _ in range(5):
                items.append(q.get_nowait())
        except Empty:
            pass # Queue has fewer than 5 items or is empty
        finally:
            # IMPORTANT: Put all the items back on the queue
            for item in reversed(items):
                q.put(item)
        return items

    job_snapshot = get_queue_snapshot(job_queue)
    result_snapshot = get_queue_snapshot(result_queue)
    monitor_snapshot = get_queue_snapshot(monitor_queue)
    
    # Categorize connected clients
    dss_servers = []
    mining_clients = []
    if connected_clients is not None:
        for client_id in connected_clients:
            if client_id.startswith('SERVER-'):
                dss_servers.append(client_id)
            else:
                mining_clients.append(client_id)

    stats = {
        "job_queue_size": job_queue.qsize() if job_queue else 0,
        "result_queue_size": result_queue.qsize() if result_queue else 0,
        "monitor_queue_size": monitor_queue.qsize() if monitor_queue else 0,
        "dss_servers": dss_servers,
        "mining_clients": mining_clients
    }
    
    snapshots = {
        "job_queue": [str(item)[:100] + '...' for item in job_snapshot],
        "result_queue": [str(item)[:100] + '...' for item in result_snapshot],
        "monitor_queue": [str(item)[:100] + '...' for item in monitor_snapshot]
    }
    
    return render_template('sync_dashboard.html', stats=stats, snapshots=snapshots)

# --- SyncManager Setup ---
class DistributedSyncServer(SyncManager):
    pass

def run_sync_server():
    """Initializes and runs the SyncManager server."""
    try:
        server_address = ('0.0.0.0', 8625)
        authkey = bytes("769ac424-adb6-5a73-83b0-d22eb27e543b", 'utf-8')

        # Register the shared objects using callables that point to the globals
        DistributedSyncServer.register('get_queue', callable=lambda: job_queue)
        DistributedSyncServer.register('result_queue', callable=lambda: result_queue)
        DistributedSyncServer.register('monitor_queue', callable=lambda: monitor_queue)
        DistributedSyncServer.register('get_clients', callable=lambda: connected_clients)

        dss = DistributedSyncServer(address=server_address, authkey=authkey)
        s = dss.get_server()

        print(f"DSS Sync Server started at port 8625")
        print("Accepting connections...")
        s.serve_forever()
        
    except (KeyboardInterrupt, SystemExit):
        print("\nShutting down sync server...")
    except Exception as e:
        print(f"Error starting sync server: {e}")

if __name__ == '__main__':
    # This block is only executed when the script is run directly
    
    # 1. Create and start the manager
    manager = SyncManager()
    manager.start()

    # 2. Create the shared objects from the manager
    #    and assign them to the global variables.
    globals().update({
        "job_queue": manager.Queue(),
        "result_queue": manager.Queue(),
        "monitor_queue": manager.Queue(),
        "connected_clients": manager.list()
    })

    # 3. Run the SyncManager in a separate thread
    sync_thread = Thread(target=run_sync_server, daemon=True)
    sync_thread.start()
    
    # 4. Run the Flask web server in the main thread
    print(f"Sync Server Dashboard running at http://127.0.0.1:8626")
    app.run(host='0.0.0.0', port=8626, debug=False)



