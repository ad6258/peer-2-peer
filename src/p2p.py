import socket
import threading
import hashlib
import json
import time
from pathlib import Path



class P2P:

    def __init__(self, host='127.0.0.1', port=5000, shared_dir='shared', downloads_dir='downloads'):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.peers = {}
        self.peer_id = f"{host}:{port}"
        self.heartbeat_interval = 10

        self.shared_dir = Path(shared_dir)
        self.shared_dir.mkdir(exist_ok=True)
        self.file_index = {}

        self.search_results = {}
        self.search_timeout = 5
        self.search_lock = threading.Lock()

        self.chunk_size = 8192

        self.downloads_dir = Path(downloads_dir)
        self.downloads_dir.mkdir(exist_ok=True)



    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"[SERVER]    Started on {self.host}:{self.port}")
            print(f"[SERVER]    Waiting for connections")
            print(f"[SERVER]    Shared directory: {self.shared_dir.absolute()}")
            print(f"[SERVER] Downloads directory: {self.downloads_dir.absolute()}")


            self.scan_shared_folder()

            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()

            heartbeat_thread = threading.Thread(target=self.loop_heartbeat)
            heartbeat_thread.daemon = True
            heartbeat_thread.start()

            cleanup_thread = threading.Thread(target=self.cleanup_dead_peers)
            cleanup_thread.daemon = True
            cleanup_thread.start()
        except Exception as e:
            print(f"[ERROR]     Failed to start server: {e}")

    def download_file(self, peer_host, peer_port, filename):
        print(f"\n{'='*50}")
        print(f"[DOWNLOAD] Starting download: {filename} from {peer_host}:{peer_port}")        
        try:
            file_info = self.request_file_info_for_download(peer_host, peer_port, filename)
            
            if not file_info:
                print(f"[ERROR]     Could not get file info from peer")
                return False
            
            file_size = file_info['size']
            file_hash = file_info['hash']
            total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            
            print(f"[DOWNLOAD]  File size: {file_size} bytes")
            print(f"[DOWNLOAD]  Total chunks: {total_chunks}")
            print(f"[DOWNLOAD]  Expected hash: {file_hash[:32]}")

            download_path = self.downloads_dir / filename
            downloaded_chunks = 0
            
            with open(download_path, 'wb') as f:
                for chunk_index in range(total_chunks):
                    chunk_data = self.request_chunk(peer_host, peer_port, filename, chunk_index)
                    
                    if chunk_data is None:
                        print(f"\n[ERROR]     Failed to download chunk {chunk_index}")
                        return False
                    
                    f.write(chunk_data)
                    downloaded_chunks += 1
                    
                    progress = (downloaded_chunks / total_chunks) * 100
                    print(f"\r[DOWNLOAD]  Progress: {downloaded_chunks}/{total_chunks} chunks ({progress:.1f}%)", end='', flush=True)
            
            print(f"[DOWNLOAD]  Download complete, saved to: {download_path}")
            
            downloaded_hash = self.calculate_file_hash(download_path)
            
            if downloaded_hash == file_hash:
                print(f"[DOWNLOAD]  File integrity verified")
                return True
            else:
                print(f"[ERROR]     File integrity check FAILED!")
                print(f"[ERROR]     Expected: {file_hash[:32]}...")
                print(f"[ERROR]     Got:      {downloaded_hash[:32]}...")
                print(f"[ERROR]     Deleting corrupted file")
                download_path.unlink()
                return False
            
        except Exception as e:
            print(f"[ERROR]     Download failed: {e}")
            return False

    def request_file_info_for_download(self, peer_host, peer_port, filename):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10)
            client_socket.connect((peer_host, peer_port))

            request_msg = {
                'type': 'GET_FILE_INFO',
                'filename': filename,
                'requester': self.peer_id
            }

            client_socket.send(json.dumps(request_msg).encode('utf-8'))
            response_data = client_socket.recv(8192)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                if response.get('type') == 'FILE_INFO':
                    return response.get('info')
            
            client_socket.close()
            
        except Exception as e:
            print(f"[ERROR]      Failed to get file info: {e}")
            return None

    def request_chunk(self, peer_host, peer_port, filename, chunk_index):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10)
            client_socket.connect((peer_host, peer_port))
            
            request_msg = {
                'type': 'REQUEST_CHUNK',
                'filename': filename,
                'chunk_index': chunk_index,
                'chunk_size': self.chunk_size,
                'requester': self.peer_id
            }
            
            client_socket.send(json.dumps(request_msg).encode('utf-8'))
            
            header_data = client_socket.recv(1024)
            if not header_data:
                return None
            
            header = json.loads(header_data.decode('utf-8'))
            
            if header.get('type') == 'CHUNK_DATA':
                chunk_size = header.get('chunk_size')
                
                chunk_data = b''
                remaining = chunk_size
                
                while remaining > 0:
                    data = client_socket.recv(min(remaining, 8192))
                    if not data:
                        break
                    chunk_data += data
                    remaining -= len(data)
                
                client_socket.close()
                return chunk_data
            
            client_socket.close()
            return None
            
        except Exception as e:
            return None

    def send_chunk(self, client_socket, filename, chunk_index, chunk_size):
        try:
            file_info = self.get_file_info(filename)
            
            if not file_info:
                error_msg = {
                    'type': 'ERROR',
                    'message': f'File not found: {filename}'
                }
                client_socket.send(json.dumps(error_msg).encode('utf-8'))
                return
            
            filepath = file_info['path']
            
            offset = chunk_index * chunk_size
            
            with open(filepath, 'rb') as f:
                f.seek(offset)
                chunk_data = f.read(chunk_size)
            
            header = {
                'type': 'CHUNK_DATA',
                'filename': filename,
                'chunk_index': chunk_index,
                'chunk_size': len(chunk_data)
            }
            
            client_socket.send(json.dumps(header).encode('utf-8'))
            
            time.sleep(0.01)
            
            client_socket.sendall(chunk_data)
            
        except Exception as e:
            print(f"[ERROR]      Failed to send chunk: {e}")
    

    def search_local(self, query):
        query_lower = query.lower()
        results = []
        
        for filename, metadata in self.file_index.items():
            if query_lower in filename.lower():
                results.append({
                    'filename': filename,
                    'size': metadata['size'],
                    'hash': metadata['hash'],
                    'peer_id': self.peer_id,
                    'peer_host': self.host,
                    'peer_port': self.port
                })
        
        return results

    def search_network(self, query):
        """
        Search for files across all connected peers
        Broadcasts search request and aggregates results
        """
        print(f"[SEARCH]    Searching for: '{query}'")
        print(f"[SEARCH]    Querying {len(self.peers)} connected peers...")
        
        local_results = self.search_local(query)
        print(f"[SEARCH]    Found {len(local_results)} local matches")
        
        search_id = f"{self.peer_id}_{time.time()}"
        
        with self.search_lock:
            self.search_results[search_id] = {
                'query': query,
                'results': local_results.copy(),
                'responses_received': 0,
                'total_peers': len(self.peers)
            }
        
        if self.peers:
            search_threads = []
            for peer_id, peer_info in list(self.peers.items()):
                thread = threading.Thread(
                    target=self.send_search_request,
                    args=[peer_info['host'], peer_info['port'], query, search_id]
                )
                thread.daemon = True
                thread.start()
                search_threads.append(thread)
            
            start_time = time.time()
            while time.time() - start_time < self.search_timeout:
                with self.search_lock:
                    if search_id in self.search_results:
                        if self.search_results[search_id]['responses_received'] >= len(self.peers):
                            break
                time.sleep(0.1)
        
        with self.search_lock:
            if search_id in self.search_results:
                results = self.aggregate_search_results(search_id)
                del self.search_results[search_id]
            else:
                results = []
        
        print(f"[SEARCH]    Search complete. Found {len(results)} unique files")
        return results

    def send_search_request(self, peer_host, peer_port, query, search_id):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.search_timeout)
            client_socket.connect((peer_host, peer_port))
            
            search_msg = {
                'type': 'SEARCH_REQUEST',
                'query': query,
                'requester': self.peer_id,
                'search_id': search_id
            }
            
            client_socket.send(json.dumps(search_msg).encode('utf-8'))
            
            # Wait for response
            response_data = client_socket.recv(8192)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                if response.get('type') == 'SEARCH_RESPONSE':
                    results = response.get('results', [])
                    
                    with self.search_lock:
                        if search_id in self.search_results:
                            self.search_results[search_id]['results'].extend(results)
                            self.search_results[search_id]['responses_received'] += 1
                    
                    print(f"[SEARCH]    Received {len(results)} results from {peer_host}:{peer_port}")
            
            client_socket.close()
            
        except Exception as e:
            with self.search_lock:
                if search_id in self.search_results:
                    self.search_results[search_id]['responses_received'] += 1

    def aggregate_search_results(self, search_id):
        if search_id not in self.search_results:
            return []
        
        all_results = self.search_results[search_id]['results']
        
        aggregated = {}
        for result in all_results:
            filename = result['filename']
            if filename not in aggregated:
                aggregated[filename] = {
                    'filename': filename,
                    'size': result['size'],
                    'hash': result['hash'],
                    'peers': []
                }
            peer_info = {
                'peer_id': result['peer_id'],
                'host': result.get('peer_host'),
                'port': result.get('peer_port')
            }
            if peer_info not in aggregated[filename]['peers']:
                aggregated[filename]['peers'].append(peer_info)
        return list(aggregated.values())

    def display_search_results(self, results):
        """
        Pretty print search results
        """
        print(f"\n{'='*50}")
        print(f"SEARCH RESULTS ({len(results)} files found)")
        
        if not results:
            print("No files found matching your query.")
        else:
            for i, result in enumerate(results, 1):
                filename = result['filename']
                size_mb = result['size'] / (1024 * 1024)
                peers = result['peers']
                
                print(f"\n{i}. {filename}")
                print(f"   Size: {size_mb:.2f} MB ({result['size']} bytes)")
                print(f"   Hash: {result['hash'][:32]}...")
                print(f"   Available on {len(peers)} peer(s):")
                
                for peer in peers:
                    peer_id = peer['peer_id']
                    host = peer.get('host', 'unknown')
                    port = peer.get('port', 'unknown')
                    print(f"      - {peer_id} ({host}:{port})")
        
        print(f"{'='*50}\n")


    def calculate_file_hash(self, filepath):
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[ERROR]     Failed to hash {filepath}: {e}")
            return None

    def scan_shared_folder(self):
        print(f"\n[INDEX]     Scanning shared folder: {self.shared_dir}")
        self.file_index = {}
        
        if not self.shared_dir.exists():
            print(f"[WARNING]   Shared directory does not exist, creating it.")
            self.shared_dir.mkdir(exist_ok=True)
            return
        
        file_count = 0
        for file_path in self.shared_dir.rglob('*'):
            if file_path.is_file():
                filename = file_path.name
                file_size = file_path.stat().st_size
                
                print(f"[INDEX]     Hashing: {filename}", end=' ')
                file_hash = self.calculate_file_hash(file_path)
                
                if file_hash:
                    self.file_index[filename] = {
                        'path': str(file_path),
                        'size': file_size,
                        'hash': file_hash
                    }
                    size_mb = file_size / (1024 * 1024)
                    print(f"✓ ({size_mb:.2f} MB)")
                    file_count += 1
                else:
                    print("[ERROR]     Indexing Failed")
        print(f"[INDEX]     Indexed {file_count} files\n")

    def refresh_index(self):
        print("[INDEX]     Refreshing file index.")
        self.scan_shared_folder()

    def get_file_list(self):
        return list(self.file_index.keys())

    def get_file_info(self, filename):
        return self.file_index.get(filename)

    def list_files(self):
        print(f"\n{'='*50}")
        print(f"SHARED FILES ({len(self.file_index)}):")

        
        if not self.file_index:
            print("No files in shared folder.")
            print(f"Add files to: {self.shared_dir.absolute()}")
        else:
            for i, (filename, metadata) in enumerate(self.file_index.items(), 1):
                size_mb = metadata['size'] / (1024 * 1024)
                file_hash = metadata['hash']
                
                print(f"\n{i}. {filename}")
                print(f"   Size: {size_mb:.2f} MB ({metadata['size']} bytes)")
                print(f"   Hash: {file_hash[:32]}...")
                print(f"   Path: {metadata['path']}")
        print(f"{'='*50}\n")

    def request_peer_file_list(self, peer_host, peer_port):
        try:
            print(f"[CLIENT]    Requesting file list from {peer_host}:{peer_port}...")

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((peer_host, peer_port))
            request_msg = {
                'type': 'GET_FILE_LIST',
                'requester': self.peer_id
            }
            client_socket.send(json.dumps(request_msg).encode('utf-8'))

            response_data = client_socket.recv(8192)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                if response.get('type') == 'FILE_LIST':
                    files = response.get('files', [])
                    peer_id = response.get('peer_id')
                    
                    print(f"\n[FILE LIST] Files on {peer_id}:")
                    print(f"{'='*50}")
                    if not files:
                        print("[ERROR]     No files available")
                    else:
                        for i, filename in enumerate(files, 1):
                            print(f"  {i}. {filename}")
                    
                    return files
            
            client_socket.close()
            
        except Exception as e:
            print(f"[ERROR]     Failed to get file list from {peer_host}:{peer_port}: {e}")
            return []

    def request_file_info(self, peer_host, peer_port, filename):
        try:
            print(f"[CLIENT]    Requesting info for '{filename}' from {peer_host}:{peer_port}")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((peer_host, peer_port))
            request_msg = {
                'type': 'GET_FILE_INFO',
                'filename': filename,
                'requester': self.peer_id
            }
            client_socket.send(json.dumps(request_msg).encode('utf-8'))
            response_data = client_socket.recv(8192)
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                if response.get('type') == 'FILE_INFO':
                    file_info = response.get('info')
                    if file_info:
                        print(f"\n[FILE INFO] {filename}")
                        size_mb = file_info['size'] / (1024 * 1024)
                        print(f"  Size: {size_mb:.2f} MB ({file_info['size']} bytes)")
                        print(f"  Hash: {file_info['hash']}")
                        print(f"{'='*70}\n")
                        return file_info
                    else:
                        print(f"[INFO]      File '{filename}' not found on peer")
            client_socket.close()
        except Exception as e:
            print(f"[ERROR]     Failed to get file info: {e}")
            return None

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
                data = client_socket.recv(8192)
                
                if not data:
                    break
                    
                message = json.loads(data.decode('utf-8'))
                
                if message.get('type') == 'REQUEST_CHUNK':
                    filename = message.get('filename')
                    chunk_index = message.get('chunk_index')
                    chunk_size = message.get('chunk_size')
                    requester = message.get('requester')
                    
                    print(f"[SERVER]    Chunk request from {requester}: {filename} chunk {chunk_index}")
                    self.send_chunk(client_socket, filename, chunk_index, chunk_size)
                    break
                else:
                    response = self.process_message(message, address)
                    if response:
                        client_socket.send(json.dumps(response).encode('utf-8'))
                    
        except Exception as e:
            print(f"[ERROR]     Error handling client {address}: {e}")
        finally:
            client_socket.close()

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

        elif msg_type == 'SEARCH_REQUEST':
            query = message.get('query')
            requester = message.get('requester')
            
            print(f"[SERVER]    Search request from {requester}: '{query}'")
            
            results = self.search_local(query)
            
            return {
                'type': 'SEARCH_RESPONSE',
                'query': query,
                'results': results,
                'peer_id': self.peer_id
            }

        elif msg_type == 'GET_FILE_LIST':
            requester = message.get('requester')
            print(f"[SERVER] File list request from {requester}")
            
            return {
                'type': 'FILE_LIST',
                'files': self.get_file_list(),
                'peer_id': self.peer_id
            }
            
        elif msg_type == 'GET_FILE_INFO':
            filename = message.get('filename')
            requester = message.get('requester')
            print(f"[SERVER]    File info request from {requester}: {filename}")
            
            file_info = self.get_file_info(filename)
            
            return {
                'type': 'FILE_INFO',
                'filename': filename,
                'info': file_info,
                'peer_id': self.peer_id
            }

        # elif msg_type == 'REQUEST_CHUNK':
        #     filename = message.get('filename')
        #     chunk_index = message.get('chunk_index')
        #     chunk_size = message.get('chunk_size')
        #     requester = message.get('requester')
            
        #     print(f"[SERVER] Chunk request from {requester}: {filename} chunk {chunk_index}")
            
        #     # Send chunk directly (not as JSON response)
        #     if client_socket:
        #         self.send_chunk(client_socket, filename, chunk_index, chunk_size)
            
        #     return None

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
            print(f"[ERROR]     Failed to connect to {peer_host}:{peer_port}: {e}")
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




