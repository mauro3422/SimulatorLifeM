
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PLAYER_FILE = os.path.join(DATA_DIR, 'player_molecules.json')
UNKNOWN_FILE = os.path.join(DATA_DIR, 'unknown_molecules.json')

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False) # indent 4 for player file usually

def main():
    print("🔧 Force Fixing Names in player_molecules.json...")
    
    player_data = load_json(PLAYER_FILE)
    unknowns_data = load_json(UNKNOWN_FILE)
    
    # helper to find unknown definition
    unknown_map = {}
    for msg in unknowns_data.get('unknown_molecules', []):
        unknown_map[msg['formula']] = msg['suggested_entry']['names']['es']

    fixed_count = 0
    
    junk_names = ["[Nombre Sugerido]", "[Suggested Name]", "Desconocida"]
    
    for formula, data in player_data.items():
        name = data.get('name', '')
        
        # If it's a known placeholder
        if name in ["[Nombre Sugerido]", "[Suggested Name]"]:
            print(f"  -> Fixing {formula}: {name} -> Residuo Inestable")
            data['name'] = "Residuo Inestable"
            fixed_count += 1
            
        # If it's Desconocida, check if we decided it's Residuo earlier
        elif name == "Desconocida":
            if formula in unknown_map:
                mapped_name = unknown_map[formula]
                # If the unknown map says it's Residuo or Fixed Name
                if mapped_name in ["Residuo Inestable", "Transitorio"] or "Sugerido" not in mapped_name:
                     print(f"  -> resolving {formula}: Desconocida -> {mapped_name}")
                     data['name'] = mapped_name
                     fixed_count += 1

    if fixed_count > 0:
        save_json(PLAYER_FILE, player_data)
        print(f"✅ Saved {fixed_count} fixes to player_molecules.json")
    else:
        print("✅ No fixes needed in player_molecules.json")

    # Re-run unknown cleanup just to be sure
    print("\n🧹 Re-cleaning unknown_molecules.json...")
    u_count = 0
    new_unknowns = []
    
    # We DO NOT want to delete H3N3/S2 here again if they are already gone, 
    # but we want to rename any [Nombre Sugerido] that crept back in.
    
    if unknowns_data:
        mols = unknowns_data.get('unknown_molecules', [])
        for m in mols:
            names = m['suggested_entry']['names']
            if "[Nombre Sugerido]" in names.get('es', '') or "[Suggested Name]" in names.get('en', ''):
                names['es'] = "Residuo Inestable"
                names['en'] = "Unstable Residue"
                m['suggested_entry']['category'] = "waste"
                u_count += 1
            new_unknowns.append(m)
            
        unknowns_data['unknown_molecules'] = new_unknowns
        # Save with indent 2 for unknowns
        with open(UNKNOWN_FILE, 'w', encoding='utf-8') as f:
            json.dump(unknowns_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Re-cleaned {u_count} entries in unknown_molecules.json")

if __name__ == "__main__":
    main()
