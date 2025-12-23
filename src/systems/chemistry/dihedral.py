"""
Dihedral Forces - Fuerzas Torsionales
======================================
Kernels para mantener la geometría de 4 átomos (A-B-C-D).
Crea los "zig-zags" característicos de las cadenas de carbono.
"""
import taichi as ti

from src.systems.taichi_fields import (
    # Campos de partículas
    pos, vel, is_active,
    pos_z, vel_z,  # 2.5D
    
    # Campos de química  
    num_enlaces, enlaces_idx,
    
    # Campos de física
    n_particles,
    
    # Constantes de torsión
    DIHEDRAL_K, DIHEDRAL_DAMPING,
)


@ti.func
def apply_dihedral_forces_i(i: ti.i32):
    """
    Aplica fuerzas torsionales para secuencias de 4 átomos A-B-C-D.
    i actúa como el átomo B en la secuencia.
    """
    if num_enlaces[i] >= 2:
        for k_idx in range(num_enlaces[i]):
            j = enlaces_idx[i, k_idx]
            if j > i and j >= 0 and num_enlaces[j] >= 2:
                # B = i, C = j
                pos_b = ti.Vector([pos[i].x, pos[i].y, pos_z[i]])
                pos_c = ti.Vector([pos[j].x, pos[j].y, pos_z[j]])
                
                vec_bc = pos_c - pos_b
                dist_bc = vec_bc.norm()
                
                if dist_bc > 0.1:
                    dir_bc = vec_bc / dist_bc
                    
                    # Vecinos de B (i) para encontrar A
                    for a_idx in range(num_enlaces[i]):
                        a = enlaces_idx[i, a_idx]
                        if a >= 0 and a != j:
                            pos_a = ti.Vector([pos[a].x, pos[a].y, pos_z[a]])
                            vec_ba = pos_a - pos_b
                            
                            # Vecinos de C (j) para encontrar D
                            for d_idx in range(num_enlaces[j]):
                                d = enlaces_idx[j, d_idx]
                                if d >= 0 and d != i:
                                    pos_d = ti.Vector([pos[d].x, pos[d].y, pos_z[d]])
                                    vec_cd = pos_d - pos_c
                                    
                                    # Planos: n1 = ba x bc, n2 = bc x cd
                                    n1 = vec_ba.cross(vec_bc)
                                    n2 = vec_bc.cross(vec_cd)
                                    
                                    n1_mag = n1.norm()
                                    n2_mag = n2.norm()
                                    
                                    if n1_mag > 0.01 and n2_mag > 0.01:
                                        n1 /= n1_mag
                                        n2 /= n2_mag
                                        
                                        # Coseno del ángulo diedro
                                        cos_phi = n1.dot(n2)
                                        
                                        # Si no es anti-periplanar perfecto
                                        if cos_phi > -0.98:
                                            force_mag = (cos_phi + 1.0) * DIHEDRAL_K
                                            
                                            f_a = n1 * force_mag
                                            f_d = -n2 * force_mag
                                            
                                            ti.atomic_add(vel[a], ti.Vector([f_a.x, f_a.y]))
                                            ti.atomic_add(vel_z[a], f_a.z)
                                            ti.atomic_add(vel[d], ti.Vector([f_d.x, f_d.y]))
                                            ti.atomic_add(vel_z[d], f_d.z)


@ti.kernel
def apply_dihedral_forces_gpu():
    """Kernel GPU para aplicar fuerzas torsionales (zig-zags)."""
    for i in range(n_particles[None]):
        if is_active[i]:
            apply_dihedral_forces_i(i)
