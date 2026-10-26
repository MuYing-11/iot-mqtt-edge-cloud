"""Load the cloud broker (EC2) address and credentials from a KEY=VALUE file."""
import os

_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.env"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cloud", "secrets.env"),
]


def load():
    for path in _CANDIDATES:
        if os.path.exists(path):
            with open(path) as f:
                return dict(line.strip().split("=", 1) for line in f if "=" in line)
    raise FileNotFoundError("secrets.env not found")
