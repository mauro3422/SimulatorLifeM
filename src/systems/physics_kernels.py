"""
Physics Kernels - Taichi GPU Kernels para Física
=================================================
Kernels de física básica: gravedad, fricción, colisiones,
movimiento Browniano y repulsión de Coulomb.
"""
import taichi as ti

from src.systems.taichi_fields import (
    # Constantes
    GRID_CELL_SIZE, GRID_RES, MAX_VALENCE,
    BROWNIAN_K, BROWNIAN_BASE_TEMP,
    COULOMB_K, REPULSION_MIN_DIST, REPULSION_MAX_DIST,
    ELECTRONEG_AVG, NUM_ELEMENTS,
    # Efectos evolutivos
    MUTATION_PROBABILITY, TUNNEL_VELOCITY_THRESHOLD, 
    TUNNEL_PROBABILITY, TUNNEL_JUMP_DISTANCE,
    # Factores de fuerza
    COULOMB_FORCE_FACTOR, VELOCITY_DERIVATION, COLLISION_CORRECTION,
    
    # Campos de partículas (Sistema 2.5D)
    pos, vel, pos_old, radii, is_active, atom_types,
    pos_z, vel_z,  # 2.5D: posición y velocidad en Z
    
    # Campos de física
    n_particles, gravity, friction, temperature, max_speed,
    world_width, world_height, charge_factor,
    medium_type, medium_viscosity, medium_polarity,
    partial_charge,
    
    # Grid espacial
    grid_count, grid_pids, sim_bounds,
    
    # Química (para Puentes de Hidrógeno y Tractor Beam)
    num_enlaces, enlaces_idx, manos_libres, player_idx,
    
    # Contadores (Fusionados)
    total_mutations, total_tunnels, n_simulated_physics,
    
    # Datos atómicos
    ELECTRONEG, MASAS_ATOMICAS
)

# Constantes de profundidad 2.5D y Física Avanzada
from src.systems import physics_constants as phys
DEPTH_Z_AMPLITUDE = phys.DEPTH_Z_AMPLITUDE
HYDROPHOBIC_K = phys.HYDROPHOBIC_K
HBOND_BOOST = phys.HBOND_BOOST

# ... (Previous imports) ...




# ===================================================================
# FÍSICA BÁSICA
# ===================================================================

@ti.func
def physics_pre_step_i(i: ti.i32):
    """Lógica de pre-paso para una partícula."""
    if is_active[i] != 0:
        # Culling Check
        if (sim_bounds[0] < pos[i].x < sim_bounds[2] and 
            sim_bounds[1] < pos[i].y < sim_bounds[3]):
            
            ti.atomic_add(n_simulated_physics[None], 1)

            vel[i].y += gravity[None] * 5.0
            
            # Aplicar fricción base + viscosidad del medio
            eff_friction = friction[None] * (1.0 - medium_viscosity[None] * 0.1)
            vel[i] *= eff_friction
            
            if temperature[None] > 0:
                vel[i] += ti.Vector([ti.random()-0.5, ti.random()-0.5]) * temperature[None] * 20.0

            speed = vel[i].norm()
            if speed > max_speed[None]:
                vel[i] = vel[i] / speed * max_speed[None]
            
            pos_old[i] = pos[i]
            pos[i] += vel[i]
            
            # 2.5D: Integrar velocidad Z a posición Z
            # Z friction slightly higher than XY for damping, but not too aggressive
            vel_z[i] *= friction[None] * 0.98  # Reduced friction for VSEPR
            
            # Z velocity limit: allow reasonable 3D motion for molecular geometry
            max_vel_z = max_speed[None] * 0.8  # Increased for proper VSEPR
            if vel_z[i] > max_vel_z:
                vel_z[i] = max_vel_z
            if vel_z[i] < -max_vel_z:
                vel_z[i] = -max_vel_z
            
            pos_z[i] += vel_z[i]
            
            # Limitar amplitud Z y resetear velocidad si toca límite
            if pos_z[i] > DEPTH_Z_AMPLITUDE:
                pos_z[i] = DEPTH_Z_AMPLITUDE
                vel_z[i] = 0.0
            if pos_z[i] < -DEPTH_Z_AMPLITUDE:
                pos_z[i] = -DEPTH_Z_AMPLITUDE
                vel_z[i] = 0.0

@ti.func
def physics_pre_step_func():
    """Fuerzas iniciales y predicción de posición."""
    for i in range(n_particles[None]):
        physics_pre_step_i(i)

@ti.kernel
def physics_pre_step():
    n_simulated_physics[None] = 0
    physics_pre_step_func()


@ti.func
def physics_post_step_func(t_total: ti.f32, run_advanced: ti.i32):
    """Derivar velocidad final."""
    for i in range(n_particles[None]):
        physics_post_step_i(i, t_total, run_advanced)

@ti.kernel
def physics_post_step(t_total: ti.f32, run_advanced: ti.i32):
    physics_post_step_func(t_total, run_advanced)


# ===================================================================
# FÍSICA MODULAR: REGLAS CUSTOM (Inyectables en Ultra-Loop)
# ===================================================================

@ti.func
def apply_brownian_i(i: ti.i32, t_total: ti.f32):
    """Regla: Agitación Térmica."""
    atom_type = atom_types[i]
    mass = MASAS_ATOMICAS[atom_type]
    v_rms = ti.sqrt(BROWNIAN_K * t_total / mass)
    
    # Dirección aleatoria
    dx = ti.random() - 0.5
    dy = ti.random() - 0.5
    length = ti.sqrt(dx*dx + dy*dy) + 1e-8
    
    # Magnitud aleatoria
    magnitude = v_rms * ti.random()
    vel[i] += ti.Vector([dx/length * magnitude, dy/length * magnitude])

@ti.func
def apply_evolution_i(i: ti.i32):
    """Regla: Efectos Especiales (Mutación y Túnel)."""
    # 1. Mutación
    if ti.random() < MUTATION_PROBABILITY: 
        new_type = ti.random(ti.i32) % NUM_ELEMENTS
        atom_types[i] = new_type
        ti.atomic_add(total_mutations[None], 1)
    
    # 2. Túnel Cuántico
    v_norm = vel[i].norm()
    if v_norm > max_speed[None] * TUNNEL_VELOCITY_THRESHOLD and ti.random() < TUNNEL_PROBABILITY:
        vel_dir = vel[i].normalized()
        pos[i] += vel_dir * TUNNEL_JUMP_DISTANCE
        ti.atomic_add(total_tunnels[None], 1)

@ti.func
def apply_electrostatic_forces_i(i: ti.i32):
    """
    Regla: Fuerzas Electrostáticas Universales (UFF).
    Calcula atracción y repulsión basada en partial_charge dinámico.
    """
    q_i = partial_charge[i]
    type_i = atom_types[i]
    
    if ti.abs(q_i) > 0.001: # Optimización: Skip si es neutro
        gx = int(pos[i][0] / GRID_CELL_SIZE)
        gy = int(pos[i][1] / GRID_CELL_SIZE)
        total_force_xy = ti.Vector([0.0, 0.0])
        total_force_z = 0.0
        
        for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
            nx, ny = gx + ox, gy + oy
            if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                num_neighbors = ti.min(16, grid_count[nx, ny]) # Reducido para performance
                for k in range(num_neighbors):
                    j = grid_pids[nx, ny, k]
                    if i != j:
                        type_j = atom_types[j]
                        q_j = partial_charge[j]
                        
                        # Solo si hay carga apreciable
                        if ti.abs(q_j) > 0.001:
                            diff_xy = pos[j] - pos[i] # Vector i -> j
                            diff_z = pos_z[j] - pos_z[i]
                            dist_sq_3d = diff_xy.x*diff_xy.x + diff_xy.y*diff_xy.y + diff_z*diff_z
                            
                            # Rango de electrostática
                            if 2.0 < dist_sq_3d < 10000.0: # Rango ~100 unidades
                                dist_3d = ti.sqrt(dist_sq_3d)
                                
                                # Ley de Coulomb: F = k * (q1 * q2) / r^2
                                force_mag = COULOMB_K * (q_i * q_j) / ti.max(dist_sq_3d, 10.0)
                                
                                # PUENTE DE HIDRÓGENO (Atracción Direccional Especial)
                                # Si i es H y j es atractor (O, N con carga negativa)
                                # Buscamos la alineación D-H...A
                                if type_i == 1 and q_j < -0.1: # H y Aceptor negativo
                                    # Encontrar donante D (índice 0 porque H solo tiene 1 enlace)
                                    if num_enlaces[i] > 0:
                                        d = enlaces_idx[i, 0]
                                        if d >= 0:
                                            # Vector D -> H
                                            vec_dh = (pos[i] - pos[d]) # XY
                                            vec_dh_z = pos_z[i] - pos_z[d]
                                            dist_dh = ti.sqrt(vec_dh.x**2 + vec_dh.y**2 + vec_dh_z**2)
                                            
                                            if dist_dh > 0.1:
                                                # Dirección D->H (Normalizada)
                                                dir_dh_x = vec_dh.x / dist_dh
                                                dir_dh_y = vec_dh.y / dist_dh
                                                dir_dh_z = vec_dh_z / dist_dh
                                                
                                                # Dirección H->A (Normalizada)
                                                dir_ha_x = diff_xy.x / dist_3d
                                                dir_ha_y = diff_xy.y / dist_3d
                                                dir_ha_z = diff_z / dist_3d
                                                
                                                # Producto punto (cos del ángulo entre D-H y H-A)
                                                # Si es 1.0, están perfectamente alineados (180°)
                                                alignment = dir_dh_x * dir_ha_x + dir_dh_y * dir_ha_y + dir_dh_z * dir_ha_z
                                                
                                                if alignment > 0.8: # Umbral de ~36 grados
                                                    # Reforzar atracción
                                                    force_mag *= HBOND_BOOST
                                
                                # Limitar fuerza por par para estabilidad
                                force_mag = ti.max(ti.min(force_mag, 2.0), -2.0)
                                
                                # Aplicar fuerza (Repulsiva aleja de pos[j], atractiva acerca)
                                total_force_xy -= (diff_xy / dist_3d) * force_mag
                                total_force_z -= (diff_z / dist_3d) * force_mag
        
        # Escalar por masa
        type_i = atom_types[i]
        mass = MASAS_ATOMICAS[type_i]
        # El COULOMB_FORCE_FACTOR ahora es maestro
        vel[i] += total_force_xy / mass * COULOMB_FORCE_FACTOR
        vel_z[i] += total_force_z / mass * COULOMB_FORCE_FACTOR

@ti.func
def apply_hydrophobic_attraction_i(i: ti.i32):
    """
    Simula el EFECTO HIDROFÓBICO: Atracción entre átomos no polares en medios polares.
    Esto ayuda a que las moléculas orgánicas 'se mantengan' unidas.
    """
    if is_active[i] != 0 and medium_polarity[None] > 0.5:
        type_i = atom_types[i]
        # Solo átomos no polares (C, H, S) - EN < 2.8
        if ELECTRONEG[type_i] < 2.8:
            gx = int(pos[i].x / GRID_CELL_SIZE)
            gy = int(pos[i].y / GRID_CELL_SIZE)
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neigh = ti.min(16, grid_count[nx, ny])
                    for k in range(num_neigh):
                        j = grid_pids[nx, ny, k]
                        if i < j and is_active[j] != 0:
                            type_j = atom_types[j]
                            if ELECTRONEG[type_j] < 2.8:
                                diff_xy = pos[j] - pos[i]
                                diff_z = pos_z[j] - pos_z[i]
                                dist_3d = ti.sqrt(diff_xy.x*diff_xy.x + diff_xy.y*diff_xy.y + diff_z*diff_z)
                                
                                # Atracción de rango medio (atracción de 'solvofobia')
                                if 5.0 < dist_3d < 80.0:
                                    # Fuerza tipo Lennard-Jones atractiva o similar
                                    force_mag = HYDROPHOBIC_K / (dist_3d * 0.1)
                                    f_xy = (diff_xy / dist_3d) * force_mag
                                    f_z = (diff_z / dist_3d) * force_mag
                                    
                                    vel[i] += f_xy * 0.05
                                    vel_z[i] += f_z * 0.05
                                    vel[j] -= f_xy * 0.05
                                    vel_z[j] -= f_z * 0.05

@ti.func
def apply_tractor_beam_i(i: ti.i32):
    """
    Simula el 'TRACTOR BEAM' de Carbono: Atracción pasiva de recursos cercanos
    si el jugador es Carbono y tiene manos libres.
    """
    p_idx = player_idx[None]
    if i == p_idx and atom_types[i] == 0: # El jugador es Carbono
        if manos_libres[i] > 0.5:
            gx = int(pos[i].x / GRID_CELL_SIZE)
            gy = int(pos[i].y / GRID_CELL_SIZE)
            
            # Rango de atracción del tractor beam
            ATTRACT_RANGE = 200.0
            ATTRACT_RANGE_SQ = ATTRACT_RANGE * ATTRACT_RANGE
            ATTRACT_FORCE = 0.8
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neigh = ti.min(16, grid_count[nx, ny])
                    for k in range(num_neigh):
                        j = grid_pids[nx, ny, k]
                        if i != j and is_active[j] != 0:
                            # Solo atraer si j NO está ya enlazado a i
                            already_bonded = False
                            for s in range(ti.static(MAX_VALENCE)):
                                if enlaces_idx[i, s] == j:
                                    already_bonded = True
                            
                            if not already_bonded:
                                diff = pos[i] - pos[j]
                                dist_sq = diff.norm_sqr()
                                if 5.0 < dist_sq < ATTRACT_RANGE_SQ:
                                    dist = ti.sqrt(dist_sq)
                                    # Atracción suave 1/r
                                    force = (diff / dist) * (ATTRACT_FORCE * (1.0 - dist/ATTRACT_RANGE))
                                    vel[j] += force

@ti.func
def apply_metabolism_i(i: ti.i32):
    """Regla de Ejemplo: El átomo 'crece' ligeramente si está muy activo."""
    if vel[i].norm() > 2.0:
        radii[i] = ti.min(radii[i] + 0.001, 20.0)

@ti.func
def resolve_constraints_grid_i(i: ti.i32):
    """Lógica de colisiones para una partícula."""
    if is_active[i] != 0:
        # Culling Check
        if (sim_bounds[0] < pos[i].x < sim_bounds[2] and 
            sim_bounds[1] < pos[i].y < sim_bounds[3]):

            # Paredes
            r = radii[i]
            if pos[i][0] < r: pos[i][0] = r
            if pos[i][0] > world_width[None] - r: pos[i][0] = world_width[None] - r
            if pos[i][1] < r: pos[i][1] = r
            if pos[i][1] > world_height[None] - r: pos[i][1] = world_height[None] - r
            
            # Colisiones via grid
            gx = int(pos[i][0] / GRID_CELL_SIZE)
            gy = int(pos[i][1] / GRID_CELL_SIZE)
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neighbors = ti.min(32, grid_count[nx, ny])
                    for k in range(num_neighbors):
                        j = grid_pids[nx, ny, k]
                        if i < j:
                            # Distancia 3D para colisiones (Sistema 2.5D)
                            diff_xy = pos[i] - pos[j]
                            diff_z = pos_z[i] - pos_z[j]
                            dist_3d = ti.sqrt(diff_xy.x*diff_xy.x + diff_xy.y*diff_xy.y + diff_z*diff_z)
                            
                            sum_radii = radii[i] + radii[j]
                            if 0.001 < dist_3d < sum_radii:
                                overlap = sum_radii - dist_3d
                                # Corrección proporcional en cada eje
                                scale = overlap * COLLISION_CORRECTION / dist_3d
                                correction_xy = diff_xy * scale
                                correction_z = diff_z * scale
                                # Aplicar corrección en XY
                                pos[i] += correction_xy * 0.5
                                pos[j] -= correction_xy * 0.5
                                # Aplicar corrección en Z
                                pos_z[i] += correction_z * 0.5
                                pos_z[j] -= correction_z * 0.5



@ti.func
def apply_brownian_i(i: ti.i32, t: ti.f32):
    """Movimiento Browniano (depende de temperatura y masa)."""
    # ... (existente) ...
    # Reutilizando lógica existente, simplificado para este snippet 
    # (En realidad, el browniano ya está en pre-step, esto es solo placeholder si se mueve aquí)
    pass

@ti.func
def apply_van_der_waals_i(i: ti.i32):
    """
    Fuerzas de Cohesión 3D (Van der Waals / Lennard-Jones soft).
    Atrae partículas cercanas para formar líquidos.
    """
    # Usar grid para eficiencia
    gx = int(pos[i][0] / GRID_CELL_SIZE)
    gy = int(pos[i][1] / GRID_CELL_SIZE)
    
    # Rango de efecto visual ~ 3 veces el radio
    cutoff = radii[i] * phys.VDW_RANGE_FACTOR
    cutoff_sq = cutoff * cutoff
    
    force_acc_xy = ti.Vector([0.0, 0.0])
    force_acc_z = 0.0
    
    for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
        nx, ny = gx + ox, gy + oy
        if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
            num_neighbors = ti.min(32, grid_count[nx, ny])
            for k in range(num_neighbors):
                j = grid_pids[nx, ny, k]
                
                if i != j:
                    # Distancia 3D
                    diff_xy = pos[j] - pos[i]  # Vector hacia el vecino (XY)
                    diff_z = pos_z[j] - pos_z[i]  # Componente Z
                    dist_sq_3d = diff_xy.x*diff_xy.x + diff_xy.y*diff_xy.y + diff_z*diff_z
                    
                    sum_radii = radii[i] + radii[j]
                    min_dist_sq = sum_radii * sum_radii
                    
                    if min_dist_sq < dist_sq_3d < cutoff_sq:
                        dist_3d = ti.sqrt(dist_sq_3d)
                        
                        # Factor de fuerza: 1.0 en superficie, 0.0 en cutoff
                        strength = 1.0 - (dist_3d - sum_radii) / (cutoff - sum_radii)
                        
                        if strength > 0:
                            # Fuerza direccional 3D hacia J
                            force_acc_xy += (diff_xy / dist_3d) * strength * phys.VDW_K
                            force_acc_z += (diff_z / dist_3d) * strength * phys.VDW_K
    
    # CRÍTICO: Limitar fuerzas 3D para evitar explosión
    f3d_norm = ti.sqrt(force_acc_xy.x*force_acc_xy.x + force_acc_xy.y*force_acc_xy.y + force_acc_z*force_acc_z)
    max_vdw_force = 1.0
    if f3d_norm > max_vdw_force:
        scale = max_vdw_force / f3d_norm
        force_acc_xy = force_acc_xy * scale
        force_acc_z = force_acc_z * scale
    
    # Aplicar fuerza 3D (limitada)
    vel[i] += force_acc_xy * 0.1
    vel_z[i] += force_acc_z * 0.1
    
@ti.kernel
def resolve_constraints_grid():
    resolve_constraints_grid_func()


# ===================================================================
# UTILIDADES
# ===================================================================

@ti.kernel
def shake_simulation():
    """Añade caos masivo para desatascar partículas."""
    for i in range(n_particles[None]):
        vel[i] += ti.Vector([ti.random()-0.5, ti.random()-0.5]) * 20.0

@ti.func
def physics_post_step_i(i: ti.i32, t_total: ti.f32, run_advanced: ti.i32):
    """Lógica de post-paso para una partícula (CON FUSIÓN TOTAL)."""
    if is_active[i] != 0:
        # Solo si está en el bounds de simulación
        if (sim_bounds[0] < pos[i].x < sim_bounds[2] and 
            sim_bounds[1] < pos[i].y < sim_bounds[3]):
            
            # 1. PBD Step (Derivar velocidad)
            vel[i] = (pos[i] - pos_old[i]) * VELOCITY_DERIVATION
            
            # 2. Advanced Rules (FUSIONADOS AQUÍ)
            if run_advanced != 0:
                apply_brownian_i(i, t_total)
                apply_evolution_i(i)
                apply_electrostatic_forces_i(i)
                apply_van_der_waals_i(i)
                apply_hydrophobic_attraction_i(i) # <--- EXTRA COHESIÓN PARA ORGANICOS
                apply_tractor_beam_i(i)            # <--- FACTORY: TRACTOR BEAM
                apply_metabolism_i(i)
