import json
import re
from pathlib import Path

def clean_audit_file(max_atoms=64):
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "data" / "unknown_molecules.json"
    
    if not input_path.exists():
        print(f"File not found: {input_path}")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    unknown = data.get("unknown_molecules", [])
    initial_count = len(unknown)
    
    # Filtrar moléculas
    cleaned = []
    glitches = 0
    
    for entry in unknown:
        formula = entry["formula"]
        # Calcular total de átomos
        atoms = sum(int(n if n else 1) for n in re.findall(r'[A-Z][a-z]?(\d*)', formula))
        
        if atoms <= max_atoms:
            cleaned.append(entry)
        else:
            glitches += 1
            
    # Guardar resultados
    with open(input_path, 'w', encoding='utf-8') as f:
        json.dump({
            "unknown_molecules": cleaned,
            "count": len(cleaned),
            "glitch_filtered": glitches
        }, f, indent=2, ensure_ascii=False)
        
    print(f"Audit Cleaned: {initial_count} -> {len(cleaned)} (Removed {glitches} glitches)")

if __name__ == "__main__":
    clean_audit_file()
