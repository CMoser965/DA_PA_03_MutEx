import sys
from CDistributedMutex import CDistributedMutex
import time

if __name__ == "__main__":
    hosts = [("mutex-node-0", 5000), ("mutex-node-1", 5001), ("mutex-node-2", 5002), ("mutex-node-3", 5003)]
    
    # Get the host index from the command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <host_index>")
        sys.exit(1)

    my_host_index = int(sys.argv[1])  # Get the host index from the arguments

    # Initialize the distributed mutex
    mutex = CDistributedMutex(hostname=f"{hosts[my_host_index][0]}:{hosts[my_host_index][1]}")
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
