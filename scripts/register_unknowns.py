
import json
import os
import re
import sys 

# Add src to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config.molecules import _is_procedural_waste

def register_unknowns():
    """
    Escanea player_molecules.json en busca de 'Desconocida'.
    Si pasan el filtro de calidad (no son basuras procedurales),
    las agrega a unknown_molecules.json para ser auditadas.
    """
    print("🔍 Escaneando descubrimientos del jugador para auditoría...")
    
    player_path = 'data/player_molecules.json'
    target_path = 'data/unknown_molecules.json'

    if not os.path.exists(player_path):
        print(f"❌ No se encontró {player_path}")
        return

    # Cargar moléculas del jugador
    try:
        with open(player_path, 'r', encoding='utf-8') as f:
            player_data = json.load(f)
    except Exception as e:
        print(f"❌ Error leyendo player_molecules.json: {e}")
        return

    # Cargar base de desconocidos existente
    if os.path.exists(target_path):
        with open(target_path, 'r', encoding='utf-8') as f:
            target_data = json.load(f)
    else:
        target_data = {"summary": {}, "unknown_molecules": [], "chemical_anomalies": []}

    existing_formulas = {x['formula'] for x in target_data.get('unknown_molecules', [])}
    
    candidates = []
    
    # Buscar candidatos
    for formula, info in player_data.items():
        name = info.get('name', '')
        
        # Criterio: Se llama "Desconocida" O tiene un nombre placeholder
        if name in ["Desconocida", "[Nombre Sugerido]"]:
            # Filtro 1: ¿Ya la tenemos auditada/pendiente?
            if formula in existing_formulas:
                continue
            
            # Filtro 2: ¿Es basura procedural? (El filtro "inteligente")
            if _is_procedural_waste(formula):
                print(f"⚠️ Ignorando {formula} (Detectada como Residuo Procedural)")
                continue

            # Si pasa, es un candidato válido
            candidates.append(formula)

    if not candidates:
        print("✅ No se encontraron nuevas moléculas desconocidas válidas para auditar.")
        return

    print(f"✨ Encontrados {len(candidates)} candidatos válidos.")
    
    added_count = 0
    for formula in candidates:
        atoms_count = sum(int(n if n else 1) for n in re.findall(r'[A-Z][a-z]?(\d*)', formula))
        
        new_entry = {
            "formula": formula,
            "atoms": atoms_count,
            "suggested_entry": {
                "names": {
                    "es": "[Nombre Sugerido]",
                    "en": "[Suggested Name]"
                },
                "category": "unknown"
            }
        }
        
        target_data.setdefault('unknown_molecules', []).append(new_entry)
        existing_formulas.add(formula)
        added_count += 1
        print(f"➕ Agregada a auditoría: {formula}")

    # Actualizar resumen
    target_data.setdefault('summary', {})
    target_data['summary']['total_incognitas'] = len(target_data['unknown_molecules'])
    
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(target_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n💾 Guardado. {added_count} nuevas entradas en {target_path}")

if __name__ == "__main__":
    register_unknowns()
