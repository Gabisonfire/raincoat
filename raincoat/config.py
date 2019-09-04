import json
import os

def load_config(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    else:
        print(f"Config file not found. ({path})")