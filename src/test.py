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
        print("\n[INFO]      Stopping server\n")
        node.stop_server()


def test_client():
    time.sleep(1)

    node = P2P(host='127.0.0.1', port=5001)
    peer_socket = node.connect_to_peer('127.0.0.1', 5000)
    
    if peer_socket:
        print("\n[INFO]      Sending HELLO")
        node.send_message(peer_socket, {
            'type': 'HELLO',
            'sender': f'{node.host}:{node.port}'
        })
        
        time.sleep(1)
        
        print("\n[INFO]      Sending PING")
        node.send_message(peer_socket, {
            'type': 'PING',
            'timestamp': time.time()
        })
        
        time.sleep(1)
        
        print("\n[INFO]      Sending MESSAGE")
        node.send_message(peer_socket, {
            'type': 'MESSAGE',
            'content': 'Hello, World!'
        })
        
        time.sleep(1)
        peer_socket.close()

def test_peer(port, connect_to_port=None):
    node = P2P(host='127.0.0.1', port=port)
    node.start_server()
    
    if connect_to_port:
        time.sleep(2)
        print(f"\n[PEER {port}] Connecting to peer on port {connect_to_port}...")
        node.connect_to_peer('127.0.0.1', connect_to_port)
    
    while True:
        try:
            time.sleep(10)
            node.list_peers()
        except KeyboardInterrupt:
            node.stop_server()
            break


def main():
    print("P2P PEER DISCOVERY TEST")
    print("\nStarting 3 peers:")
    print("Peer 1: Port 5000 (Bootstrap peer)")
    print("Peer 2: Port 5001 (Connects to 5000)")
    print("Peer 3: Port 5002 (Connects to 5001)")
    
    peer1_thread = threading.Thread(target=test_peer, args=[5000])
    peer1_thread.daemon = True
    peer1_thread.start()
    
    time.sleep(2)
    
    peer2_thread = threading.Thread(target=test_peer, args=[5001, 5000])
    peer2_thread.daemon = True
    peer2_thread.start()
    
    time.sleep(2)
    
    peer3_thread = threading.Thread(target=test_peer, args=[5002, 5001])
    peer3_thread.daemon = True
    peer3_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[INFO]      Demo completed!")


if __name__ == "__main__":
    main()
