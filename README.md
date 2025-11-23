## Documentation:
root
│
├── src/
│   ├── p2p.py              # Packet structure with checksum
│   ├── interface.py        # RDT protocol (sender & receiver)
│
├── shared/
├── downloaded/
│
├── README.md
├── Report.pdf
├── revisions.txt
└── documentation.pdf


## Requirement:
Python 3.6 or higher. No external dependencies.


## How to run:
python3 src/p2p_interface.py 


## User Interface

### Options
  1. List connected peers - list all currently connected peers
  2. List my shared files - list all files available to share
  3. Search for files     - search for a file on the network
  4. Download file        - download a file once searched
  5. Refresh file index   - refresh hashes on files
  6. Connect to peer      - connect to a peer
  7. Exit
