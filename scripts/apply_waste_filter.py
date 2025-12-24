import sys
import os

# Add src to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.molecules import export_unknown_molecules

def run():
    print("Applying Procedural Waste Filter to unknown_molecules.json...")
    
    # Passing an empty set of new discoveries serves to just re-process existing data
    # The export function loads existing data, filters it using the new logic, and writes it back.
    output_path = export_unknown_molecules(set())
    
    print(f"Cleanup complete. File updated at: {output_path}")

if __name__ == "__main__":
    run()
