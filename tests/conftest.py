"""
Pytest configuration — ensures project root is on sys.path
so imports like `from models.schemas import ...` work correctly.
"""
import sys
from pathlib import Path

# Insert project root at the front of sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
