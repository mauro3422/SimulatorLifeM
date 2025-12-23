"""
Molecule Scanner - Escaneo de Moléculas Conocidas
===================================================
Escanea partículas visibles para encontrar moléculas conocidas
usando IDs de molécula propagados en GPU.
"""

import numpy as np
from src.config.molecules import is_known_molecule, get_molecule_info


ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']


def scan_visible_known_molecules(state, gpu, synced_data=None):
    """
    Escanea partículas visibles usando IDs de molécula propagados en GPU.
    Optimización V4: Usa particles_vis para evitar syncs de 10k elementos.
    """
    rings_known_pos = []
    rings_known_col = []
    
    # Nuevo modo V4: Usar solo lo que está en pantalla (Ya traído por render_data segmentado)
    if synced_data and 'particles_vis' in synced_data:
        p_data = synced_data['particles_vis']
        # p_data columns: [x, y, r, g, b, scale, type, mol_id, n_enl, z, global_idx]
        
        molecules = {}
        for i in range(len(p_data)):
            # Culling se asume hecho en GPU para particles_vis
            num_enl = int(p_data[i, 8])
            if num_enl == 0: continue
            
            mid = int(p_data[i, 7])
            if mid not in molecules: molecules[mid] = []
            molecules[mid].append(i)
            
        for mid, indices in molecules.items():
            if len(indices) < 2: continue
            
            # Construir fórmula
            counts = {}
            for idx in indices:
                t = int(p_data[idx, 6])
                if 0 <= t < len(ATOM_SYMBOLS):
                    sym = ATOM_SYMBOLS[t]
                    counts[sym] = counts.get(sym, 0) + 1
            
            formula = "".join([f"{s}{counts[s]}" for s in sorted(counts.keys())])
            # Nota: is_known_molecule maneja la normalización Hill internamente o requiere Hill
            # (Asumimos Hill simplificado para speed)
            
            if is_known_molecule(formula):
                info = get_molecule_info(formula)
                col = [c/255.0 for c in info.get("color", [255,215,0])] if info else [1, 0.84, 0, 0.85]
                if len(col) == 3: col.append(0.85)

                for idx in indices:
                    rings_known_pos.append(p_data[idx, 0:2])
                    rings_known_col.append(col)
                    
        if rings_known_pos:
            return (np.array(rings_known_pos), np.array(rings_known_col))
        return (np.array([]), np.array([]))

    # Fallback modo Legacy (Solo para misiones/detección total)
    mol_ids_np = synced_data['molecule_id'] if synced_data else state.sim['molecule_id'].to_numpy()
    pos_np = synced_data['pos'] if synced_data else gpu['pos'].to_numpy()
    types_np = synced_data['atom_types'] if synced_data else state.sim['atom_types'].to_numpy()
    num_enlaces_np = synced_data['num_enlaces'] if synced_data else gpu['num_enlaces'].to_numpy()
    is_active_np = synced_data['is_active'] if synced_data else state.sim['is_active'].to_numpy()
    
    # Culling params
    zoom, cx, cy = state.camera.get_render_params()
    vis_h_half = 15000.0 / (2.0 * zoom)
    vis_w_half = vis_h_half * state.camera.aspect_ratio
    
    # Agrupar partículas visibles por ID de molécula
    molecules = {}
    
    for i in range(len(pos_np)):
        if not is_active_np[i]: 
            continue
        if num_enlaces_np[i] == 0: 
            continue  # Átomos sueltos no cuentan
        
        # Culling: solo procesar si está en vista
        x, y = pos_np[i]
        if abs(x - cx) > vis_w_half * 1.2 or abs(y - cy) > vis_h_half * 1.2:
            continue
            
        mid = mol_ids_np[i]
        if mid not in molecules:
            molecules[mid] = []
        molecules[mid].append(i)
    
    # Verificar fórmulas para cada grupo
    for mid, indices in molecules.items():
        if len(indices) < 2: 
            continue
        
        # Calcular Fórmula
        atom_counts = {}
        for idx in indices:
            t = types_np[idx]
            if 0 <= t < len(ATOM_SYMBOLS):
                sym = ATOM_SYMBOLS[t]
                atom_counts[sym] = atom_counts.get(sym, 0) + 1
        
        # Ordenar sistema Hill (C, H, resto alfabético)
        formula_parts = []
        if 'C' in atom_counts:
            c_count = atom_counts.pop('C')
            formula_parts.append(f"C{c_count}")
            if 'H' in atom_counts:
                h_count = atom_counts.pop('H')
                formula_parts.append(f"H{h_count}")
        
        for sym in sorted(atom_counts.keys()):
            count = atom_counts[sym]
            formula_parts.append(f"{sym}{count}")
        
        formula = "".join(formula_parts)
        
        # Verificar base de datos
        if is_known_molecule(formula):
            info = get_molecule_info(formula)
            raw_col = info.get("color", [255, 215, 0]) if info else [255, 215, 0]
            
            # Normalize to float 0.0-1.0 and add Alpha
            norm_col = [c/255.0 for c in raw_col]
            if len(norm_col) == 3: 
                norm_col.append(0.85)
            
            # Agregar posiciones para highlight
            for idx in indices:
                rings_known_pos.append(pos_np[idx])
                rings_known_col.append(norm_col)
    
    if len(rings_known_pos) > 0:
        return (np.array(rings_known_pos, dtype=np.float32), 
                np.array(rings_known_col, dtype=np.float32))
    else:
        return (np.array([], dtype=np.float32), 
                np.array([], dtype=np.float32))
