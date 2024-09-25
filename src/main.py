import sys
from CDistributedMutex import CDistributedMutex
import time

if __name__ == "__main__":
    # Hosts and voting group setup (assuming 3 hosts for simplicity)
    hosts = [("localhost", 5000), ("localhost", 5001), ("localhost", 5002)]
    
    # Get the host index from the command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <host_index>")
        sys.exit(1)

    my_host_index = int(sys.argv[1])  # Get the host index from the arguments

    # Initialize the distributed mutex
    mutex = CDistributedMutex(hostname=f"localhost:{hosts[my_host_index][1]}")
    mutex.GlobalInitialize(my_host_index, hosts)

    # Start the server to accept connections from other processes
    mutex.start_server()

    # Initialize Maekawa's algorithm with a quorum
    voting_group = [i for i in range(len(hosts)) if i != my_host_index]  # Everyone else is in the voting group
    mutex.MInitialize(voting_group)

    # Request the lock (this will block until the lock is acquired)
    mutex.MLockMutex()
    print("Entered critical section")

    # Simulate some critical section work
    time.sleep(2)

    # Release the lock
    mutex.MReleaseMutex()
    print("Exited critical section")

    # Cleanup
    mutex.QuitAndCleanup()
