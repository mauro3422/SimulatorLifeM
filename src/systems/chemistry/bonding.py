"""
Bonding - Formación de Enlaces Químicos
========================================
Kernels para formación/rotura de enlaces y propagación de IDs de molécula.
"""
import taichi as ti

from src.config.system_constants import MAX_BONDS, MAX_PARTICLES
from src.systems.taichi_fields import (
    # Constantes
    MAX_VALENCE, GRID_CELL_SIZE, GRID_RES, MAX_PER_CELL,
    
    # Campos de partículas
    pos, is_active, atom_types,
    pos_z,  # 2.5D
    
    # Campos de química
    manos_libres, enlaces_idx, num_enlaces, prob_enlace_base,
    
    # Campos de física
    n_particles,
    rango_enlace_max,
    
    # Contadores
    total_bonds_count,
    
    # DEBUG Counters
    debug_particles_checked, debug_neighbors_found, 
    debug_distance_passed, debug_prob_passed,
    
    # Grid espacial
    grid_count, grid_pids,
    
    # Datos atómicos
    AFINIDAD_MATRIX,
    VALENCIAS_MAX,
    ELECTRONEG,
    
    # Molecule ID Propagation
    molecule_id, needs_propagate,
    
    # Medio
    medium_polarity,
    partial_charge,
)


# ===================================================================
# FORMACIÓN DE ENLACES
# ===================================================================

@ti.func
def check_bonding_func_single(i: ti.i32):
    """Formar enlaces para una partícula i - Lógica optimizada (Sin Culling)."""
    if i < n_particles[None] and is_active[i]:
        ti.atomic_add(debug_particles_checked[None], 1)
        if manos_libres[i] > 0.5:
            ti.atomic_add(debug_prob_passed[None], 1)
            
            gx = int(pos[i].x / GRID_CELL_SIZE)
            gy = int(pos[i].y / GRID_CELL_SIZE)
            
            type_i = atom_types[i]
            max_val_i = VALENCIAS_MAX[type_i]
            
            # Buffering local de posición para estabilidad
            pos_i_cached = pos[i]
            pos_z_i_cached = pos_z[i]
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neigh = ti.min(MAX_PER_CELL, grid_count[nx, ny])
                    for k in range(num_neigh):
                        j = grid_pids[nx, ny, k]
                        
                        if i < j:
                            ti.atomic_add(debug_distance_passed[None], 1)
                        
                        if i < j and is_active[j] and manos_libres[j] > 0.5:
                            ti.atomic_add(debug_neighbors_found[None], 1)
                            type_j = atom_types[j]
                            max_val_j = VALENCIAS_MAX[type_j]
                            
                            if num_enlaces[i] < max_val_i and num_enlaces[j] < max_val_j:
                                # Distancia 3D usando valores cacheados de i
                                diff_xy = pos_i_cached - pos[j]
                                diff_z = pos_z_i_cached - pos_z[j]
                                dist_3d = ti.sqrt(diff_xy.x*diff_xy.x + diff_xy.y*diff_xy.y + diff_z*diff_z)
                                
                                if 1.0 < dist_3d < rango_enlace_max[None]:
                                    ti.atomic_add(debug_distance_passed[None], 1)
                                    
                                    # Force bond if already same molecule ID
                                    force_bond = (molecule_id[i] == molecule_id[j] and molecule_id[i] != -1)
                                    
                                    should_bond = False
                                    if force_bond:
                                        should_bond = True
                                    else:
                                        # --- LÓGICA DE CATÁLISIS (Silicio/Arcilla) ---
                                        # Si = 6, C = 0, N = 2
                                        is_clay_catalysis = False
                                        
                                        # 1. Adsorción: C o N se pegan al Silicio (Anclaje)
                                        is_si_anchor = (type_i == 6 and (type_j == 0 or type_j == 2)) or \
                                                       (type_j == 6 and (type_i == 0 or type_i == 2))
                                        
                                        if is_si_anchor:
                                            is_clay_catalysis = True
                                            
                                        # 2. Efecto Template: Pares orgánicos cerca de Silicio
                                        is_organic_pair = ((type_i == 0 or type_i == 2) and 
                                                           (type_j == 0 or type_j == 2))
                                        
                                        if is_organic_pair:
                                            # Buscamos si i o j están anclados a un Si
                                            for b_idx in range(num_enlaces[i]):
                                                neighbor_idx = enlaces_idx[i, b_idx]
                                                if neighbor_idx >= 0 and atom_types[neighbor_idx] == 6:
                                                    is_clay_catalysis = True
                                                    break
                                            
                                            if not is_clay_catalysis:
                                                for b_idx in range(num_enlaces[j]):
                                                    neighbor_idx = enlaces_idx[j, b_idx]
                                                    if neighbor_idx >= 0 and atom_types[neighbor_idx] == 6:
                                                        is_clay_catalysis = True
                                                        break
                                        
                                        prob = ti.min(1.0, prob_enlace_base[None] * AFINIDAD_MATRIX[type_i, type_j])
                                        
                                        if is_clay_catalysis:
                                            # Boost agresivo para estabilidad/anclaje
                                            prob = ti.min(0.98, prob * 5.0) 
                                        
                                        # Efecto hidrofóbico
                                        if medium_polarity[None] > 0.5:
                                            if ELECTRONEG[type_i] < 2.8 and ELECTRONEG[type_j] < 2.8:
                                                prob = ti.min(1.0, prob * 2.0)
                                        
                                        if ti.random() < prob:
                                            # --- VERIFICACIÓN DE SEGURIDAD FINAL (Parche de Saturación) ---
                                            # Evitamos clústeres gigantes que rompen la física (Macro-glitches)
                                            # Reducimos probabilidad si la densidad de enlaces local es muy alta
                                            if is_clay_catalysis and num_enlaces[i] >= 2 and num_enlaces[j] >= 2:
                                                prob *= 0.1 # Freno de mano para redes infinitas
                                            
                                            if ti.random() < prob:
                                                should_bond = True
                                            ti.atomic_add(debug_prob_passed[None], 1)

                                    if should_bond:
                                        idx_i = ti.atomic_add(num_enlaces[i], 1)
                                        idx_j = ti.atomic_add(num_enlaces[j], 1)
                                        
                                        if idx_i < max_val_i and idx_j < max_val_j:
                                            enlaces_idx[i, idx_i] = j
                                            enlaces_idx[j, idx_j] = i
                                            ti.atomic_sub(manos_libres[i], 1.0)
                                            ti.atomic_sub(manos_libres[j], 1.0)
                                            ti.atomic_add(total_bonds_count[None], 1)
                                            
                                            # Molecule ID merge
                                            if not force_bond:
                                                mol_i = molecule_id[i]
                                                mol_j = molecule_id[j]
                                                if mol_i != mol_j:
                                                    if mol_i < mol_j:
                                                        molecule_id[j] = mol_i
                                                        needs_propagate[j] = 1
                                                    else:
                                                        molecule_id[i] = mol_j
                                                        needs_propagate[i] = 1
                                        else:
                                            # Rollback
                                            ti.atomic_sub(num_enlaces[i], 1)
                                            ti.atomic_sub(num_enlaces[j], 1)


@ti.kernel
def check_bonding_gpu():
    for i in range(MAX_PARTICLES):
        check_bonding_func_single(i)


# ===================================================================
# PROPAGACIÓN DE IDS DE MOLÉCULA
# ===================================================================

@ti.kernel
def reset_molecule_ids():
    """RESET (Paso 1): Cada partícula inicia con su propio ID."""
    for i in range(n_particles[None]):
        if is_active[i]:
            molecule_id[i] = i
            if num_enlaces[i] > 0:
                needs_propagate[i] = 1
            else:
                needs_propagate[i] = 0


@ti.kernel
def propagate_molecule_ids_step() -> ti.i32:
    """FLOOD FILL (Paso 2): Propaga el ID menor a través de la red."""
    changes = 0
    for i in range(n_particles[None]):
        if is_active[i] and num_enlaces[i] > 0:
            my_id = molecule_id[i]
            min_id = my_id
            
            n_b = num_enlaces[i]
            for b in range(n_b):
                neighbor = enlaces_idx[i, b]
                if neighbor != -1:
                    neigh_id = molecule_id[neighbor]
                    if neigh_id < min_id:
                        min_id = neigh_id
            
            if min_id < my_id:
                molecule_id[i] = min_id
                changes += 1
                
    return changes


# ===================================================================
# CARGAS PARCIALES
# ===================================================================

@ti.kernel
def update_partial_charges():
    """Calcula la carga parcial dinámica de cada átomo."""
    for i in range(MAX_PARTICLES):
        if is_active[i]:
            type_i = atom_types[i]
            en_i = ELECTRONEG[type_i]
            
            q_accum = 0.0
            
            for k in range(num_enlaces[i]):
                j = enlaces_idx[i, k]
                if j >= 0:
                    type_j = atom_types[j]
                    en_j = ELECTRONEG[type_j]
                    q_accum += (en_j - en_i) * 0.1
            
            partial_charge[i] = q_accum
