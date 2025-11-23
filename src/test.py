import socket
import threading
import json
import time
from p2p import P2P
from pathlib import Path
import os


def create_demo_files(peer_num):
    """
    Create demo files for testing
    """
    import shutil
    
    shared_dir = Path(f'shared_{peer_num}')
    
    # Remove old directory if it exists
    if shared_dir.exists():
        shutil.rmtree(shared_dir)
    
    shared_dir.mkdir(exist_ok=True)
    
    files = {
        1: [('small_file.txt', 1024), ('medium_file.pdf', 50000), ('large_file.mp4', 200000)],
        2: [('document.txt', 2048), ('image.jpg', 75000)]
    }
    
    for filename, size in files.get(peer_num, []):
        filepath = shared_dir / filename
        with open(filepath, 'wb') as f:
            # Write random data to reach target size
            f.write(os.urandom(size))
    
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


def main_fileindexing():
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

def main_search():
    """
    Demo: Search functionality across multiple peers
    """
    print("=" * 50)
    print("P2P SEARCH FUNCTIONALITY DEMO - STEP 5")
    print("\nSetup:")
    print("  Peer 1 (Port 5000): report_2024.txt, document.pdf, video_tutorial.mp4")
    print("  Peer 2 (Port 5001): report_2024.txt, presentation.ppt, music_track.mp3")
    print("  Peer 3 (Port 5002): image_photo.jpg, data_analysis.csv, report_final.txt")
    print("\nStarting network...\n")
    
    # Create demo files
    create_demo_files(1)
    create_demo_files(2)
    create_demo_files(3)
    
    # Start peers
    peer1 = P2P('127.0.0.1', 5000, 'shared_1')
    peer1.start_server()
    time.sleep(1)
    
    peer2 = P2P('127.0.0.1', 5001, 'shared_2')
    peer2.start_server()
    peer2.connect_to_peer('127.0.0.1', 5000)
    time.sleep(1)
    
    peer3 = P2P('127.0.0.1', 5002, 'shared_3')
    peer3.start_server()
    peer3.connect_to_peer('127.0.0.1', 5001)
    time.sleep(2)
    
    # Test searches
    print("\n" + "="*70)
    print("SEARCH DEMONSTRATIONS")
    print("="*70)
    
    # Search 1: Find files with "report"
    print("\n>>> Peer 1 searching for 'report'")
    results = peer1.search_network('report')
    peer1.display_search_results(results)
    
    time.sleep(1)
    
    # Search 2: Find files with "music"
    print("\n>>> Peer 2 searching for 'music'")
    results = peer2.search_network('music')
    peer2.display_search_results(results)
    
    time.sleep(1)
    
    # Search 3: Find files with "data"
    print("\n>>> Peer 3 searching for 'data'")
    results = peer3.search_network('data')
    peer3.display_search_results(results)
    
    time.sleep(1)
    
    # Search 4: Search for non-existent file
    print("\n>>> Peer 1 searching for 'nonexistent'")
    results = peer1.search_network('nonexistent')
    peer1.display_search_results(results)
    
    print("\n[INFO] Demo completed! Press Ctrl+C to exit")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        peer1.stop_server()
        peer2.stop_server()
        peer3.stop_server()

def main():
    """
    Demo: Chunked file transfer between peers
    """
    print("=" * 70)
    print("P2P CHUNKED FILE TRANSFER DEMO - STEP 6")
    print("=" * 70)
    print("\nSetup:")
    print("  Peer 1 (Port 5000): small_file.txt (1KB), medium_file.pdf (50KB), large_file.mp4 (200KB)")
    print("  Peer 2 (Port 5001): document.txt (2KB), image.jpg (75KB)")
    print("\nStarting network...\n")
    
    # Create demo files
    create_demo_files(1)
    create_demo_files(2)
    
    # Start peers
    peer1 = P2P('127.0.0.1', 5000, 'shared_1', 'downloads_1')
    peer1.start_server()
    time.sleep(1)
    
    peer2 = P2P('127.0.0.1', 5001, 'shared_2', 'downloads_2')
    peer2.start_server()
    peer2.connect_to_peer('127.0.0.1', 5000)
    time.sleep(2)
    
    # Peer 2 searches and downloads from Peer 1
    print("\n" + "="*70)
    print("DEMO: Peer 2 downloads 'medium_file.pdf' from Peer 1")
    
    success = peer2.download_file('127.0.0.1', 5000, 'medium_file.pdf')
    
    if success:
        print("\n✓ Download successful!")
    else:
        print("\n✗ Download failed!")
    
    time.sleep(1)
    
    # Peer 1 downloads from Peer 2
    print("\n" + "="*70)
    print("DEMO: Peer 1 downloads 'image.jpg' from Peer 2")
    print("="*70)
    
    success = peer1.download_file('127.0.0.1', 5001, 'image.jpg')
    
    if success:
        print("\n✓ Download successful!")
    else:
        print("\n✗ Download failed!")
    
    print("\n[INFO] Demo completed! Check downloads_1 and downloads_2 folders")
    print("[INFO] Press Ctrl+C to exit")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        peer1.stop_server()
        peer2.stop_server()

if __name__ == "__main__":
    main()