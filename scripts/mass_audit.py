import json
import os
import re

# Paths
UNKNOWN_MOLECULES_PATH = r"c:\Users\mauro\OneDrive\Escritorio\LifeSimulator\data\unknown_molecules.json"
OUTPUT_PATH = r"c:\Users\mauro\OneDrive\Escritorio\LifeSimulator\data\molecules\emergent.json"
BLOCKLIST_PATH = r"c:\Users\mauro\OneDrive\Escritorio\LifeSimulator\data\molecules\blocklist.json"

def load_blocklist():
    """Load formulas that should be auto-skipped (trash)."""
    if os.path.exists(BLOCKLIST_PATH):
        with open(BLOCKLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("blocked_formulas", []))
    return set()

# Chemical Nomenclature Data
PREFIXES = {
    1: "Meth", 2: "Eth", 3: "Prop", 4: "But", 5: "Pent",
    6: "Hex", 7: "Hept", 8: "Oct", 9: "Non", 10: "Dec"
}

ELEMENT_NAMES = {
    "C": "Carbon", "H": "Hydrogen", "O": "Oxygen", "N": "Nitrogen",
    "P": "Phosphorus", "S": "Sulfur", "Si": "Silicon"
}

def parse_formula(formula):
    """Parses a chemical formula like 'C2H6O1' into a dictionary {'C': 2, 'H': 6, 'O': 1}."""
    matches = re.findall(r"([A-Z][a-z]*)(\d*)", formula)
    atoms = {}
    for element, count in matches:
        atoms[element] = int(count) if count else 1
    return atoms

def generate_name(formula, atoms):
    """Generates a plausible scientific name based on composition."""
    c_count = atoms.get("C", 0)
    si_count = atoms.get("Si", 0)
    n_count = atoms.get("N", 0)
    o_count = atoms.get("O", 0)
    p_count = atoms.get("P", 0)
    s_count = atoms.get("S", 0)
    
    name_parts = []
    
    # Base structure (Carbon or Silicon)
    if c_count > 0:
        base = PREFIXES.get(c_count, f"C{c_count}")
        suffix = "ane" # Default to single bonds assumption for procedural generation
        if n_count > 0: suffix = "amine"
        elif o_count > 0: suffix = "ol" if "H" in atoms else "one"
        name_parts.append(f"{base}yl-{suffix}" if len(name_parts) > 0 else f"{base}{suffix}")
    elif si_count > 0:
        base = "Sil" if si_count == 1 else "Disil" if si_count == 2 else "Polysil"
        name_parts.append(f"{base}ane")
    else:
        name_parts.append("Inorganic Aggregate")

    # Modifiers
    if p_count > 0: name_parts.insert(0, "Phospho")
    if s_count > 0: name_parts.insert(0, "Thio")
    if si_count > 0 and c_count > 0: name_parts.insert(0, "Sila")
    
    # Cleaning up name
    full_name = "".join(name_parts)
    
    # Special cases for realistic look
    if c_count == 0 and n_count > 0: full_name = "Azotic Compound"
    if full_name.endswith("ane") and n_count > 0: full_name = full_name.replace("ane", "amino")
    
    # Generic fallback if too complex
    if len(full_name) > 20 or full_name == "Inorganic Aggregate":
        elements = "".join([f"{k}{v}" for k, v in atoms.items()])
        full_name = f"Complex {elements}"

    return full_name

def generate_lore(atoms):
    """Generates lore strings."""
    c_count = atoms.get("C", 0)
    p_count = atoms.get("P", 0)
    si_count = atoms.get("Si", 0)
    
    origin = "Synthesized in the chaotic primeval soup."
    bio = "Currently unknown role in biological systems."
    utility = "Potential catalyst for further reactions."
    
    if p_count > 0:
        origin = "Formed in high-energy phosphate-rich environments."
        bio = "May serve as a precursor to genetic polymers."
        utility = "Energy storage candidate."
    elif si_count > 0:
        origin = "A rare organosilicon structure."
        bio = "Incompatible with standard carbon biology."
        utility = "Heat-resistant material component."
    elif c_count > 5:
        origin = "Complex organic aggregate formed by polymerization."
        bio = "Could form cell membrane structures."
        utility = "Structural lipid precursor."

    return {
        "origin_story": origin,
        "biological_presence": bio,
        "utility": utility
    }

def calculate_dou(atoms):
    """Calculate Degree of Unsaturation (DoU) for radical detection.
    DoU = (2C + 2 + N - H - X) / 2
    Fractional DoU = radical (unpaired electron)
    """
    C = atoms.get("C", 0)
    H = atoms.get("H", 0)
    N = atoms.get("N", 0)
    # Halogens (not common in simulation, but include for completeness)
    X = 0
    
    dou = (2 * C + 2 + N - H - X) / 2
    return dou

def is_radical(atoms):
    """Check if molecule is a radical (fractional DoU or too few atoms)."""
    dou = calculate_dou(atoms)
    total_atoms = sum(atoms.values())
    
    # Radical conditions:
    # 1. Fractional DoU (unpaired electron)
    # 2. Very small fragments (< 3 atoms)
    # 3. No hydrogen and only heavy atoms (very unstable)
    is_fractional = dou != int(dou)
    is_tiny = total_atoms < 3
    no_hydrogen = atoms.get("H", 0) == 0 and total_atoms < 5
    
    return is_fractional or is_tiny or no_hydrogen

RADICALS_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "molecules", "radicals_log.json")

def process_molecules():
    if not os.path.exists(UNKNOWN_MOLECULES_PATH):
        print("Unknown molecules file not found.")
        return

    with open(UNKNOWN_MOLECULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    unknowns = data.get("unknown_molecules", [])
    new_molecules = {}
    radicals_detected = []
    
    # Load blocklist to skip trash
    blocklist = load_blocklist()
    if blocklist:
        print(f"  [FILTER] Loaded {len(blocklist)} blocked formulas")
    
    skipped = 0
    radicals_skipped = 0
    print(f"Processing {len(unknowns)} unknown molecules...")
    
    for entry in unknowns:
        formula = entry["formula"]
        
        # Skip if in blocklist
        if formula in blocklist:
            skipped += 1
            continue
            
        atoms = parse_formula(formula)
        
        # Skip radicals (fractional DoU = unstable)
        if is_radical(atoms):
            radicals_skipped += 1
            radicals_detected.append({
                "formula": formula,
                "atoms": sum(atoms.values()),
                "dou": calculate_dou(atoms),
                "reason": "Radical/Unstable fragment"
            })
            continue
        
        # Generate data
        name_en = generate_name(formula, atoms)
        # Simple Spanish Translation heuristic
        name_es = name_en.replace("thyl", "til").replace("phos", "fos").replace("Thio", "Tio").replace("ylic", "ílico").replace("ane", "ano").replace("ine", "ina").replace("ol", "ol")
        
        lore = generate_lore(atoms)
        
        # Gameplay stats
        discovery_points = sum(atoms.values()) * 5
        difficulty = sum(atoms.values()) / 2
        
        new_molecules[formula] = {
            "identity": {
                "formula": formula,
                "names": {"es": name_es, "en": name_en},
                "category": "emergent",
                "family_color": [0.5, 0.5, 0.5] # Grey for neutral/emergent
            },
            "lore": lore,
            "gameplay": {
                "milestones": ["Emergent Discovery"],
                "discovery_points": int(discovery_points),
                "difficulty": round(difficulty, 1)
            }
        }
        
    # Output to new file
    output_data = {"molecules": new_molecules}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"Generated {len(new_molecules)} molecules in {OUTPUT_PATH}")
    if skipped > 0:
        print(f"  [FILTER] Skipped {skipped} blocked formulas")
    if radicals_skipped > 0:
        print(f"  [RADICAL] Filtered {radicals_skipped} unstable radicals")
        # Save radicals to log
        try:
            existing_radicals = []
            if os.path.exists(RADICALS_LOG_PATH):
                with open(RADICALS_LOG_PATH, "r", encoding="utf-8") as f:
                    existing_radicals = json.load(f).get("radicals", [])
            existing_radicals.extend(radicals_detected)
            with open(RADICALS_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump({"radicals": existing_radicals, "total": len(existing_radicals)}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  [WARN] Could not save radicals log: {e}")
    
    # Clear unknown molecules list
    data["unknown_molecules"] = []
    data["summary"]["total_incognitas"] = 0
    
    with open(UNKNOWN_MOLECULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print("Cleared unknown_molecules.json")

if __name__ == "__main__":
    process_molecules()
