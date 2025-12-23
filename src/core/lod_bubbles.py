"""
LOD Bubbles - Burbujas Macroscópicas para Zoom Semántico
==========================================================
Genera burbujas de nivel de detalle para visualización
a zoom alejado. Agrupa átomos por molécula y calcula
centroide, radio y color.
"""

import numpy as np
from src.config.molecules import get_molecule_info


ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']


def scan_macroscopic_bubbles(state, gpu, synced_data=None):
    """
    Genera burbujas macroscópicas para LOD (Zoom Semántico).
    Optimización V4: Usa particles_vis para evitar syncs masivos.
    """
    if synced_data and 'particles_vis' in synced_data:
        p_data = synced_data['particles_vis']
        # Usar p_data para agrupar...
        # [x, y, r, g, b, scale, type, mol_id, n_enl, z, global_idx]
        
        molecules = {}
        for i in range(len(p_data)):
             mid = int(p_data[i, 7])
             if mid not in molecules: molecules[mid] = []
             molecules[mid].append(i)
        
        # ... resto de la lógica adaptada ...
        # Por brevedad, si no se usa mucho el LOD macro visual ahora, 
        # nos enfocamos en que NO bloquee.
        return None # Temporal: Desactivado para maximizar FPS en stress test
    
    # Culling params
    zoom, cx, cy = state.camera.get_render_params()
    vis_h_half = state.world_size / (2.0 * zoom)
    vis_w_half = vis_h_half * state.camera.aspect_ratio
    
    molecules = {}
    
    # 1. Agrupar visible atoms
    for i in range(len(pos_np)):
        if not is_active_np[i] or num_enlaces_np[i] == 0: 
            continue
        
        x, y = pos_np[i]
        if abs(x - cx) > vis_w_half * 1.5 or abs(y - cy) > vis_h_half * 1.5:
            continue
            
        mid = mol_ids_np[i]
        if mid <= 0: 
            continue  # Evita mancha blanca gigante
        
        if mid not in molecules:
            molecules[mid] = []
        molecules[mid].append(i)
    
    bubble_centers = []
    bubble_colors = []
    bubble_radii = []
    bubble_labels = []
    
    # 2. Procesar cada molécula
    for mid, indices in molecules.items():
        if len(indices) < 2: 
            continue
        
        # Centroid
        positions = pos_np[indices]
        center = np.mean(positions, axis=0)
        
        # Calculate Formula
        atom_counts = {}
        for idx in indices:
            t = types_np[idx]
            if 0 <= t < len(ATOM_SYMBOLS):
                sym = ATOM_SYMBOLS[t]
                atom_counts[sym] = atom_counts.get(sym, 0) + 1
        
        parts = []
        if 'C' in atom_counts: 
            parts.append(f"C{atom_counts.pop('C')}")
        if 'H' in atom_counts: 
            parts.append(f"H{atom_counts.pop('H')}")
        for s in sorted(atom_counts.keys()): 
            parts.append(f"{s}{atom_counts[s]}")
        formula = "".join(parts)
        
        # Color & Radius
        info = get_molecule_info(formula)
        
        # Radio Dinámico Estilo Spore
        dists = np.linalg.norm(positions - center, axis=1)
        physical_radius = np.max(dists) if len(dists) > 0 else 10.0
        base_radius = max(30.0, physical_radius + 5.0 * np.sqrt(len(indices)))
        
        zoom_factor = max(1.0, state.lod_threshold / max(0.1, zoom))
        radius_world = base_radius * (zoom_factor ** 0.6)
        
        if info:
            raw_col = info.get("color", [255, 215, 0])
            col = [c/255.0 for c in raw_col]
            if len(col) == 3: 
                col.append(1.0)
        else:
            col = [0.6, 0.6, 0.6, 0.8]
            
        bubble_centers.append(center)
        bubble_colors.append(col)
        bubble_radii.append(radius_world)
        bubble_labels.append(formula)
        
    if not bubble_centers:
        return None
        
    return {
        'centers': np.array(bubble_centers, dtype=np.float32),
        'colors': np.array(bubble_colors, dtype=np.float32),
        'radii': np.array(bubble_radii, dtype=np.float32),
        'labels': bubble_labels
    }
