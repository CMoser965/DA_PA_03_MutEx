import threading
import socket
import pickle
import heapq
import IDistributedMutex

class Message:
    def __init__(self, msg_type, timestamp, sender_id):
        self.msg_type = msg_type
        self.timestamp = timestamp
        self.sender_id = sender_id

class VectorClock:
    def __init__(self, size, hostname):
        self.clock = [0] * size
        self.hostname = hostname

    def increment(self, index):
        self.clock[index] += 1

    def update(self, timestamp, sender_id):
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], timestamp[i])
        self.increment(sender_id)

    def get_clock(self):
        return self.clock

class CDistributedMutex:
    def __init__(self, hostname):
        self.vector_clock = None
        self.host_id = None
        self.hosts = []
        self.voting_group = []
        self.quorum_connections = {}
        self.request_queue = []  # Queue for outstanding requests
        self.in_critical_section = False
        self.current_votes = 0
        self.curr_req = None
        self.vote_granted = False
        self.waiting_for_votes = False
        self.lock = threading.Lock()
        self.hostname = hostname
        self.condition = threading.Condition()
        self.server_socket = None
        self.locked = False  # Flag for current lock status
        self.current_lock_request = None  # The current locking request details

    def GlobalInitialize(self, this_host, hosts):
        self.host_id = this_host
        self.hosts = hosts
        self.vector_clock = VectorClock(len(hosts), self.hostname)
        self.start_server()
        self.voting_group = self.form_quorum(self.host_id, len(hosts))
        print(f"Voting group for {self.hostname}: {self.voting_group}")
        return self.voting_group
    
    def MCleanup(self):
        for conn in self.quorum_connections.values():
            conn.close()
        self.quorum_connections.clear()
        if self.server_socket:
            self.server_socket.close()

    def MInitialize(self, votingGroupHosts):
        with self.lock:
            self.quorum_connections = {}
            while len(self.quorum_connections.keys()) < len(votingGroupHosts):
                for host_index in self.voting_group:
                    host, port = self.hosts[host_index]
                    try:
                        conn = socket.create_connection((host, port))
                        self.quorum_connections[host_index] = conn
                    except Exception as e:
                        continue
    
    def MLockMutex(self, callback):
        with self.lock:
            self.waiting_for_votes = True
            self.locked = True

        req = self.buildMessage("REQUEST")
        self.multicast_to_quorum(req)
        self.critical_section_callback = callback


    def MReleaseMutex(self):
        with self.lock:
            self.waiting_for_votes = False
            self.locked = False
            self.in_critical_section = False
        release = self.buildMessage("RELEASE")
        self.multicast_to_quorum(release)

    def start_server(self):
        host, port = self.hosts[self.host_id]
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)

        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_message, args=(conn,), daemon=True).start()

    def buildMessage(self, msg):
        return Message(msg, self.vector_clock.get_clock(), self.host_id)

    def multicast_to_quorum(self, msg):
        data = pickle.dumps(msg)
        for host_index, conn in self.quorum_connections.items():
            try:
                conn.sendall(data)
            except Exception as e:
                return False
        return True

    def handle_request(self, msg):
        with self.lock:
            request_priority = (msg.timestamp, msg.sender_id)
            if self.in_critical_section or self.locked:
                heapq.heappush(self.request_queue, request_priority)
            else:
                # Grant the lock and send LOCKED message
                self.multicast_to_quorum(msg)
                self.locked = True
                self.current_lock_request = request_priority
                self.send_lock_granted(msg.sender_id)


    def send_lock_granted(self, target_process_id):
        try:
            if target_process_id in self.quorum_connections:
                conn = self.quorum_connections[target_process_id]
                with self.lock:
                    self.vector_clock.increment(self.host_id)
                    locked_msg = Message("LOCKED", self.vector_clock.get_clock(), self.host_id)
                    conn.sendall(pickle.dumps(locked_msg))
                self.send_inquiry(target_process_id)
        except Exception as e:
            print(f"Failed to send LOCKED message to {target_process_id}: {e}")

    def send_inquiry(self, target_process_id):
        with self.lock:
            inquire = self.buildMessage("INQUIRE")
            self.quorum_connections[target_process_id].sendall(pickle.dumps(inquire))

    def handle_release(self, msg):
        with self.lock:
            self.locked = False  # Release the lock
            if self.request_queue:
                next_request = heapq.heappop(self.request_queue)
                self.send_lock_granted(next_request[1])  # Send LOCKED message to the next requester

    def handle_inquire(self, msg):
        with self.lock:
            if self.locked:  
                self.critical_section_callback()
                relinquish_msg = Message("RELINQUISH", self.vector_clock.get_clock(), self.host_id)
                self.quorum_connections[msg.sender_id].sendall(pickle.dumps(relinquish_msg))
            else:
                self.send_lock_granted(msg.sender_id)

    def handle_relinquish(self, msg):
        with self.lock:
            if self.locked:
                self.locked = False
                if self.request_queue:
                    next_request = heapq.heappop(self.request_queue)
                    self.send_lock_granted(next_request[1])

    def handle_message(self, conn):
        try:
            data = conn.recv(1024)
            if not data:
                return
            msg = pickle.loads(data)
            with self.lock:
                # Update vector clock on receiving a message
                self.vector_clock.update(msg.timestamp, msg.sender_id)
            formatted_timestamp = ', '.join(map(str, self.vector_clock.get_clock()))
            print(f"{self.hostname}:({formatted_timestamp})")

            if msg.msg_type == "REQUEST":
                self.handle_request(msg)
            elif msg.msg_type == "RELEASE":
                self.handle_release(msg)
            elif msg.msg_type == "INQUIRE":
                self.handle_inquire(msg)
            elif msg.msg_type == "RELINQUISH":
                self.handle_relinquish(msg)
            elif msg.msg_type == "OK":
                with self.condition:
                    self.current_votes += 1
                    self.condition.notify_all()
        except Exception as e:
            print(f"Error handling message: {e}")

    def form_quorum(self, node_id, total_nodes):
        quorum_size = int(total_nodes ** 0.5)  # Create quorums of size √N
        quorum = set()

        for i in range(total_nodes):
            if i // quorum_size == node_id // quorum_size or i % quorum_size == node_id % quorum_size:
                quorum.add(i)
        quorum.remove(self.host_id)
        return list(quorum)
