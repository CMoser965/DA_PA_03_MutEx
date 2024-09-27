import socket
import threading
import pickle  # For message serialization
from queue import Queue
from typing import List
import heapq
import time


class VectorClock:
    def __init__(self, num_processes, hostname):
        self.clock = [0] * num_processes
        self.hostname = hostname

    def increment(self, process_id):
        self.clock[process_id] += 1
        self.print_timestamp()

    def update(self, other_clock, process_id):
        self.clock = [max(self.clock[i], other_clock[i]) for i in range(len(self.clock))]
        self.clock[process_id] += 1
        self.print_timestamp()

    def get_clock(self):
        return self.clock

    def print_timestamp(self):
        # Print the vector clock in the required format
        print(f"{self.hostname}:({','.join(map(str, self.clock))})")


class Message:
    def __init__(self, msg_type, timestamp, sender_id):
        self.msg_type = msg_type
        self.timestamp = timestamp
        self.sender_id = sender_id


class CDistributedMutex:
    def __init__(self, hostname):
        self.vector_clock = None
        self.host_id = None
        self.hosts = []
        self.voting_group = []
        self.quorum_connections = {}
        self.request_queue = []
        self.in_critical_section = False
        self.current_votes = 0
        self.vote_granted = False
        self.waiting_for_votes = False  # Initialize the attribute here
        self.lock = threading.Lock()
        self.hostname = hostname
        self.condition = threading.Condition()
        self.server_socket = None
    
    def GlobalInitialize(self, this_host, hosts):
        self.host_id = this_host
        self.hosts = hosts
        self.vector_clock = VectorClock(len(hosts), self.hostname)
        self.start_server()
        self.voting_group = self.form_quorum(self.host_id, len(hosts))
        print(f"Voting group for {self.hostname}: {self.voting_group}")
    
    def start_server(self):
        host, port = self.hosts[self.host_id]
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        print(f"Listening on {host}:{port}")

        # Start a thread to handle incoming connections
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_message, args=(conn,), daemon=True).start()

    def QuitAndCleanup(self):
        for conn in self.quorum_connections.values():
            conn.close()
        self.quorum_connections.clear()
        if self.server_socket:
            self.server_socket.close()

    def MInitialize(self, voting_group_hosts):
        self.quorum_connections = {}
        failed_connections = []
        for host_index in self.voting_group:
            host, port = self.hosts[host_index]
            try:
                conn = socket.create_connection((host, port))
                self.quorum_connections[host_index] = conn
                print(f"Connected to {host}:{port}")
            except Exception as e:
                print(f"Failed to connect to {host}:{port} - Possibly node is not initialized.")
                failed_connections.append(host_index)
        if(len(failed_connections) > 0):
            while len(self.quorum_connections) < len(self.voting_group):
                for host_index in failed_connections:
                    host, port = self.hosts[host_index]
                    try:
                        conn = socket.create_connection((host, port))
                        self.quorum_connections[host_index] = conn
                        print(f"Connected to {host}:{port}")
                        failed_connections.remove(host_index)
                    except Exception as e:
                        continue

        # Print the group formation
        group_hosts = [self.hosts[i] for i in voting_group_hosts]
        print(f"Voting group for {self.hostname}: {group_hosts}")
    
    def MLockMutex(self):
        print(f"{self.hostname} attempting to acquire lock.")
        
        with self.lock:
            self.vector_clock.increment(self.host_id)
            self.waiting_for_votes = True
        
        request = Message("REQUEST", self.vector_clock.get_clock(), self.host_id)
        self.multicast_to_quorum(request)

        with self.condition:
            while self.current_votes < len(self.voting_group):
                self.condition.wait()

        # Enter critical section only after all votes have been received
        print(f"{self.hostname} entered the critical section.")
        self.in_critical_section = True
        self.waiting_for_votes = False

    
    def MLockMutex(self):
        print(f"{self.hostname} attempting to acquire lock.")
        
        with self.lock:
            self.vector_clock.increment(self.host_id)
            self.waiting_for_votes = True
        
        request = Message("REQUEST", self.vector_clock.get_clock(), self.host_id)
        self.multicast_to_quorum(request)

        with self.condition:
            while self.current_votes < len(self.voting_group):
                self.condition.wait()

        # Enter critical section only after all votes have been received
        print(f"{self.hostname} entered the critical section.")
        self.in_critical_section = True
        self.waiting_for_votes = False
    
    def multicast_to_quorum(self, msg):
        data = pickle.dumps(msg)
        for host_index, conn in self.quorum_connections.items():
            try:
                conn.sendall(data)
            except Exception as e:
                print(f"Failed to send message to {host_index}: {e}")
                self.reconnect_to_process(host_index)
                try:
                    self.quorum_connections[host_index].sendall(data)
                except Exception as e:
                    print(f"Failed to send message to {host_index} after reconnection: {e}")
    
    def MLockMutex(self):
        print(f"{self.hostname} attempting to acquire lock.")
        
        with self.lock:
            self.vector_clock.increment(self.host_id)
            self.waiting_for_votes = True
        
        request = Message("REQUEST", self.vector_clock.get_clock(), self.host_id)
        self.multicast_to_quorum(request)

        with self.condition:
            while self.current_votes < len(self.voting_group):
                self.condition.wait()

        # Enter critical section only after all votes have been received
        print(f"{self.hostname} entered the critical section.")
        self.in_critical_section = True
        self.waiting_for_votes = False
    
    def handle_request(self, msg):
        with self.lock:
            request_priority = (msg.timestamp, msg.sender_id)
            if self.in_critical_section or self.vote_granted or self.waiting_for_votes:
                # Queue the request if already in critical section, vote granted, or waiting for votes
                heapq.heappush(self.request_queue, request_priority)
            else:
                # Grant the vote if conditions allow
                self.send_vote(msg.sender_id)
                self.vote_granted = True
    
    def handle_release(self, msg):
        with self.lock:
            self.vote_granted = False  # Release the lock
            if self.request_queue:
                # Grant vote to the next requester in the queue
                next_requestor = heapq.heappop(self.request_queue)[1]
                self.send_vote(next_requestor)
                print(f"{self.hostname} granted vote to {next_requestor}")
    
    def send_vote(self, target_process_id):
        try:
            if target_process_id in self.quorum_connections:
                conn = self.quorum_connections[target_process_id]
                with self.lock:
                    self.vector_clock.increment(self.host_id)
                    ok_msg = Message("OK", self.vector_clock.get_clock(), self.host_id)
                conn.sendall(pickle.dumps(ok_msg))
            else:
                print(f"No connection found for target process {target_process_id}. Attempting to reconnect.")
                self.reconnect_to_process(target_process_id)
                self.send_vote(target_process_id)  # Retry sending the vote after reconnecting
        except Exception as e:
            print(f"Failed to send vote to {target_process_id}: {e}")
    
    def reconnect_to_process(self, target_process_id):
        # Attempt to reconnect to the specified process
        host, port = self.hosts[target_process_id]
        try:
            conn = socket.create_connection((host, port))
            self.quorum_connections[target_process_id] = conn
            print(f"Reconnected to {host}:{port}")
        except Exception as e:
            print(f"Failed to reconnect to {host}:{port}: {e}")


    def form_quorum(self, node_id, total_nodes):
        quorum_size = int(total_nodes ** 0.5)  # Create quorums of size √N
        quorum = set()

        # Form a row and column-based quorum ensuring intersections
        for i in range(total_nodes):
            if i // quorum_size == node_id // quorum_size or i % quorum_size == node_id % quorum_size:
                quorum.add(i)
        quorum.remove(self.host_id)
        return list(quorum)

    def handle_message(self, conn):
        try:
            data = conn.recv(1024)
            msg = pickle.loads(data)
            with self.lock:
                # Update vector clock on receiving a message
                self.vector_clock.update(msg.timestamp, self.host_id)

            if msg.msg_type == "REQUEST":
                print(f"Got request for lock on socket")
                self.handle_request(msg)
            elif msg.msg_type == "RELEASE":
                print('Lock is released.')
                self.handle_release(msg)
            elif msg.msg_type == "OK":
                with self.condition:
                    self.current_votes += 1
                    self.condition.notify_all()
        except Exception as e:
            print(f"Error handling message: {e}")