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
        self.peers = []

    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"[SERVER] Started on {self.host}:{self.port}")
            print(f"[SERVER] Waiting for connections")

            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")

    def accept_connections(self):
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"[SERVER] New connection from {address}")

                client_thread = threading.Thread(
                                    target=self.handle_client,
                                    args=[client_socket, address]
                                )
                client_thread.daemon = True
                client_thread.start()

            except Exception as e:
                if self.running:
                    print(f"[ERROR] Error accepting connection: {e}")

    def handle_client(self, client_socket, address):
        try:
            while self.running:
                data = client_socket.recv(4096)
            
                if not data:
                    print(f"[SERVER] Connection closed by {address}")
                    break

                message = json.loads(data.decode('utf-8'))
                print(f"[SERVER] Received from {address}: {message}")

                response = self.process_message(message, address)

                if response:
                    client_socket.send(json.dumps(response).encode('utf-8'))

        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON from {address}")
        except Exception as e:
            print(f"[ERROR] Error handling client {address}: {e}")
        finally:
            client_socket.close()
            print(f"[SERVER] Closed connection with {address}")

    def process_message(self, message, address):
        msg_type = message.get('type')

        if msg_type == "HELLO":
            print(f"[SERVER] Received HELLO from {address}")
            return {
                'type': 'HELLO_RESP',
                'status': 'success',
                'message': f'Hello from {self.host}:{self.port}'
            }

        elif msg_type == "PING":
            print(f"[SERVER] Received PING from {address}")
            return {
                'type': 'PONG',
                'status': 'success',
                'timestamp': time.time()
            }

        elif msg_type == 'MESSAGE':
            content = message.get('content', '')
            print(f"[SERVER] Message from {address}: {content}")
            return {
                'type': 'ACK',
                'status': 'received'
            }

        else:
            print(f"[SERVER] Unknown message type: {msg_type}")
            return {
                'type': 'ERROR',
                'status': 'unknown_type',
                'message': f'Unknown message type: {msg_type}'
            }

    def connect_to_peer(self, peer_host, peer_port):
        try:
            print(f"[CLIENT] Connecting to {peer_host}:{peer_port}")

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer_host, peer_port))

            print(f"[CLIENT] Connected to {peer_host}:{peer_port}")

            peer_address = f"{peer_host}:{peer_port}"
            if peer_address not in self.peers:
                self.peers.append(peer_address)

            return client_socket

        except Exception as e:
            print(f"[ERROR] Failed to connect to {peer_host}:{peer_port}: {e}")
            return None

    def send_message(self, peer_socket, message):
        try:
            message_json = json.dumps(message)
            peer_socket.send(message_json.encode('utf-8'))
            print(f"[CLIENT] Sent message")

            response_data = peer_socket.recv(4096)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                print(f"[CLIENT] Received response: {response}")
                return response

        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            return None

    def stop_server(self):
        """
        Stop the server and close all connections
        """
        print("[SERVER] Shutting down\n")
        self.running = False
        if self.server_socket:
            self.server_socket.close()


