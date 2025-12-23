import taichi as ti
import numpy as np
import json
from src.systems.taichi_fields import molecule_id, atom_types, num_enlaces, n_particles, is_active

def analyze_macro_molecules():
    """
    Escanea la simulación en busca de clústeres moleculares que violen las leyes físicas.
    """
    ti.sync()
    ids = molecule_id.to_numpy()
    types = atom_types.to_numpy()
    active = is_active.to_numpy()
    n = n_particles[None]
    
    clusters = {}
    for i in range(n):
        if not active[i]: continue
        m_id = ids[i]
        if m_id not in clusters:
            clusters[m_id] = []
        clusters[m_id].append(types[i])
        
    print(f"\n[FORENSIC] Analizando {len(clusters)} grupos moleculares...")
    
    glitches = []
    for m_id, members in clusters.items():
        if len(members) > 50:
            glitches.append({
                "id": int(m_id),
                "size": len(members),
                "composition": str(members[:20]) + "..."
            })
            
    if glitches:
        print(f"❌ ¡ATENCIÓN! Detectados {len(glitches)} macro-glitches:")
        for g in glitches:
            print(f"  - Molécula {g['id']}: {g['size']} átomos. Composición inicial: {g['composition']}")
    else:
        print("✅ No se detectan macro-glitches extremos en este snapshot.")

if __name__ == "__main__":
    # Este script se importaría en main.py o se correría con un snapshot
    print("Iniciando monitor forense...")
