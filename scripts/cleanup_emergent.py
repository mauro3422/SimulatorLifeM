"""
cleanup_emergent.py - Clean up emergent.json

1. Name the valuable molecules with proper scientific names
2. Remove trash molecules
3. Add trash to BLOCKLIST so they never appear again
4. Keep neutral molecules for future review
"""

import json
import os

EMERGENT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "molecules", "emergent.json")
TRASH_ARCHIVE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "molecules", "trash_archive.json")
BLOCKLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "molecules", "blocklist.json")

# Nombres científicos para las moléculas valiosas
VALUABLE_NAMES = {
    "C1O3S2": {
        "es": "Tiosulfato de Carbono",
        "en": "Carbon Thiosulfate",
        "lore": "Un compuesto azufrado que puede actuar como catalizador en reacciones prebióticas."
    },
    "C3H3N1O1S1Si1": {
        "es": "Sila-Tiazolina",
        "en": "Sila-Thiazoline", 
        "lore": "Híbrido silicio-azufre con potencial como catalizador termorresistente."
    },
    "C2H3N1O3S3": {
        "es": "Tri-Tioetanolamina",
        "en": "Tri-Thioethanolamine",
        "lore": "Rico en azufre, posible precursor de cofactores enzimáticos primitivos."
    },
    "C1H3N1O2S1": {
        "es": "Tio-Glicinol",
        "en": "Thio-Glycinol",
        "lore": "Análogo azufrado de la glicina, potencial bloque constructor de proto-péptidos."
    },
    "C1H2O1P2S1": {
        "es": "Difosfotiol",
        "en": "Diphosphothiol",
        "lore": "Enlace doble fósforo-azufre, clave para almacenamiento de energía."
    },
    "C2H1N1S2": {
        "es": "Ditio-Acetonitrilo",
        "en": "Dithio-Acetonitrile",
        "lore": "Compuesto cianuro-azufre, posible catalizador de síntesis prebiótica."
    },
    "C3H4O1P1S1": {
        "es": "Fosfo-Tiopropano",
        "en": "Phospho-Thiopropane",
        "lore": "Portador de energía fosfato con grupo tiol activo."
    },
    "C3H2N2O1S1": {
        "es": "Tio-Imidazolina",
        "en": "Thio-Imidazoline",
        "lore": "Anillo nitrogenado con azufre, estructura similar a bases nucléicas."
    },
    "C1N2O1P1": {
        "es": "Fosfo-Carbodiimida",
        "en": "Phospho-Carbodiimide",
        "lore": "Fragmento fosfato-nitrógeno, precursor de enlaces peptídicos."
    },
    "C3H5N1O1S2Si1": {
        "es": "Sila-Ditio-Propilamina",
        "en": "Sila-Dithio-Propylamine",
        "lore": "Híbrido silicio-azufre complejo con potencial catalítico."
    },
    "C4H3N3O4S1": {
        "es": "Proto-Nucleobase Alfa",
        "en": "Proto-Nucleobase Alpha",
        "lore": "¡Estructura similar a una base nucléica! 4C, 3N, 4O y S. Candidato a precursor de ADN."
    },
    "C3H5O6P1S1": {
        "es": "Fosfo-Glicerato Sulfurado",
        "en": "Sulfurated Phosphoglycerate",
        "lore": "Análogo del 3-fosfoglicerato con azufre. Potencial intermediario metabólico."
    },
    "C2H6O1P1": {
        "es": "Etil-Fosfonato",
        "en": "Ethyl Phosphonate",
        "lore": "Éster de fosfato simple, bloque constructor de fosfolípidos."
    },
    "C3H5O2P1": {
        "es": "Fosfo-Propenol",
        "en": "Phospho-Propenol",
        "lore": "Precursor de fosfato orgánico, importante para transferencia de energía."
    }
}

# Fórmulas de basura a eliminar
TRASH_FORMULAS = [
    "H1O3Si1",
    "O2P1Si2", 
    "C3P1S1",
    "H1O2S2",
    "C1O3P1",
    "H2O1P1S1",
    "H1N2P2"
]

def cleanup():
    print("=" * 60)
    print("CLEANING UP EMERGENT.JSON")
    print("=" * 60)
    
    with open(EMERGENT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    molecules = data.get("molecules", {})
    original_count = len(molecules)
    
    # Load existing blocklist (or create new)
    blocklist = set()
    if os.path.exists(BLOCKLIST_PATH):
        with open(BLOCKLIST_PATH, "r", encoding="utf-8") as f:
            bl_data = json.load(f)
            blocklist = set(bl_data.get("blocked_formulas", []))
        print(f"  Loaded {len(blocklist)} formulas from existing blocklist")
    
    # Archive trash before deleting
    trash_archived = {}
    for formula in TRASH_FORMULAS:
        if formula in molecules:
            trash_archived[formula] = molecules.pop(formula)
            blocklist.add(formula)  # Add to blocklist!
            print(f"  [TRASH] Removed + Blocked: {formula}")
    
    # Save trash archive
    with open(TRASH_ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump({"archived_trash": trash_archived, "reason": "Radicales inestables sin valor biologico"}, f, indent=2, ensure_ascii=False)
    print(f"\n  Archived {len(trash_archived)} trash molecules")
    
    # Save blocklist for future filtering
    with open(BLOCKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "blocked_formulas": sorted(list(blocklist)),
            "description": "Formulas que seran ignoradas automaticamente en futuros audits",
            "total": len(blocklist)
        }, f, indent=2, ensure_ascii=False)
    print(f"  Updated blocklist: {len(blocklist)} formulas will be auto-ignored")
    
    # Rename valuable molecules
    renamed_count = 0
    for formula, names_data in VALUABLE_NAMES.items():
        if formula in molecules:
            molecules[formula]["identity"]["names"]["es"] = names_data["es"]
            molecules[formula]["identity"]["names"]["en"] = names_data["en"]
            molecules[formula]["lore"]["origin_story"] = names_data["lore"]
            molecules[formula]["lore"]["utility"] = "Candidato a precursor biologico."
            print(f"  [NAMED] {formula} -> {names_data['es']}")
            renamed_count += 1
    
    # Save cleaned file
    data["molecules"] = molecules
    with open(EMERGENT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"DONE: {original_count} -> {len(molecules)} molecules")
    print(f"  - Removed: {len(trash_archived)} trash")
    print(f"  - Renamed: {renamed_count} valuable")
    print(f"  - Kept: {len(molecules) - renamed_count} neutral")
    print("=" * 60)

if __name__ == "__main__":
    cleanup()
