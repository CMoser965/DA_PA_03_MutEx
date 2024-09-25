import socket
import threading
import pickle  # For message serialization
from queue import Queue
from typing import List


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
        self.quorum_connections = []
        self.request_queue = Queue()
        self.in_critical_section = False
        self.current_votes = 0
        self.vote_granted = False
        self.lock = threading.Lock()
        self.hostname = hostname  # Add the hostname for print statements
        self.server_socket = None  # Server socket for incoming connections
        self.condition = threading.Condition()  # Use Condition for thread synchronization
    
    def GlobalInitialize(self, this_host, hosts):
        self.host_id = this_host
        self.hosts = hosts
        self.vector_clock = VectorClock(len(hosts), self.hostname)
    
    def start_server(self):
        host, port = self.hosts[self.host_id]
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        if self.server_socket:
            self.server_socket.close()
        for conn in self.quorum_connections:
            conn.close()
        self.quorum_connections.clear()
    
    def MInitialize(self, voting_group_hosts):
        self.voting_group = voting_group_hosts
        self.quorum_connections = []
        for host_index in voting_group_hosts:
            host, port = self.hosts[host_index]
            try:
                conn = socket.create_connection((host, port))
                self.quorum_connections.append(conn)
            except Exception as e:
                print(f"Failed to connect to {host}:{port} - {e}")

        # Print the group formation
        group_hosts = [self.hosts[i] for i in voting_group_hosts]
        print(f"Voting group for {self.hostname}: {group_hosts}")
    
    def MLockMutex(self):
        # Step 1: Increment local vector clock before sending the request
        with self.lock:
            self.vector_clock.increment(self.host_id)
        
        # Step 2: Multicast the request to the quorum
        request = Message("REQUEST", self.vector_clock.get_clock(), self.host_id)
        self.multicast_to_quorum(request)

        # Step 3: Wait for the votes to be returned
        with self.condition:
            while self.current_votes < len(self.voting_group):
                self.condition.wait()  # Wait until enough votes are received

        # Step 4: Enter critical section
        self.in_critical_section = True
    
    def MReleaseMutex(self):
        if self.in_critical_section:
            # Step 5: Release the lock, multicast the release message to the quorum
            release = Message("RELEASE", self.vector_clock.get_clock(), self.host_id)
            self.multicast_to_quorum(release)

            # Reset state
            self.in_critical_section = False
            self.current_votes = 0
    
    def multicast_to_quorum(self, msg):
        for conn in self.quorum_connections:
            try:
                data = pickle.dumps(msg)
                conn.sendall(data)
            except Exception as e:
                print(f"Failed to send message: {e}")
    
    def handle_message(self, conn):
        try:
            data = conn.recv(1024)
            msg = pickle.loads(data)
            with self.lock:
                # Update vector clock on receiving a message
                self.vector_clock.update(msg.timestamp, self.host_id)

            if msg.msg_type == "REQUEST":
                self.handle_request(msg)
            elif msg.msg_type == "RELEASE":
                self.handle_release(msg)
            elif msg.msg_type == "OK":
                with self.condition:
                    self.current_votes += 1
                    self.condition.notify_all()  # Notify that a vote was received
        except Exception as e:
            print(f"Error handling message: {e}")
    
    def handle_request(self, msg):
        with self.lock:
            if self.in_critical_section or self.vote_granted:
                self.request_queue.put(msg.sender_id)
            else:
                self.send_vote(msg.sender_id)
                self.vote_granted = True
    
    def handle_release(self, msg):
        with self.lock:
            self.vote_granted = False
            if not self.request_queue.empty():
                next_requestor = self.request_queue.get()
                self.send_vote(next_requestor)
    
    def send_vote(self, target_process_id):
        try:
            host, port = self.hosts[target_process_id]
            conn = socket.create_connection((host, port))
            ok_msg = Message("OK", self.vector_clock.get_clock(), self.host_id)
            conn.sendall(pickle.dumps(ok_msg))
            conn.close()
        except Exception as e:
            print(f"Failed to send vote to {target_process_id}: {e}")

