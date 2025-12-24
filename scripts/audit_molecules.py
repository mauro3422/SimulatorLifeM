import json
import os
import glob
from collections import defaultdict

# Paths
DATA_DIR = r"c:\Users\mauro\OneDrive\Escritorio\LifeSimulator\data"
MOLECULES_DIR = os.path.join(DATA_DIR, "molecules")
UNKNOWN_FILE = os.path.join(DATA_DIR, "unknown_molecules.json")

# Common chemical formulas to identify
COMMON_FORMULAS = {
    "C2H2": {"name": "Acetileno", "category": "organic/hydrocarbons"},
    "C2H4": {"name": "Etileno", "category": "organic/hydrocarbons"},
    "C2H6": {"name": "Etano", "category": "organic/hydrocarbons"},
    "C3H8": {"name": "Propano", "category": "organic/hydrocarbons"},
    "C4H10": {"name": "Butano", "category": "organic/hydrocarbons"},
    "C6H6": {"name": "Benceno", "category": "organic/hydrocarbons"},
    "CH4": {"name": "Metano", "category": "organic/hydrocarbons"},
    "CH3OH": {"name": "Metanol", "category": "organic/alcohols"}, # C1H4O1
    "C2H5OH": {"name": "Etanol", "category": "organic/alcohols"}, # C2H6O1
    "CH3COOH": {"name": "Ácido Acético", "category": "organic/acids"}, # C2H4O2
    "H2CO3": {"name": "Ácido Carbónico", "category": "inorganic/acids"}, # H2C1O3
    "NH3": {"name": "Amoníaco", "category": "inorganic/basics"}, # H3N1
    "O3": {"name": "Ozono", "category": "inorganic/basics"}, # O3
    "H2O2": {"name": "Peróxido de Hidrógeno", "category": "inorganic/basics"}, # H2O2
}

# Normalized common mapping (C H O order independent)
def normalize_formula(formula_str):
    # This is a simple parser, assuming standard game format e.g. "C2H4", "H2O1"
    # Actually checking the game format: it seems to be Element+Count.
    # We might need a proper parser if the order varies. 
    # For now, let's just rely on the string from the file if it's consistent.
    # Or better, parse to a dict to compare.
    import re
    matches = re.findall(r"([A-Z][a-z]?)(\d*)", formula_str)
    counts = {}
    for el, count in matches:
        counts[el] = int(count) if count else 1
    return counts

# Pre-compute common normalized
existing_definitions = {}
normalized_common = {}

# Map manual common list to normalized dicts
for manual_f, info in COMMON_FORMULAS.items():
    # We need to manually normalize these standard human formulas to match the game's likely output
    # E.g. CH3COOH -> C2H4O2
    # I'll create a helper for the manual list too
    counts = normalize_formula(manual_f)
    # Convert to sorted string for key
    key = "".join(sorted([f"{k}{v}" for k,v in counts.items()]))
    normalized_common[key] = info

def load_known_molecules():
    known = set()
    for root, dirs, files in os.walk(MOLECULES_DIR):
        for file in files:
            if file.endswith(".json"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Depending on structure, might be list or dict
                        # Usually "molecules": [...]
                        mols = data.get("molecules", []) if isinstance(data, dict) else data
                        for m in mols:
                            if "formula" in m:
                                known.add(m["formula"])
                                # Also normalize to catch order diffs
                                counts = normalize_formula(m["formula"])
                                key = "".join(sorted([f"{k}{v}" for k,v in counts.items()]))
                                existing_definitions[key] = m.get("name", "Unknown")
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    return known

def analyze_unknowns():
    load_known_molecules()
    
    try:
        with open(UNKNOWN_FILE, 'r', encoding='utf-8') as f:
            unknown_data = json.load(f)
    except Exception as e:
        print(f"Error reading unknown file: {e}")
        return

    unknown_list = unknown_data.get("unknown_molecules", [])
    print(f"Total Unknown Entries: {len(unknown_list)}")

    identified_candidates = []
    really_unknown = []

    for entry in unknown_list:
        raw_formula = entry["formula"]
        atoms_count = entry["atoms"]
        
        counts = normalize_formula(raw_formula)
        # Create a sorted key
        key = "".join(sorted([f"{k}{v}" for k,v in counts.items()]))
        
        # Check against existing (game might have order weirdness, so we verify)
        if key in existing_definitions:
            print(f"[WARN] {raw_formula} exists as {existing_definitions[key]} but is in unknown list!")
            continue

        # Check against common list
        if key in normalized_common:
            match = normalized_common[key]
            identified_candidates.append({
                "game_formula": raw_formula,
                "real_formula": key, # simplified
                "name": match["name"],
                "category": match["category"],
                "atoms": atoms_count
            })
        else:
            really_unknown.append(entry)

    print("\n--- IDENTIFIED CANDIDATES (Ready to Add) ---")
    for c in identified_candidates:
        print(f"Formula: {c['game_formula']} -> {c['name']} ({c['category']})")

    print("\n--- TOP FREQUENT / INTERESTING UNKNOWNS ---")
    # Here we could group by formula if there are dupes, but the file implies unique entries?
    # Actually checking the file content earlier, it seemed list-based.
    # Let's just list the top 10 weird ones.
    for u in really_unknown[:20]:
        print(f"Unknown: {u['formula']} (Atoms: {u['atoms']})")

if __name__ == "__main__":
    analyze_unknowns()
