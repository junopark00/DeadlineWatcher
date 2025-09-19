import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from watcher.api import start_api_server

if __name__ == "__main__":
    start_api_server()