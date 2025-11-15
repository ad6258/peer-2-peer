import socket
import threading
import json
import time
from p2p import P2P

def test_server():
    node = P2P(host='127.0.0.1', port=5000)
    node.start_server()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping server\n")
        node.stop_server()


def test_client():
    time.sleep(1)

    node = P2P(host='127.0.0.1', port=5001)
    peer_socket = node.connect_to_peer('127.0.0.1', 5000)
    
    if peer_socket:
        print("\n[INFO] Sending HELLO")
        node.send_message(peer_socket, {
            'type': 'HELLO',
            'sender': f'{node.host}:{node.port}'
        })
        
        time.sleep(1)
        
        print("\n[INFO] Sending PING")
        node.send_message(peer_socket, {
            'type': 'PING',
            'timestamp': time.time()
        })
        
        time.sleep(1)
        
        print("\n[INFO] Sending MESSAGE")
        node.send_message(peer_socket, {
            'type': 'MESSAGE',
            'content': 'Hello, World!'
        })
        
        time.sleep(1)
        peer_socket.close()


def main():
    server_thread = threading.Thread(target=test_server)
    server_thread.daemon = True
    server_thread.start()
    
    client_thread = threading.Thread(target=test_client)
    client_thread.daemon = True
    client_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Test completed\n")


if __name__ == "__main__":
    main()
