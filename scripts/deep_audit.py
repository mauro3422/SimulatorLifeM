import json
import re
from pathlib import Path

def parse_formula(formula):
    return {m[0]: int(m[1] if m[1] else 1) for m in re.findall(r'([A-Z][a-z]?)(\d*)', formula)}

def audit_molecules():
    path = Path("data/unknown_molecules.json")
    if not path.exists():
        print("No se encontró el archivo de incógnitas.")
        return

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    unknowns = data.get("unknown_molecules", [])
    results = {
        "plausible": [],
        "unstable_hydrogen": [],
        "over-oxidized": [],
        "complex_metal_organics": [],
        "simple_fragments": []
    }

    # Valencias estándar
    valencias = {
        "H": 1, "C": 4, "N": 3, "O": 2, "P": 5, "S": 6, "Si": 4
    }

    for mol in unknowns:
        formula = mol["formula"]
        atoms = parse_formula(formula)
        total_atoms = sum(atoms.values())
        
        # 1. Filtro de Fragmentos Simples
        if total_atoms <= 4:
            results["simple_fragments"].append(formula)
            continue

        # 2. Heurística de Hidrógeno (Regla de saturación C_n H_{2n+2})
        c = atoms.get("C", 0)
        h = atoms.get("H", 0)
        if c > 0 and h > (2 * c + 6): # Margen generoso para heteroátomos
            results["unstable_hydrogen"].append(formula)
            continue

        # 3. Heurística de Oxígeno (Sobre-oxidación)
        o = atoms.get("O", 0)
        if o > (total_atoms / 2) and total_atoms > 5:
            results["over-oxidized"].append(formula)
            continue

        # 4. Siliconas / Silicatos
        if "Si" in atoms:
            results["complex_metal_organics"].append(formula)
            continue

        results["plausible"].append(formula)

    print(f"\n=== REPORTE DE AUDITORÍA AUTOMATIZADA ===")
    print(f"Total analizadas: {len(unknowns)}")
    print(f"✅ Plausibles: {len(results['plausible'])}")
    print(f"💧 Exceso H: {len(results['unstable_hydrogen'])}")
    print(f"🔥 Sobre-oxidación: {len(results['over-oxidized'])}")
    print(f"🧪 Silicatos/Especiales: {len(results['complex_metal_organics'])}")
    print(f"✂️ Fragmentos < 5 at: {len(results['simple_fragments'])}")
    
    # Guardar reporte detallado
    report_path = Path("data/audit_results.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    audit_molecules()
