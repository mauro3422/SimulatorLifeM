import sys
import os

# Add project root to path
sys.path.append(r"c:\Users\mauro\OneDrive\Escritorio\LifeSimulator")

from src.config.molecules import load_molecule_database, get_all_known_molecules, get_molecule_entry

def verify():
    print("Loading molecule database...")
    load_molecule_database("es")
    
    db = get_all_known_molecules()
    print(f"Total molecules loaded: {len(db)}")
    
    # Check for a sample emergent molecule
    # I'll check a few from the list I generated (I don't know the exact formulas without reading, 
    # but I know 'C1H3N2O2P1' was the first one in the unknown list).
    
    sample_formula = "C1H3N2O2P1"
    entry = get_molecule_entry(sample_formula)
    
    if entry:
        print(f"SUCCESS: Found emergent molecule {sample_formula}")
        print(f"Name: {entry['identity']['names']['es']}")
        print(f"Lore: {entry.get('lore')}")
        print(f"Category: {entry['identity']['category']}")
    else:
        print(f"FAILURE: Could not find emergent molecule {sample_formula}")

    # Check for 'C2H7O1P1' (second one)
    sample_formula_2 = "C2H7O1P1"
    if is_known := (sample_formula_2 in db):
        print(f"SUCCESS: Found {sample_formula_2}")
    else:
        print(f"FAILURE: Could not find {sample_formula_2}")

if __name__ == "__main__":
    verify()
