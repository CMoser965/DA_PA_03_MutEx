# Distributed Mutex Library - README

## Overview

This library implements a **Distributed Mutex** using **Maekawa’s Algorithm** for mutual exclusion in a distributed system. It allows multiple hosts (nodes) in a distributed environment to request, acquire, and release locks (mutexes) to safely enter a critical section. The algorithm ensures that only one node can access the critical section at a time, even in the presence of concurrent requests.

The library leverages **vector clocks** to maintain causal ordering of events across nodes and uses TCP sockets for inter-node communication. The quorums required by Maekawa’s algorithm are computed dynamically based on the total number of hosts in the system.

## Design

### Key Components

1. **`Message` Class**:
   - Encapsulates message data exchanged between nodes, including:
     - `msg_type`: Type of message (`REQUEST`, `RELEASE`, etc.).
     - `timestamp`: Vector clock timestamp of the sender.
     - `sender_id`: ID of the sending node.

2. **`VectorClock` Class**:
   - Manages vector clock logic for maintaining causality across nodes.
   - Key methods:
     - `increment(index)`: Increments the clock value at the given index.
     - `update(timestamp, sender_id)`: Updates the local vector clock based on received timestamp.
     - `get_clock()`: Returns the current vector clock state.

3. **`CDistributedMutex` Class**:
   - Core class that implements Maekawa's algorithm for distributed mutual exclusion.
   - Main responsibilities:
     - **Initialization**:
       - `GlobalInitialize(this_host, hosts)`: Initializes the node, its vector clock, and starts the server for incoming connections.
       - `MInitialize(votingGroupHosts)`: Establishes connections to nodes in the voting group (quorum).
     - **Critical Section Handling**:
       - `MLockMutex(callback)`: Sends a lock request to the quorum and, upon receiving the necessary votes, executes the provided callback function.
       - `MReleaseMutex()`: Releases the lock and informs quorum members.
     - **Communication**:
       - `start_server()`: Starts a socket server to listen for incoming connections.
       - `multicast_to_quorum(msg)`: Sends a message to all members of the quorum.
       - `handle_message(conn)`: Processes incoming messages and updates the vector clock.
     - **Quorum Formation**:
       - `form_quorum(node_id, total_nodes)`: Forms a quorum based on the total number of nodes using a mathematical approach for equal-sized quorums.

4. **Critical Section Callback**:
   - The critical section is defined as a callback function that simulates work being done while holding the lock. In the example, it sleeps for 5 seconds.

### Assumptions

- **Reliable Network**: The implementation assumes that the underlying network is reliable, i.e., no message loss or node failures.
- **Fixed Node Count**: The quorum size is determined by the total number of nodes, which is assumed to be known at initialization.
- **TCP Sockets**: Communication between nodes is done using TCP sockets, ensuring a reliable connection between hosts.
- **Localhost Configuration**: The example provided uses `localhost` for all hosts, but this can be modified to use different machines/IPs in a real-world setup.

## Testing the Project

### Prerequisites

- Python 3.x installed.
- The following Python standard libraries are used and don't need additional installation:
  - `socket`
  - `threading`
  - `pickle`
  - `heapq`
  - `json`

### Step-by-Step Instructions to Compile and Run

1. **Download the Project Files**:
   - Ensure you have the following files in the project directory:
     - `CDistributedMutex.py`: Contains the implementation of Maekawa's algorithm.
     - `main.py`: The entry point for running a node. This file is only to simulate library usage and can be replaced with your own test cases. This section describes usage with the entry point used in this repository.
     - `hosts.json`: Configuration file with a list of hosts in the distributed system.

2. **Configure `hosts.json`**:
   - Modify the `hosts.json` file to reflect your setup. Here is the sample format for 4 hosts:
     ```json
     {
         "hosts": [
             {"host": "localhost", "port": 5000},
             {"host": "localhost", "port": 5001},
             {"host": "localhost", "port": 5002},
             {"host": "localhost", "port": 5003}
         ]
     }
     ```
   - Replace `localhost` with the appropriate IP addresses if running across different machines.

3. **Run the Program**:
   - Open a terminal for each node (host) you want to run.
   - Start each node by specifying its index (as per the `hosts.json` file). For example:
     ```bash
     python3 main.py 0  # For node 0
     python3 main.py 1  # For node 1
     python3 main.py 2  # For node 2
     python3 main.py 3  # For node 3
     ```

4. **Critical Section Simulation**:
   - Once the nodes are running, they will automatically request locks and enter their critical section. The critical section is simulated with a 5-second pause (`time.sleep(5)`).
   - The critical section is displayed as:
     ```
     ~CRITICAL SECTION~
     ```

5. **Cleanup**:
   - To stop the program, press `Ctrl+C` in the terminal for each node.
   - This will trigger the `MCleanup()` method to close the open connections and release resources.

### Sample Output

You should see the nodes coordinating their lock requests and entering the critical section one at a time. Example log:
