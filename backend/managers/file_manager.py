import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / 'data'

def get_filepath(filename):
    """Returns the absolute path for a file in the data directory."""
    return DATA_DIR / filename

def read_json(filename, default=None):
    """Reads and returns JSON data from a file, returning default if file not found."""
    filepath = get_filepath(filename)
    if not filepath.exists():
        return default if default is not None else {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default if default is not None else {}
    except Exception:
        return default if default is not None else {}

def write_json(filename, data):
    """Writes data to a JSON file."""
    filepath = get_filepath(filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)