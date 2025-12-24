
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
UNKNOWN_FILE = os.path.join(DATA_DIR, 'unknown_molecules.json')
VITAL_FILE = os.path.join(DATA_DIR, 'molecules', 'inorganic', 'vital.json')

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    print("🧹 Starting cleanup of unknown_molecules.json...")
    
    unknowns_data = load_json(UNKNOWN_FILE)
    if not unknowns_data:
        print("❌ unknown_molecules.json not found!")
        return

    # Check for known molecules to remove
    known_formulas = set()
    # H3N3 was added to vital.json
    known_formulas.add("H3N3")
    # S2 was seen in logs as Azufre Diatomico
    known_formulas.add("S2") 

    molecules = unknowns_data.get("unknown_molecules", [])
    new_molecules = []
    
    removed_count = 0
    updated_count = 0
    
    for mol in molecules:
        formula = mol['formula']
        entry = mol['suggested_entry']
        names = entry.get('names', {})
        
        # 1. Remove if known
        if formula in known_formulas:
            print(f"➖ Removing known molecule: {formula}")
            removed_count += 1
            continue
            
        # 2. Update placeholders to Residuo Inestable
        es_name = names.get('es', '')
        en_name = names.get('en', '')
        
        is_placeholder = False
        if "[Nombre Sugerido]" in es_name or "[Suggested Name]" in en_name:
            is_placeholder = True
        
        if is_placeholder:
            names['es'] = "Residuo Inestable"
            names['en'] = "Unstable Residue"
            entry['category'] = "waste" # Fix the 'ESTABLE' issue
            updated_count += 1
            
        new_molecules.append(mol)
        
    unknowns_data['unknown_molecules'] = new_molecules
    unknowns_data['summary']['total_incognitas'] = len(new_molecules)
    
    save_json(UNKNOWN_FILE, unknowns_data)
    
    print(f"✅ Cleanup complete.")
    print(f"   Removed: {removed_count}")
    print(f"   Updated names/category: {updated_count}")
    print(f"   Remaining: {len(new_molecules)}")

if __name__ == "__main__":
    main()
