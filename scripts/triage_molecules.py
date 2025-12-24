"""
triage_molecules.py - Automatic molecule triage system

Classifies emergent molecules into:
- TRASH: Radicals, transients, Si-only compounds (mark for deletion)
- VALUABLE: Stable biologically-relevant precursors (candidates for promotion)
- NEUTRAL: Keep in emergent for now (interesting but not promotable yet)
"""

import json
import os
import re

EMERGENT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "molecules", "emergent.json")
PRECURSORS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "molecules", "organic", "precursors.json")

def parse_formula(formula):
    """Parse a molecular formula into atom counts."""
    pattern = r'([A-Z][a-z]?)(\d*)'
    atoms = {}
    for match in re.finditer(pattern, formula):
        element = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        if element:
            atoms[element] = atoms.get(element, 0) + count
    return atoms

def calculate_unsaturation(atoms):
    """Calculate Degree of Unsaturation (DoU)."""
    C = atoms.get('C', 0)
    H = atoms.get('H', 0)
    N = atoms.get('N', 0)
    X = 0  # Halogens
    return (2*C + 2 + N - H - X) / 2

def classify_for_triage(formula, mol_data):
    """
    Classify a molecule for triage.
    Returns: ("TRASH" | "VALUABLE" | "NEUTRAL", reason)
    """
    atoms = parse_formula(formula)
    dou = calculate_unsaturation(atoms)
    total_atoms = sum(atoms.values())
    
    C = atoms.get('C', 0)
    H = atoms.get('H', 0)
    N = atoms.get('N', 0)
    O = atoms.get('O', 0)
    P = atoms.get('P', 0)
    S = atoms.get('S', 0)
    Si = atoms.get('Si', 0)
    
    name = mol_data.get("identity", {}).get("names", {}).get("es", "")
    lore = mol_data.get("lore", {}).get("origin_story", "")
    
    # === TRASH CRITERIA ===
    
    # 1. Pure radicals with "Radical" in name and non-integer DoU
    is_radical = dou != int(dou) or "Radical" in name
    
    # 2. Very small molecules (transients) - less than 4 atoms
    is_tiny = total_atoms < 4
    
    # 3. Silicon-only (no carbon) - incompatible with carbon biology
    is_si_only = Si > 0 and C == 0
    
    # 4. No heteroatoms at all (just C and H) - boring hydrocarbons
    is_boring_hydrocarbon = C > 0 and N == 0 and O == 0 and P == 0 and S == 0 and Si == 0
    
    # 5. Marked as "Complex Radical" in lore
    is_complex_radical = "Complex Radical" in lore
    
    if is_radical and is_tiny:
        return ("TRASH", "Tiny radical fragment")
    if is_si_only and is_radical:
        return ("TRASH", "Silicon radical - no carbon biology")
    if is_complex_radical and total_atoms < 6:
        return ("TRASH", "Small complex radical")
    
    # === VALUABLE CRITERIA ===
    
    # 1. Stable isomer with CNOPS (elements of life)
    is_stable = dou == int(dou) or "Stable Isomer" in lore
    has_cnops = C > 0 and (N > 0 or O > 0) and (P > 0 or S > 0)
    
    # 2. Phosphorus + Oxygen = potential energy storage / nucleotide precursor
    has_phosphate_potential = P > 0 and O >= 2
    
    # 3. Contains all 4: C, N, O, and (P or S) - proto-biological
    is_proto_bio = C > 0 and N > 0 and O > 0 and (P > 0 or S > 0)
    
    # 4. Reasonable size for a precursor (5-20 atoms)
    good_size = 5 <= total_atoms <= 20
    
    if is_stable and is_proto_bio and good_size:
        return ("VALUABLE", f"Proto-biological precursor (C{C}N{N}O{O}{'P'+str(P) if P else ''}{'S'+str(S) if S else ''})")
    if is_stable and has_phosphate_potential and good_size:
        return ("VALUABLE", f"Phosphate precursor (P{P}O{O})")
    if is_stable and has_cnops and good_size:
        return ("VALUABLE", f"CNOPS candidate")
    
    # === NEUTRAL (keep watching) ===
    return ("NEUTRAL", "Interesting but not promotable yet")

def run_triage():
    """Run the full triage on emergent.json"""
    
    with open(EMERGENT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    molecules = data.get("molecules", {})
    
    trash = []
    valuable = []
    neutral = []
    
    print("=" * 60)
    print("[TRIAGE] MOLECULE TRIAGE REPORT")
    print("=" * 60)
    
    for formula, mol_data in molecules.items():
        category, reason = classify_for_triage(formula, mol_data)
        name = mol_data.get("identity", {}).get("names", {}).get("es", formula)
        
        if category == "TRASH":
            trash.append((formula, name, reason))
        elif category == "VALUABLE":
            valuable.append((formula, name, reason))
        else:
            neutral.append((formula, name, reason))
    
    # Print results
    print(f"\n[TRASH] ({len(trash)} molecules) - Safe to delete:")
    print("-" * 50)
    for formula, name, reason in trash[:10]:  # Show first 10
        print(f"  [X] {formula} ({name}): {reason}")
    if len(trash) > 10:
        print(f"  ... and {len(trash) - 10} more")
    
    print(f"\n[VALUABLE] ({len(valuable)} molecules) - Candidates for promotion:")
    print("-" * 50)
    for formula, name, reason in valuable:
        print(f"  [*] {formula} ({name}): {reason}")
    
    print(f"\n[NEUTRAL] ({len(neutral)} molecules) - Keep watching:")
    print("-" * 50)
    for formula, name, reason in neutral[:5]:  # Show first 5
        print(f"  [ ] {formula} ({name})")
    if len(neutral) > 5:
        print(f"  ... and {len(neutral) - 5} more")
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(trash)} trash, {len(valuable)} valuable, {len(neutral)} neutral")
    print("=" * 60)
    
    # Save to JSON for full review
    output = {
        "trash": [{"formula": f, "name": n, "reason": r} for f, n, r in trash],
        "valuable": [{"formula": f, "name": n, "reason": r} for f, n, r in valuable],
        "neutral": [{"formula": f, "name": n, "reason": r} for f, n, r in neutral],
        "summary": {
            "trash_count": len(trash),
            "valuable_count": len(valuable),
            "neutral_count": len(neutral)
        }
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "triage_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to: {output_path}")
    
    return trash, valuable, neutral

if __name__ == "__main__":
    run_triage()
