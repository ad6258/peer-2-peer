from p2p import P2P
import time

class UserInterface():
    def __init__(self, node):
        self.node = node
        self.last_search_results = []

    def show_menu(self):
        print("Options:")
        print("  1. List connected peers")
        print("  2. List my shared files")
        print("  3. Search for files")
        print("  4. Download file")
        print("  5. Refresh file index")
        print("  6. Connect to peer")
        print("  7. Exit")

    def run(self):
        while self.node.running:
            try:
                self.show_menu()
                choice = input("Enter choice (1-7): ").strip()

                if choice == '1':
                    self.node.list_peers()
                    
                elif choice == '2':
                    self.node.list_files()
                    
                elif choice == '3':
                    self.search_files()
                    
                elif choice == '4':
                    self.download_file()
                    
                elif choice == '5':
                    print("\nRefreshing file index")
                    self.node.scan_shared_folder()
                    
                elif choice == '6':
                    self.connect_to_peer()
                    
                elif choice == '7':
                    print("\nShutting down")
                    self.node.stop_server()
                    break
                    
                else:
                    print("\nInvalid choice. Please enter 1-7.")
                    
            except KeyboardInterrupt:
                print("Shutting down")
                self.node.stop_server()
                break

    def search_files(self):
        query = input("\nEnter search query: ").strip()
        
        if not query:
            print("Please enter a search term")
            return
        
        print(f"\nSearching for '{query}'")
        results = self.node.search_network(query)
        self.last_search_results = results
        
        
        if not results:
            print("No files found matching your query.")
        else:
            print(f"{len(results)} files found")
            for i, result in enumerate(results, 1):
                filename = result['filename']
                size_mb = result['size'] / (1024 * 1024)
                peers = result['peers']
                
                print(f"\n{i}. {filename}")
                print(f"   Size: {size_mb:.2f} MB")
                print(f"   Available on {len(peers)} peer(s):")
                
                for peer in peers:
                    print(f"      - {peer['peer_id']}")

    def download_file(self):
        if not self.last_search_results:
            print("\nNot in search results. Please search for files first (option 3).")
            return
        
        print(f"\nYou have {len(self.last_search_results)} files from last search.")
        file_num = input("Enter file number to download: ").strip()
        
        try:
            file_num = int(file_num)
            if file_num < 1 or file_num > len(self.last_search_results):
                print("Invalid file number")
                return
            
            result = self.last_search_results[file_num - 1]
            filename = result['filename']
            peers = result['peers']
            
            if not peers:
                print("No peers available for this file")
                return
            
            print(f"\nFile is available on {len(peers)} peer(s):")
            for i, peer in enumerate(peers, 1):
                print(f"{i}. {peer['peer_id']}")
            
            peer_num = input("Select peer (1-{}): ".format(len(peers))).strip()
            
            try:
                peer_num = int(peer_num)
                if peer_num < 1 or peer_num > len(peers):
                    print("Invalid peer number")
                    return
                
                peer = peers[peer_num - 1]
                success = self.node.download_file(peer['host'], peer['port'], filename)
                
                if success:
                    print(f"\nSuccessfully downloaded: {filename}")
                else:
                    print(f"\nFailed to download: {filename}")
                    
            except ValueError:
                print("Please enter a valid number")
                
        except ValueError:
            print("Please enter a valid number")

    def connect_to_peer(self):
        print("\nConnect to peer:")
        host = input("Enter peer IP address (default: 127.0.0.1): ").strip() or "127.0.0.1"
        port_str = input("Enter peer port: ").strip()
        
        try:
            port = int(port_str)
            print(f"\nConnecting to {host}:{port}")
            success = self.node.connect_to_peer(host, port)
            
            if success:
                print(f"Successfully connected to {host}:{port}")
            else:
                print(f"Failed to connect to {host}:{port}")
                
        except ValueError:
            print("Invalid port number")


    def download_file(self):
        """Download a file from search results"""
        if not self.last_search_results:
            print("\n✗ No search results. Please search for files first (option 3).")
            return
        
        print(f"\nYou have {len(self.last_search_results)} files from last search.")
        file_num = input("Enter file number to download: ").strip()
        
        try:
            file_num = int(file_num)
            if file_num < 1 or file_num > len(self.last_search_results):
                print("✗ Invalid file number")
                return
            
            result = self.last_search_results[file_num - 1]
            filename = result['filename']
            peers = result['peers']
            
            if not peers:
                print("✗ No peers available for this file")
                return
            
            print(f"\nFile is available on {len(peers)} peer(s):")
            for i, peer in enumerate(peers, 1):
                print(f"{i}. {peer['peer_id']}")
            
            peer_num = input("Select peer (1-{}): ".format(len(peers))).strip()
            
            try:
                peer_num = int(peer_num)
                if peer_num < 1 or peer_num > len(peers):
                    print("✗ Invalid peer number")
                    return
                
                peer = peers[peer_num - 1]
                success = self.node.download_file(peer['host'], peer['port'], filename)
                
                if success:
                    print(f"\nSuccessfully downloaded: {filename}")
                else:
                    print(f"\nFailed to download: {filename}")
                    
            except ValueError:
                print("✗ Please enter a valid number")
                
        except ValueError:
            print("✗ Please enter a valid number")
     


def main():
    print("P2P FILE SHARING SYSTEM")
    print("="*50)
    port_str = input("Enter port number (default: 5000): ").strip() or "5000"
    
    try:
        port = int(port_str)
    except ValueError:
        print("Invalid port, using 5000")
        port = 5000
    
    # Create and start node
    node = P2P('127.0.0.1', port)
    node.start_server()
    time.sleep(1)

    ui = UserInterface(node)
    ui.run()


if __name__ == "__main__":
    main()