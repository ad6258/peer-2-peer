import socket
import threading
import json
import time
from p2p import P2P
from pathlib import Path


def create_demo_files(peer_num):
    """
    Create some demo files in the shared folder
    """
    shared_dir = Path(f'shared_{peer_num}')
    shared_dir.mkdir(exist_ok=True)
    
    # Create different files for each peer
    files = {
        1: [('report.txt', 1024), ('document.pdf', 2048), ('video.mp4', 5120)],
        2: [('presentation.ppt', 3072), ('music.mp3', 4096), ('data.csv', 512)]
    }
    
    for filename, size in files.get(peer_num, []):
        filepath = shared_dir / filename
        with open(filepath, 'w') as f:
            # Write content to reach approximate size
            content = f"Demo file content from Peer {peer_num}: {filename}\n"
            f.write(content * (size // len(content)))
    
    print(f"[SETUP] Created demo files for Peer {peer_num}")



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
    """
    Demo: File indexing and querying between peers
    """
    print("=" * 70)
    print("P2P FILE INDEXING DEMO - STEP 4")
    print("=" * 70)
    print("\nSetup:")
    print("  Peer 1 (Port 5000): report.txt, document.pdf, video.mp4")
    print("  Peer 2 (Port 5001): presentation.ppt, music.mp3, data.csv")
    print("\nStarting network...\n")
    
    # Create demo files
    create_demo_files(1)
    create_demo_files(2)
    
    # Start Peer 1
    peer1 = P2P('127.0.0.1', 5000, 'shared_1')
    peer1.start_server()
    time.sleep(1)
    
    # Start Peer 2
    peer2 = P2P('127.0.0.1', 5001, 'shared_2')
    peer2.start_server()
    peer2.connect_to_peer('127.0.0.1', 5000)
    time.sleep(2)
    
    # Show local files on each peer
    print("\nLOCAL FILE INDEXES")
    peer1.list_files()
    peer2.list_files()
    
    # Peer 1 requests file list from Peer 2
    print("PEER 1 -> Requesting file list from PEER 2")
    peer1.request_peer_file_list('127.0.0.1', 5001)
    
    time.sleep(1)
    
    # Peer 2 requests file info from Peer 1
    print("\n" + "="*70)
    print("PEER 2 → Requesting file info for 'video.mp4' from PEER 1")
    print("="*70)
    peer2.request_file_info('127.0.0.1', 5000, 'video.mp4')
    
    time.sleep(1)
    
    # Peer 1 requests non-existent file
    print("\n" + "="*70)
    print("PEER 1 → Requesting file info for 'nonexistent.txt' from PEER 2")
    print("="*70)
    peer2.request_file_info('127.0.0.1', 5001, 'nonexistent.txt')
    
    print("\n[INFO] Demo completed! Press Ctrl+C to exit")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        peer1.stop_server()
        peer2.stop_server()


if __name__ == "__main__":
    main()