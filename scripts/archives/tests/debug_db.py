import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config.molecules import load_molecule_database, _molecule_db, is_known_molecule

# Load DB
load_molecule_database("es")

# Print first 20 keys to see format
print("DB Keys Sample:")
keys = list(_molecule_db.keys())
print(keys[:20])

# Test some common formulas
tests = ["H2O", "H2O1", "CH4", "C1H4", "O2", "O2P1"]
print("\nTesting lookups:")
for t in tests:
    print(f"'{t}': {is_known_molecule(t)}")
