import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from watcher.main import run_watcher

if __name__ == "__main__":
    run_watcher()