import os, sys, json
from CDistributedMutex import CDistributedMutex
import time

def load_hosts(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        return [(host_info['host'], host_info['port']) for host_info in data['hosts']]

def get_node_index():
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <host_index>")
        sys.exit(1)
    print(f"NODE ID: {sys.argv[1]}")
    return int(sys.argv[1]) 

def critical_section():
    print("~CRITICAL SECTION~")
    time.sleep(5)

if __name__ == "__main__":
    hosts = load_hosts('hosts.json')
    print(f"Loaded node information: {hosts}")
    my_host_index = get_node_index()  

    mutex = CDistributedMutex(hostname=f"{hosts[my_host_index][0]}:{hosts[my_host_index][1]}")
    voting_group = mutex.GlobalInitialize(my_host_index, hosts)

    # Initialize Maekawa's algorithm with a quorum
    mutex.MInitialize(voting_group)

    try:
        while True:
            # Request the lock (this will block until the lock is acquired)
            mutex.MLockMutex(callback=critical_section)
            # Release the lock
            mutex.MReleaseMutex()
    except KeyboardInterrupt:
        # Cleanup
        mutex.MCleanup()
