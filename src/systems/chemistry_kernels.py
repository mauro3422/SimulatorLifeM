"""
Chemistry Kernels - Taichi GPU Kernels para Química
====================================================
Kernels de química: formación/rotura de enlaces, fuerzas
de resorte y efectos evolutivos (mutación/túnel).
"""
import taichi as ti

from src.systems.taichi_fields import (
    # Constantes
    MAX_VALENCE, GRID_CELL_SIZE, GRID_RES, NUM_ELEMENTS,
    
    # Campos de partículas
    pos, vel, is_active, atom_types,
    
    # Campos de química
    manos_libres, enlaces_idx, num_enlaces, prob_enlace_base,
    
    # Campos de física
    n_particles, max_speed,
    dist_equilibrio, spring_k, damping,
    rango_enlace_min, rango_enlace_max, dist_rotura, max_fuerza,
    
    # Contadores
    total_bonds_count, total_mutations, total_tunnels,
    
    # Grid espacial
    grid_count, grid_pids,
    
    # Datos atómicos
    AFINIDAD_MATRIX
)


# ===================================================================
# FORMACIÓN DE ENLACES
# ===================================================================

@ti.kernel
def check_bonding_gpu():
    """Formar enlaces - SOLO partículas visibles (O(active))."""
    for i in range(n_particles[None]):
        if is_active[i] and manos_libres[i] > 0.5:
            gx = int(pos[i][0] / GRID_CELL_SIZE)
            gy = int(pos[i][1] / GRID_CELL_SIZE)
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neighbors = ti.min(32, grid_count[nx, ny])
                    for k in range(num_neighbors):
                        j = grid_pids[nx, ny, k]
                        if i < j and manos_libres[j] > 0.5:
                            already_bonded = False
                            for b in range(num_enlaces[i]):
                                if enlaces_idx[i, b] == j:
                                    already_bonded = True
                            
                            if not already_bonded:
                                diff = pos[i] - pos[j]
                                dist = diff.norm()
                                if rango_enlace_min[None] < dist < rango_enlace_max[None]:
                                    # Obtener afinidad química entre estos tipos
                                    type_i = atom_types[i]
                                    type_j = atom_types[j]
                                    afinidad = AFINIDAD_MATRIX[type_i, type_j]
                                    
                                    # Probabilidad dinámica (Afectada por MODO REALISMO)
                                    prob_enlace = ti.min(1.0, prob_enlace_base[None] * afinidad)
                                    
                                    if ti.random() < prob_enlace:
                                        idx_i = ti.atomic_add(num_enlaces[i], 1)
                                        idx_j = ti.atomic_add(num_enlaces[j], 1)
                                        if idx_i < MAX_VALENCE and idx_j < MAX_VALENCE:
                                            enlaces_idx[i, idx_i] = j
                                            enlaces_idx[j, idx_j] = i
                                            ti.atomic_sub(manos_libres[i], 1.0)
                                            ti.atomic_sub(manos_libres[j], 1.0)
                                        else:
                                            ti.atomic_sub(num_enlaces[i], 1)
                                            ti.atomic_sub(num_enlaces[j], 1)


# ===================================================================
# FUERZAS DE ENLACE (RESORTE)
# ===================================================================

@ti.kernel
def apply_bond_forces_gpu():
    """Aplicar fuerzas de resorte - GLOBAL (O(N))."""
    for i in range(n_particles[None]):
        if is_active[i]:
            force = ti.Vector([0.0, 0.0])
            n_b = num_enlaces[i]
            for b in range(n_b):
                j = enlaces_idx[i, b]
                if j < 0:
                    continue
                
                pos_j = pos[j]
                diff = pos[i] - pos_j
                dist = diff.norm()
                if dist > 0.001:
                    if dist > dist_rotura[None]:
                        # Romper enlace
                        enlaces_idx[i, b] = -1
                        for b_j in range(num_enlaces[j]):
                            if enlaces_idx[j, b_j] == i:
                                enlaces_idx[j, b_j] = -1
                        
                        ti.atomic_add(manos_libres[i], 1.0)
                        ti.atomic_add(manos_libres[j], 1.0)
                        ti.atomic_sub(total_bonds_count[None], 1)
                    else:
                        # Aplicar fuerza de resorte (Ley de Hooke)
                        direction = diff / dist
                        f_spring = direction * (dist - dist_equilibrio[None]) * spring_k[None]
                        v_rel = vel[i] - vel[j]
                        f_damp = direction * v_rel.dot(direction) * damping[None]
                        force += f_spring + f_damp
            
            # Limitar fuerza máxima
            f_norm = force.norm()
            if f_norm > max_fuerza[None]:
                force = force * (max_fuerza[None] / f_norm)
            vel[i] -= force * 0.3


# ===================================================================
# EFECTOS EVOLUTIVOS
# ===================================================================

@ti.kernel
def apply_evolutionary_effects_gpu():
    """Introduce Mutaciones y Efecto Túnel (O(N))."""
    for i in range(n_particles[None]):
        if is_active[i]:
            # 1. MUTACIÓN (Evolución de tipo) - Muy rara
            if ti.random() < 0.00005: 
                new_type = ti.random(ti.i32) % NUM_ELEMENTS
                atom_types[i] = new_type
                ti.atomic_add(total_mutations[None], 1)
            
            # 2. EFECTO TÚNEL (Teletransportación)
            v_norm = vel[i].norm()
            if v_norm > max_speed[None] * 0.95 and ti.random() < 0.01:
                jump_dist = 60.0  # Salto cuántico
                pos[i] += vel[i].normalized() * jump_dist
                ti.atomic_add(total_tunnels[None], 1)
