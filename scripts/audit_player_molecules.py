
import sys
import os
import json
import re

# Add project root to path so we can import src
sys.path.append(os.getcwd())

try:
    from src.config.molecules import load_molecule_database, get_molecule_entry, get_molecule_name, _molecule_db
except ImportError:
    # Fallback if run from scripts/ dir
    sys.path.append(os.path.dirname(os.getcwd()))
    from src.config.molecules import load_molecule_database, get_molecule_entry, get_molecule_name, _molecule_db

def audit_player_molecules():
    print("Loading molecule database...")
    if not load_molecule_database():
        print("Failed to load database.")
        return

    player_file = 'data/player_molecules.json'
    if not os.path.exists(player_file):
        print(f"File not found: {player_file}")
        return

    print(f"Scanning {player_file}...")
    with open(player_file, 'r', encoding='utf-8') as f:
        player_molecules = json.load(f)

    total = 0
    direct_match = 0
    recovered_by_fix = 0
    truly_unknown = 0
    
    recovered_list = []
    unknown_only = []

    for formula in player_molecules:
        if formula == "AGGREGATE_AMORPHOUS":
            continue
            
        total += 1
        
        # 1. Check if it exists exactly in the DB (Direct Match)
        is_direct = formula in _molecule_db
        
        # 2. Check if the new logic finds it (Resolved)
        entry = get_molecule_entry(formula)
        
        if is_direct:
            direct_match += 1
        elif entry:
            # Not in DB directly, but found by get_molecule_entry -> implies Normalization fixed it!
            recovered_by_fix += 1
            name = get_molecule_name(formula)
            recovered_list.append(f"{formula} -> {name}")
        else:
            truly_unknown += 1
            unknown_only.append(formula)

    print("-" * 40)
    print(f"AUDIT RESULTS")
    print("-" * 40)
    print(f"Total Molecules in Inventory: {total}")
    print(f"✅ Direct Database Matches:    {direct_match}")
    print(f"🔧 Recovered by Fix (Mismatch): {recovered_by_fix}")
    print(f"❓ Truly Unknown (New/Missing): {len(unknown_only)}")
    print("----------------------------------------")
    
    if unknown_only:
        print("\nTop 20 Unknowns (by formula length):")
        # Sort by length for interest, or just list them
        sorted_unknowns = sorted(list(unknown_only), key=len)[:20]
        for f in sorted_unknowns:
            print(f"  • {f}")
            
    print("\nFull list of Unknowns:")
    for f in sorted(list(unknown_only)):
        print(f"  • {f}")
    print("-" * 40)
    
    if recovered_by_fix > 0:
        print("\nExamples of molecules saved by the fix:")
        for item in recovered_list[:15]:
            print(f"  • {item}")
        if len(recovered_list) > 15:
            print(f"  ... and {len(recovered_list) - 15} more.")

if __name__ == "__main__":
    audit_player_molecules()
