import json
import os

def process_remaining():
    enriched_path = 'data/molecules/enriched_discoveries.json'
    blocklist_path = 'data/molecules/blocklist.json'
    
    with open(enriched_path, 'r', encoding='utf-8') as f:
        enriched = json.load(f)
    
    with open(blocklist_path, 'r', encoding='utf-8') as f:
        blocklist = json.load(f)
    
    blocked_formulas = set(blocklist['blocked_formulas'])
    molecules = enriched['molecules']
    
    remaining_formulas = list(molecules.keys())
    print(f"Analyzing {len(remaining_formulas)} molecules...")

    to_move_to_precursors = {}
    to_move_to_exotic = {}
    to_block = []
    to_keep_as_is = {}

    # Definitions for moving
    for formula in remaining_formulas:
        mol = molecules[formula]
        name = mol['identity']['names']['es']
        
        # 1. Acroleína (C3H4O1) -> Move to precursors (normalizing formula if needed)
        if name == "Acroleína" or formula == "C3H4O1":
            to_move_to_precursors[formula] = mol
            continue
            
        # 2. Phospho/Sila/Tio - Many were already redirected, but let's check for "Fosforamida" etc.
        if "Fosforamida" in name:
            to_move_to_exotic[formula] = mol
            continue

        # 3. Simple radicals or generic combos that are suspicious
        # If formula has Si and P together and small amount of H
        if "Si" in formula and "P" in formula:
            to_move_to_exotic[formula] = mol
            continue

        # 4. Radicals that are real but weren't caught
        if "Radical" in name:
            to_move_to_exotic[formula] = mol
            continue

        # 5. Generic names like "Azotic Compound" were blocked usually, 
        # but if any survived with weird formulas, block them.
        if "Azotic Compound" in name or "Complex" in name:
            to_block.append(formula)
            continue
            
        # Default: suspicious/emergent to exotic for now with a warning
        to_move_to_exotic[formula] = mol

    print(f"To precursors: {len(to_move_to_precursors)}")
    print(f"To exotic: {len(to_move_to_exotic)}")
    print(f"To block: {len(to_block)}")

    # Update files (simplified for this script)
    # In a real scenario, I'd update each file properly.
    # For now, I'll just output the lists so I can handle them in the next step.
    
    return to_move_to_precursors, to_move_to_exotic, to_block

if __name__ == "__main__":
    p, e, b = process_remaining()
    print("\n--- BLOCK LIST ---")
    print(b)
    print("\n--- PRECURSORS ---")
    print(list(p.keys()))
    print("\n--- EXOTIC ---")
    print(list(e.keys()))
