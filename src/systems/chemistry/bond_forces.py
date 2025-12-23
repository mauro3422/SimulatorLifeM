"""
Bond Forces - Fuerzas de Enlace (Resorte)
==========================================
Kernels para fuerzas de atracción química entre átomos enlazados.
Usa Ley de Hooke + rotura por distancia y térmica.
"""
import taichi as ti

from src.systems.taichi_fields import (
    # Campos de partículas
    pos, vel, is_active,
    pos_z, vel_z,  # 2.5D
    
    # Campos de química
    manos_libres, enlaces_idx, num_enlaces,
    
    # Campos de física
    n_particles,
    dist_equilibrio, spring_k, damping,
    dist_rotura, max_fuerza,
    temperature,
    
    # Contadores
    total_bonds_count, total_bonds_broken_dist,
    
    # Jugador
    player_idx,
    
    # Factor de fuerza
    BOND_FORCE_FACTOR,
)


@ti.func
def apply_bond_forces_i(i: ti.i32):
    """Aplica fuerzas de atracción química para una partícula.
    
    NOTA: Usa distancia 3D (incluyendo pos_z) para consistencia con VSEPR.
    """
    if is_active[i]:
        force = ti.Vector([0.0, 0.0])
        force_z = 0.0
        n_b = num_enlaces[i]
        for b in range(n_b):
            j = enlaces_idx[i, b]
            if j < 0:
                continue
            
            # Calcular distancia 3D
            pos_j = pos[j]
            diff_xy = pos[i] - pos_j
            diff_z = pos_z[i] - pos_z[j]
            
            dist_3d = ti.sqrt(diff_xy.x*diff_xy.x + diff_xy.y*diff_xy.y + diff_z*diff_z)
            
            if dist_3d > 0.001:
                dir_xy = diff_xy / dist_3d
                dir_z = diff_z / dist_3d
                
                # Rotura por distancia (excepto enlaces del jugador)
                if dist_3d > dist_rotura[None]:
                    # PROTECCIÓN: No romper enlaces del jugador
                    p_idx = player_idx[None]
                    is_player_bond = (i == p_idx) or (j == p_idx)
                    
                    if not is_player_bond:
                        enlaces_idx[i, b] = -1
                        for b_j in range(num_enlaces[j]):
                            if enlaces_idx[j, b_j] == i:
                                enlaces_idx[j, b_j] = -1
                        
                        ti.atomic_add(manos_libres[i], 1.0)
                        ti.atomic_add(manos_libres[j], 1.0)
                        if i < j:
                            ti.atomic_sub(total_bonds_count[None], 1)
                            ti.atomic_add(total_bonds_broken_dist[None], 1)
                
                # Rotura térmica (solo para moléculas grandes)
                elif i < j:
                    connectivity = num_enlaces[i] + num_enlaces[j]
                    
                    if connectivity >= 6:
                        temp = temperature[None]
                        thermal_prob = 0.0005 * float(connectivity - 5) * (temp + 0.05)
                        
                        if ti.random() < thermal_prob:
                            enlaces_idx[i, b] = -1
                            for b_j in range(num_enlaces[j]):
                                if enlaces_idx[j, b_j] == i:
                                    enlaces_idx[j, b_j] = -1
                            
                            ti.atomic_add(manos_libres[i], 1.0)
                            ti.atomic_add(manos_libres[j], 1.0)
                            ti.atomic_sub(total_bonds_count[None], 1)
                        else:
                            # Fuerza de resorte 3D
                            f_spring_mag = (dist_3d - dist_equilibrio[None]) * spring_k[None]
                            force += dir_xy * f_spring_mag
                            force_z += dir_z * f_spring_mag
                            v_rel = vel[i] - vel[j]
                            v_rel_z = vel_z[i] - vel_z[j]
                            f_damp = dir_xy.dot(v_rel) * damping[None]
                            force += dir_xy * f_damp
                            force_z += dir_z * v_rel_z * damping[None]
                    else:
                        # Moléculas pequeñas: solo fuerza de resorte
                        f_spring_mag = (dist_3d - dist_equilibrio[None]) * spring_k[None]
                        force += dir_xy * f_spring_mag
                        force_z += dir_z * f_spring_mag
                        v_rel = vel[i] - vel[j]
                        v_rel_z = vel_z[i] - vel_z[j]
                        f_damp = dir_xy.dot(v_rel) * damping[None]
                        force += dir_xy * f_damp
                        force_z += dir_z * v_rel_z * damping[None]
                else:
                    # Para i >= j, sin check térmico
                    f_spring_mag = (dist_3d - dist_equilibrio[None]) * spring_k[None]
                    force += dir_xy * f_spring_mag
                    force_z += dir_z * f_spring_mag
                    v_rel = vel[i] - vel[j]
                    v_rel_z = vel_z[i] - vel_z[j]
                    f_damp = dir_xy.dot(v_rel) * damping[None]
                    force += dir_xy * f_damp
                    force_z += dir_z * v_rel_z * damping[None]
        
        # Limitar fuerza máxima
        f_norm = ti.sqrt(force.x*force.x + force.y*force.y + force_z*force_z)
        if f_norm > max_fuerza[None]:
            scale = max_fuerza[None] / f_norm
            force = force * scale
            force_z = force_z * scale
        vel[i] -= force * BOND_FORCE_FACTOR
        vel_z[i] -= force_z * BOND_FORCE_FACTOR


@ti.func
def apply_bond_forces_func():
    """Aplicar fuerzas de resorte - Versión O(N)."""
    for i in range(n_particles[None]):
        apply_bond_forces_i(i)


@ti.kernel
def apply_bond_forces_gpu():
    apply_bond_forces_func()
