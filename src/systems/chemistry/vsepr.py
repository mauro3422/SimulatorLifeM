"""
VSEPR - Geometría Molecular
============================
Kernels para mantener ángulos de enlace VSEPR.
Usa física 3D real para geometría tetraédrica, angular, lineal, etc.
"""
import taichi as ti

from src.systems.taichi_fields import (
    # Campos de partículas
    pos, vel, is_active, atom_types,
    pos_z, vel_z,  # 2.5D
    
    # Campos de química
    num_enlaces, enlaces_idx,
    
    # Campos de física
    n_particles,
    
    # Datos atómicos
    VALENCIA_ELECTRONES,
    ELECTRONEG,
)

from src.systems import chemistry_constants as chem
ANGULAR_SPRING_K = chem.ANGULAR_SPRING_K
ANGULAR_DAMPING = chem.ANGULAR_DAMPING
ANGULAR_FORCE_FACTOR = chem.ANGULAR_FORCE_FACTOR


@ti.func
def get_ideal_angle_rad(center_idx: ti.i32, n1_idx: ti.i32, n2_idx: ti.i32) -> ti.f32:
    """
    Calcula el ángulo ideal VSEPR dinámico.
    Considera:
    1. Pares solitarios (LP): Contraen los ángulos de enlace.
    2. Electronegatividad (EN): Vecinos más EN contraen el ángulo.
    """
    type_i = atom_types[center_idx]
    n_b = num_enlaces[center_idx]
    
    valence_e = VALENCIA_ELECTRONES[type_i]
    lone_pairs = ti.max(0.0, float(valence_e - n_b) / 2.0)
    
    # Determinación del sistema base (AXnEm)
    total_domains = float(n_b) + lone_pairs
    angle = 1.911  # 109.5° (Tetraédrico)
    
    if total_domains <= 2.1:
        angle = 3.14159  # 180° (Lineal)
    elif 2.9 < total_domains < 3.1:
        angle = 2.094    # 120° (Trigonal)
    elif total_domains > 4.1:
        angle = 1.571    # 90° (Octaédrico)
        
    # Contracción por pares solitarios
    angle -= lone_pairs * 0.044
    
    # Efecto de electronegatividad (Bent's Rule)
    en_c = ELECTRONEG[type_i]
    en_n1 = ELECTRONEG[atom_types[n1_idx]]
    en_n2 = ELECTRONEG[atom_types[n2_idx]]
    
    en_sensitivity = 0.03
    angle -= (en_n1 - en_c) * en_sensitivity
    angle -= (en_n2 - en_c) * en_sensitivity
    
    return angle


@ti.func
def apply_vsepr_geometry_i(i: ti.i32):
    """
    Aplica fuerzas VSEPR usando geometría 3D real (Sistema 2.5D).
    Incluye lógica de "symmetry breaking" para mover átomos fuera del plano Z=0.
    """
    if is_active[i]:
        n_bonds = num_enlaces[i]
        
        # Symmetry Breaking
        if n_bonds >= 1:
            target_z = 15.0 if (i % 2 == 1) else -15.0
            if ti.abs(pos_z[i] - target_z) > 10.0 and ti.abs(vel_z[i]) < 1.0:
                push_direction = 1.0 if target_z > pos_z[i] else -1.0
                vel_z[i] += push_direction * 5.0
        
        # Solo aplicar VSEPR si tiene 2+ enlaces
        if n_bonds >= 2:
            p_center_x = pos[i].x
            p_center_y = pos[i].y
            p_center_z = pos_z[i]
            
            for b1 in range(n_bonds):
                j1 = enlaces_idx[i, b1]
                if j1 >= 0:
                    v1_x = pos[j1].x - p_center_x
                    v1_y = pos[j1].y - p_center_y
                    v1_z = pos_z[j1] - p_center_z
                    len_v1 = ti.sqrt(v1_x*v1_x + v1_y*v1_y + v1_z*v1_z)
                    
                    if len_v1 >= 0.001:
                        v1_nx = v1_x / len_v1
                        v1_ny = v1_y / len_v1
                        v1_nz = v1_z / len_v1
                        
                        for b2 in range(b1 + 1, n_bonds):
                            j2 = enlaces_idx[i, b2]
                            if j2 >= 0:
                                v2_x = pos[j2].x - p_center_x
                                v2_y = pos[j2].y - p_center_y
                                v2_z = pos_z[j2] - p_center_z
                                len_v2 = ti.sqrt(v2_x*v2_x + v2_y*v2_y + v2_z*v2_z)
                                
                                if len_v2 >= 0.001:
                                    v2_nx = v2_x / len_v2
                                    v2_ny = v2_y / len_v2
                                    v2_nz = v2_z / len_v2
                                    
                                    # Ángulo 3D
                                    dot_3d = v1_nx*v2_nx + v1_ny*v2_ny + v1_nz*v2_nz
                                    dot_3d = ti.math.clamp(dot_3d, -1.0, 1.0)
                                    current_angle = ti.acos(dot_3d)
                                    
                                    ideal_angle = get_ideal_angle_rad(i, j1, j2)
                                    angle_diff = current_angle - ideal_angle
                                    
                                    # HYBRID PHYSICS BYPASS: 
                                    # Skip if angle is near-perfect (< 1.5 degrees) to avoid micro-jitter and save cycles
                                    if ti.abs(angle_diff) > 0.026:
                                        max_force = 10.0
                                        force_mag = ti.tanh((angle_diff * ANGULAR_SPRING_K) / max_force) * max_force * ANGULAR_FORCE_FACTOR
                                        force_mag *= (1.0 - ANGULAR_DAMPING)
                                        
                                        # Eje de rotación (producto cruz)
                                        cross_x = v1_ny*v2_nz - v1_nz*v2_ny
                                        cross_y = v1_nz*v2_nx - v1_nx*v2_nz
                                        cross_z = v1_nx*v2_ny - v1_ny*v2_nx
                                        cross_len = ti.sqrt(cross_x*cross_x + cross_y*cross_y + cross_z*cross_z)
                                        
                                        if cross_len > 0.001:
                                            axis_x = cross_x / cross_len
                                            axis_y = cross_y / cross_len
                                            axis_z = cross_z / cross_len
                                            
                                            # Vectores perpendiculares
                                            perp1_x = axis_y*v1_nz - axis_z*v1_ny
                                            perp1_y = axis_z*v1_nx - axis_x*v1_nz
                                            perp1_z = axis_x*v1_ny - axis_y*v1_nx
                                            
                                            perp2_x = axis_y*v2_nz - axis_z*v2_ny
                                            perp2_y = axis_z*v2_nx - axis_x*v2_nz
                                            perp2_z = axis_x*v2_ny - axis_y*v2_nx
                                            
                                            sign = 1.0 if angle_diff < 0 else -1.0
                                            
                                            vel[j1].x += sign * perp1_x * force_mag
                                            vel[j1].y += sign * perp1_y * force_mag
                                            vel[j2].x -= sign * perp2_x * force_mag
                                            vel[j2].y -= sign * perp2_y * force_mag
                                            
                                            vel_z[j1] += sign * perp1_z * force_mag
                                            vel_z[j2] -= sign * perp2_z * force_mag


@ti.func
def apply_vsepr_geometry_func():
    """Aplica geometría VSEPR a todas las partículas - O(N)."""
    for i in range(n_particles[None]):
        apply_vsepr_geometry_i(i)


@ti.kernel
def apply_vsepr_geometry_gpu():
    """Kernel GPU para geometría VSEPR."""
    apply_vsepr_geometry_func()
