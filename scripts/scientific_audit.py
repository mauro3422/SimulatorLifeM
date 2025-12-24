import json
import os

# Database of REAL chemical formulas
# Format: "FORMULA": {"names": {"es": "...", "en": "..."}, "lore": "...", "category": "..."}
REAL_MOLECULES = {
    # Hydrocarbons
    "C1H4": {"names": {"es": "Metano", "en": "Methane"}, "lore": "The simplest alkane and the main constituent of natural gas.", "category": "organic"},
    "C2H6": {"names": {"es": "Etano", "en": "Ethane"}, "lore": "A colorless, odorless gas isolated from natural gas.", "category": "organic"},
    "C3H8": {"names": {"es": "Propano", "en": "Propane"}, "lore": "A three-carbon alkane, a gas at standard temperature and pressure.", "category": "organic"},
    "C4H10": {"names": {"es": "Butano", "en": "Butane"}, "lore": "A gas that is easily liquefied under pressure.", "category": "organic"},
    "C5H12": {"names": {"es": "Pentano", "en": "Pentane"}, "lore": "A volatile liquid alkane.", "category": "organic"},
    "C6H14": {"names": {"es": "Hexano", "en": "Hexane"}, "lore": "A significant constituent of gasoline.", "category": "organic"},
    
    # Alcohols
    "C1H4O1": {"names": {"es": "Metanol", "en": "Methanol"}, "lore": "A simple alcohol, toxic but useful as fuel and solvent.", "category": "organic"},
    "C2H6O1": {"names": {"es": "Etanol", "en": "Ethanol"}, "lore": "Drinking alcohol, also used as fuel and solvent.", "category": "organic"},
    "C3H8O1": {"names": {"es": "Propanol/Isopropanol", "en": "Propanol"}, "lore": "Commonly used as a solvent and antiseptic.", "category": "organic"},
    
    # Acids
    "C1H2O2": {"names": {"es": "Ácido Fórmico", "en": "Formic Acid"}, "lore": "The simplest carboxylic acid, found in ant venom.", "category": "organic"},
    "C2H4O2": {"names": {"es": "Ácido Acético", "en": "Acetic Acid"}, "lore": "The main component of vinegar apart from water.", "category": "organic"},
    
    # Inorganics / Simples
    "H2O": {"names": {"es": "Agua", "en": "Water"}, "lore": "The solvent of life.", "category": "inorganic"},
    "C1O2": {"names": {"es": "Dióxido de Carbono", "en": "Carbon Dioxide"}, "lore": "A gas vital for plant life and a greenhouse gas.", "category": "inorganic"},
    "H3N1": {"names": {"es": "Amoníaco", "en": "Ammonia"}, "lore": "A colorless gas with a distinct pungent smell.", "category": "inorganic"},
    "H4Si1": {"names": {"es": "Silano", "en": "Silane"}, "lore": "A pyrophoric, colorless gas with a sharp, repulsive smell.", "category": "inorganic"},
    "H3P1": {"names": {"es": "Fosfina", "en": "Phosphine"}, "lore": "A toxic gas used in semiconductor industry.", "category": "inorganic"},
    "H2S1": {"names": {"es": "Sulfuro de Hidrógeno", "en": "Hydrogen Sulfide"}, "lore": "A gas with the foul odor of rotten eggs.", "category": "inorganic"},
    
    # Prebiotic / Others
    "C1H1N1": {"names": {"es": "Ácido Cianhídrico", "en": "Hydrogen Cyanide"}, "lore": "A highly toxic liquid or gas, but a prebiotic precursor.", "category": "precursor"},
    "C1H2O1": {"names": {"es": "Formaldehído", "en": "Formaldehyde"}, "lore": "A simple aldehyde, important precursor to complex organics.", "category": "precursor"},
    "C1H4N2O1": {"names": {"es": "Urea", "en": "Urea"}, "lore": "The first organic compound synthesized from inorganic chemicals.", "category": "organic"}
}

def normalize_formula(formula):
    # This is a naive check. A robust one would parse C2H6 vs H6C2.
    # We assume standard formatting from the game engine (Alphabetical order usually?).
    # If the game output C2H6, verify if it's consistent.
    # For now, we use exact match on string, hoping game is consistent.
    return formula

def calculate_unsaturation(atom_counts):
    """
    Calculates Degree of Unsaturation (DoU).
    DoU = C + 1 - H/2 - X/2 + N/2
    X = Halogens (F, Cl, Br, I) -> We treat F, Cl, Br, I generally, but here mostly H.
    P and S can be variable valency, often treated similar to N or O depending on context,
    but standard DoU usually ignores S/O.
    
    If DoU is not an integer, it suggests a Radical (incomplete valence).
    """
    C = atom_counts.get("C", 0) + atom_counts.get("Si", 0) # Si acts like C
    H = atom_counts.get("H", 0)
    N = atom_counts.get("N", 0) + atom_counts.get("P", 0) # P often acts like N (trivalent)
    # O and S are divalent, usually don't affect DoU count directly in this formula
    
    dou = C + 1 - (H / 2) + (N / 2)
    return dou

def classify_molecule(formula, atom_counts):
    # Heuristic classification based on atom counts
    C = atom_counts.get("C", 0)
    H = atom_counts.get("H", 0)
    O = atom_counts.get("O", 0)
    N = atom_counts.get("N", 0)
    S = atom_counts.get("S", 0)
    P = atom_counts.get("P", 0)
    Si = atom_counts.get("Si", 0)
    
    classification = None
    scientific_name = None
    
    dou = calculate_unsaturation(atom_counts)
    is_radical = not dou.is_integer()
    
    # 1. Hydrocarbons
    if C > 0 and H > 0 and O == 0 and N == 0 and S == 0 and P == 0 and Si == 0:
        if is_radical:
            classification = "Radical alkyl"
            scientific_name = f"{get_prefix(C)}yl Radical"
        elif dou == 0:
            classification = "Alkane"
            scientific_name = f"{get_prefix(C)}ane"
        elif dou == 1:
            classification = "Alkene"
            scientific_name = f"{get_prefix(C)}ene"
        elif dou == 2:
            classification = "Alkyne/Diene"
            scientific_name = f"{get_prefix(C)}yne (Isomer)"
        else:
            classification = "Poly-unsaturated Hydrocarbon"
            scientific_name = f"Cyclo-{get_prefix(C)}a-polyene"

    # 2. Simple Oxygenated (Alcohols/Ethers/Aldehydes)
    elif C > 0 and H > 0 and O > 0 and N == 0 and S == 0 and P == 0 and Si == 0:
        if is_radical:
             classification = "Oxidized Radical"
             scientific_name = f"Oxo-{get_prefix(C)}yl Radical"
        elif dou == 0:
             # CnH2n+2O -> Alcohol or Ether
             if H == 2*C + 2:
                 classification = "Alcohol/Ether"
                 scientific_name = f"{get_prefix(C)}anol (Isomer)"
        elif dou == 1:
            # CnH2nO -> Aldehyde or Ketone
            if H == 2*C:
                 classification = "Aldehyde/Ketone"
                 scientific_name = f"{get_prefix(C)}anal (Isomer)"
    
    # 3. Nitrogenous
    elif C > 0 and N > 0:
        if is_radical:
            classification = "Nitrogen Radical"
            scientific_name = f"Amino-{get_prefix(C)}yl Radical"
        elif dou == 0:
            classification = "Amine"
            scientific_name = f"{get_prefix(C)}ylamine"

    # Fallback for complex things with integer DoU
    if not classification and not is_radical:
        classification = "Stable Isomer"
        scientific_name = f"Iso-{formula}"

    # Fallback for complex radicals
    if not classification and is_radical:
        classification = "Complex Radical"
        scientific_name = f"Radical-{formula}"
        
    return classification, scientific_name

def get_prefix(carbon_count):
    prefixes = {1: "Meth", 2: "Eth", 3: "Prop", 4: "But", 5: "Pent", 6: "Hex", 7: "Hept", 8: "Oct", 9: "Non", 10: "Dec"}
    return prefixes.get(carbon_count, f"C{carbon_count}-")

def parse_formula(formula):
    # Very basic parser: "C1H4" -> {"C": 1, "H": 4}
    import re
    atoms = {}
    matches = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    for element, count in matches:
        if count == "": count = 1
        atoms[element] = int(count)
    return atoms

def audit_molecules_file(filepath):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    print(f"--- Auditing {os.path.abspath(filepath)} ---", flush=True)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR loading JSON: {e}", flush=True)
        return

    modified_count = 0
    molecules = data.get("molecules", {})
    
    for formula, mol_data in molecules.items():
        # 1. Exact Match check
        if formula in REAL_MOLECULES:
            real_data = REAL_MOLECULES[formula]
            mol_data["identity"]["names"] = real_data["names"]
            mol_data["lore"]["origin_story"] = "[SCIENTIFICALLY VERIFIED] " + real_data["lore"]
            print(f"✅ EXACT MATCH: {formula} -> {real_data['names']['en']}")
            modified_count += 1
            continue
            
        # 2. Heuristic Check
        atom_counts = parse_formula(formula)
        cls, sci_name = classify_molecule(formula, atom_counts)
        
        if cls:
            old_name = mol_data["identity"]["names"]["en"]
            if sci_name and sci_name != old_name:
                mol_data["identity"]["names"]["en"] = sci_name
                mol_data["identity"]["names"]["es"] = sci_name # Simple copy for now
                mol_data["lore"]["origin_story"] = f"[CLASSIFIED: {cls}] This molecule exhibits the stoichiometry of a {cls}."
                print(f"⚠️ CLASSIFIED: {formula} ({old_name} -> {sci_name})")
                modified_count += 1

    if modified_count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"💾 Saved updates to {filepath}. Modified {modified_count} molecules.")
    else:
        print("No matches or classifications found.")


def audit_unknowns_file(filepath):
    if not os.path.exists(filepath):
        return

    print(f"--- Scanning {filepath} for knowns ---")
    with open(filepath, 'r', encoding='utf-8') as f:
         data = json.load(f)
    
    unknowns = data.get("unknown_molecules", [])
    matches = []
    
    for unk in unknowns:
        formula = unk["formula"]
        if formula in REAL_MOLECULES:
            real_data = REAL_MOLECULES[formula]
            matches.append(f"{formula} -> {real_data['names']['es']}")
            
            # Auto-suggest filling the entry (We don't modify this file directly 
            # to avoid conflict with the game engine writing to it, 
            # but we could output a 'knowns_found.json' to import later)
            
    if matches:
        print(f"🔎 Found {len(matches)} known molecules in unknown list:")
        for m in matches:
            print(f"  - {m}")
    else:
        print("No known molecules found in unknown list.")

    
def analyze_candidates(emergent_filepath):
    """
    Scans the emergent molecules for 'High Value' candidates that resemble 
    biological precursors (C-H-N-O-P-S) and are stable.
    """
    if not os.path.exists(emergent_filepath):
        return

    print(f"\n--- 🧬 Analyzing Candidates for Promotion ({os.path.basename(emergent_filepath)}) ---", flush=True)
    
    with open(emergent_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    candidates = []
    molecules = data.get("molecules", {})
    
    for formula, mol_data in molecules.items():
        atoms = parse_formula(formula)
        dou = calculate_unsaturation(atoms)
        is_stable = dou.is_integer()
        
        # Criteria for "Life-like" candidate:
        # 1. Must be Stable (not a radical)
        # 2. Must contain Carbon
        # 3. Must contain at least one heteroatom (N, O, P, S) to be interesting (not just plain hydrocarbon)
        # 4. Correct size (not too small like CO2, not huge)
        
        has_C = atoms.get("C", 0) > 0
        has_hetero = (atoms.get("N", 0) + atoms.get("O", 0) + atoms.get("P", 0) + atoms.get("S", 0)) > 0
        atom_count = sum(atoms.values())
        
        if is_stable and has_C and has_hetero and 3 < atom_count < 25:
             # Score it? For now just list it.
             candidates.append((formula, mol_data["identity"]["names"]["es"], mol_data["classification"] if "classification" in mol_data else "Unknown"))

    if candidates:
        print(f"💎 Found {len(candidates)} potential candidates for curation:", flush=True)
        # Sort by complexity (atom count approximately inferred from formula length for visualization)
        candidates.sort(key=lambda x: len(x[0])) 
        
        for cand in candidates:
            print(f"  - {cand[0]} ({cand[1]}): Potential Precursor?", flush=True)
            
        print("\n💡 RECOMMENDATION: Review these molecules. If they appear frequently in simulation, move them to 'organic.json' and give them specific specific uses (e.g. 'Membrane Component', 'Catalyst').", flush=True)
    else:
        print("No obvious biological candidates found (mostly radicals or simple hydrocarbons).", flush=True)

if __name__ == "__main__":
    MOLECULES_DIR = os.path.join(os.path.dirname(__file__), "../data/molecules")
    EMERGENT_FILE = os.path.join(MOLECULES_DIR, "emergent.json")
    UNKNOWN_FILE = os.path.join(os.path.dirname(__file__), "../data/unknown_molecules.json")
    
    # 1. Audit Emergent Molecules (Fix the ones we just generated)
    audit_molecules_file(EMERGENT_FILE)
    
    # 2. Check current unknowns
    audit_unknowns_file(UNKNOWN_FILE)

    # 3. Analyze for Promotion
    analyze_candidates(EMERGENT_FILE)
