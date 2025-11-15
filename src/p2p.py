import socket
import threading
import hashlib
import json
import time


class P2P:

    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.peers = {}
        self.peer_id = f"{host}:{port}"
        self.heartbeat_interval = 10

    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"[SERVER]    Started on {self.host}:{self.port}")
            print(f"[SERVER]    Waiting for connections")

            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()

            heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
            heartbeat_thread.daemon = True
            heartbeat_thread.start()

            cleanup_thread = threading.Thread(target=self.cleanup_dead_peers)
            cleanup_thread.daemon = True
            cleanup_thread.start()
        except Exception as e:
            print(f"[ERROR]     Failed to start server: {e}")

    def accept_connections(self):
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"[SERVER]    New connection from {address}")

                client_thread = threading.Thread(
                                    target=self.handle_client,
                                    args=[client_socket, address]
                                )
                client_thread.daemon = True
                client_thread.start()

            except Exception as e:
                if self.running:
                    print(f"[ERROR]    Error accepting connection: {e}")

    def handle_client(self, client_socket, address):
        try:
            while self.running:
                data = client_socket.recv(4096)
            
                if not data:
                    print(f"[SERVER]    Connection closed by {address}")
                    break

                message = json.loads(data.decode('utf-8'))
                print(f"[SERVER]    Received from {address}: {message}")

                response = self.process_message(message, address)

                if response:
                    client_socket.send(json.dumps(response).encode('utf-8'))

        except json.JSONDecodeError:
            print(f"[ERROR]    Invalid JSON from {address}")
        except Exception as e:
            print(f"[ERROR]    Error handling client {address}: {e}")
        finally:
            client_socket.close()
            print(f"[SERVER]    Closed connection with {address}")

    def process_message(self, message, address):
        msg_type = message.get('type')

        if msg_type == 'PEER_DISCOVERY':
            peer_info = message.get('peer_info')
            print(f"[SERVER]    Received PEER_DISCOVERY from {address}, peer info: {peer_info}")
            self.add_peer(peer_info)
            return {
                'type': 'PEER_DISCOVERY_RESPONSE',
                'peer_info': {
                    'peer_id': self.peer_id,
                    'host': self.host,
                    'port': self.port
                },
                'known_peers': list(self.peers.values())
            }

        elif msg_type == 'HEARTBEAT':
            peer_id = message.get('peer_id')
            print(f"[SERVER]    Received HEARTBEAT from {address}, {peer_id}")
            if peer_id in self.peers:
                self.peers[peer_id]['last_seen'] = time.time()
            return {
                'type': 'HEARTBEAT_ACK',
                'peer_id': self.peer_id,
                'timestamp': time.time()
            }

        elif msg_type == 'GET_PEERS':
            print(f"[SERVER]    Received GET_PEERS from {address}")
            return {
                'type': 'PEER_LIST',
                'peers': list(self.peers.values())
            }

        elif msg_type == "HELLO":
            print(f"[SERVER]    Received HELLO from {address}")
            return {
                'type': 'HELLO_RESP',
                'status': 'success',
                'message': f'Hello from {self.host}:{self.port}'
            }

        elif msg_type == "PING":
            print(f"[SERVER]    Received PING from {address}")
            return {
                'type': 'PONG',
                'status': 'success',
                'timestamp': time.time()
            }

        elif msg_type == 'MESSAGE':
            content = message.get('content', '')
            print(f"[SERVER]    Message from {address}: {content}")
            return {
                'type': 'ACK',
                'status': 'received'
            }

        else:
            print(f"[SERVER]    Unknown message type: {msg_type}")
            return {
                'type': 'ERROR',
                'status': 'unknown_type',
                'message': f'Unknown message type: {msg_type}'
            }

    def add_peer(self, peer_info):
        peer_id = peer_info.get('peer_id')
        if peer_id and peer_id != self.peer_id:
            self.peers[peer_id] = {
                'peer_id': peer_id,
                'host': peer_info.get('host'),
                'port': peer_info.get('port'),
                'last_seen': time.time()
            }
            print(f"[DISCOVERY] Added peer: {peer_id}")


    def connect_to_peer(self, peer_host, peer_port):
        try:
            print(f"[CLIENT]    Connecting to {peer_host}:{peer_port}")

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((peer_host, peer_port))

            print(f"[CLIENT]    Connected to {peer_host}:{peer_port}")

            discovery_msg = {
                'type': 'PEER_DISCOVERY',
                'peer_info': {
                    'peer_id': self.peer_id,
                    'host': self.host,
                    'port': self.port
                }
            }
            
            client_socket.send(json.dumps(discovery_msg).encode('utf-8'))

            response_data = client_socket.recv(4096)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                
                self.add_peer(response.get('peer_info'))
                
                known_peers = response.get('known_peers', [])
                for peer in known_peers:
                    self.add_peer(peer)

                print(f"[DISCOVERY] Discovered {len(known_peers)} peers")

            client_socket.close()
            return True

        except Exception as e:
            print(f"[ERROR]    Failed to connect to {peer_host}:{peer_port}: {e}")
            return None

    def announce_to_peers(self):
        for peer_id, peer_info in list(self.peers.items()):
            try:
                self.connect_to_peer(peer_info['host'], peer_info['port'])
            except:
                pass
    
    def loop_heartbeat(self):
        while self.running:
            time.sleep(self.heartbeat_interval)
            for peer_id, peer_info in list(self.peers.items()):
                try:
                    self.send_heartbeat(peer_info['host'], peer_info['port'])
                except:
                    pass

    def send_heartbeat(self, peer_host, peer_port):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)
            client_socket.connect((peer_host, peer_port))

            heartbeat_msg = {
                'type': 'HEARTBEAT',
                'peer_id': self.peer_id,
                'timestamp': time.time()
            }
            client_socket.send(json.dumps(heartbeat_msg).encode('utf-8'))

            response_data = client_socket.recv(4096)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                if response.get('type') == 'HEARTBEAT_ACK':
                    peer_id = f"{peer_host}:{peer_port}"
                    if peer_id in self.peers:
                        self.peers[peer_id]['last_seen'] = time.time()
            
            client_socket.close()
        
        except:
            pass

    def cleanup_dead_peers(self):
        timeout = 30

        while self.running:
            time.sleep(15)
            current_time = time.time()
            dead_peers = []
            for peer_id, peer_info in self.peers.items():
                last_seen = peer_info.get('last_seen', 0)
                if current_time - last_seen > timeout:
                    dead_peers.append(peer_id)

            for peer_id in dead_peers:
                print(f"[CLEANUP]   Removing dead peer: {peer_id}")
                del self.peers[peer_id]

    def list_peers(self):
        print(f"[INFO]      Known Peers ({len(self.peers)}):")
        if not self.peers:
            print("[INFO]      No peers connected yet.")
        else:
            for peer_id, peer_info in self.peers.items():
                last_seen = peer_info.get('last_seen', 0)
                time_ago = int(time.time() - last_seen)
                print(f"  • {peer_id} (last seen {time_ago}s ago)")

    def send_message(self, peer_socket, message):
        try:
            message_json = json.dumps(message)
            peer_socket.send(message_json.encode('utf-8'))
            print(f"[CLIENT]    Sent message")

            response_data = peer_socket.recv(4096)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                print(f"[CLIENT]    Received response: {response}")
                return response

        except Exception as e:
            print(f"[ERROR]    Failed to send message: {e}")
            return None

    def stop_server(self):
        """
        Stop the server and close all connections
        """
        print("[SERVER]    Shutting down\n")
        self.running = False
        if self.server_socket:
            self.server_socket.close()


