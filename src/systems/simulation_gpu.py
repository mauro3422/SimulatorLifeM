"""
GPU-Accelerated Simulation Engine (Physics + Chemistry)
========================================================
Kernels de física y química ejecutados en GPU via Taichi.
Los campos están definidos en taichi_fields.py
"""
import taichi as ti
import numpy as np
import src.config as cfg
from src.systems import physics_constants as phys

# Importar todos los campos desde el módulo centralizado
from src.systems.taichi_fields import (
    # Constantes
    MAX_PARTICLES, SOLVER_ITERATIONS, MAX_VALENCE, MAX_BONDS,
    GRID_CELL_SIZE, GRID_RES,
    BROWNIAN_K, BROWNIAN_BASE_TEMP, COULOMB_K, 
    REPULSION_MIN_DIST, REPULSION_MAX_DIST, ELECTRONEG_AVG, NUM_ELEMENTS,
    
    # Campos de partículas
    pos, vel, pos_old, radii, is_active, atom_types,
    pos_normalized, colors, radii_normalized,
    
    # Campos de química
    manos_libres, enlaces_idx, num_enlaces, prob_enlace_base,
    bond_lines, n_bonds_to_draw,
    
    # Grid espacial
    grid_count, grid_pids, sim_bounds,
    visible_indices, n_visible,
    
    # Contadores
    n_particles, active_particles_count, total_bonds_count,
    total_mutations, total_tunnels,
    
    # Parámetros de física
    gravity, friction, temperature, max_speed,
    world_width, world_height,
    dist_equilibrio, spring_k, damping,
    rango_enlace_min, rango_enlace_max, dist_rotura, max_fuerza,
    click_force, click_radius,
    
    # Datos atómicos
    ELECTRONEG, MASAS_ATOMICAS, AFINIDAD_MATRIX
)

# ===================================================================
# KERNELS DE FÍSICA Y QUÍMICA
# ===================================================================

@ti.kernel
def update_grid():
    """Actualiza grid espacial GLOBAL Y filtra visibles para render."""
    grid_count.fill(0)
    n_visible[None] = 0
    
    min_x, min_y = sim_bounds[0], sim_bounds[1]
    max_x, max_y = sim_bounds[2], sim_bounds[3]
    
    for i in range(n_particles[None]):
        if is_active[i]:
            p = pos[i]
            
            # 1. Agregar al grid espacial GLOBAL (Independiente de la vista)
            gx = int(p.x / GRID_CELL_SIZE)
            gy = int(p.y / GRID_CELL_SIZE)
            if 0 <= gx < GRID_RES and 0 <= gy < GRID_RES:
                idx = ti.atomic_add(grid_count[gx, gy], 1)
                if idx < 32:
                    grid_pids[gx, gy, idx] = i
            
            # 2. CULLING: Agregar a lista de visibles solo si está en pantalla
            if (min_x < p.x < max_x and min_y < p.y < max_y):
                vis_idx = ti.atomic_add(n_visible[None], 1)
                if vis_idx < MAX_PARTICLES:
                    visible_indices[vis_idx] = i

@ti.kernel
def check_bonding_gpu():
    """Formar enlaces - SOLO partículas visibles (O(active))."""
    n_vis = n_visible[None]
    
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
                                            # ti.atomic_add(total_bonds_count[None], 1) # Eliminado por performance/estabilidad
                                        else:
                                            ti.atomic_sub(num_enlaces[i], 1)
                                            ti.atomic_sub(num_enlaces[j], 1)

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
                        enlaces_idx[i, b] = -1
                        for b_j in range(num_enlaces[j]):
                            if enlaces_idx[j, b_j] == i:
                                enlaces_idx[j, b_j] = -1
                        
                        ti.atomic_add(manos_libres[i], 1.0)
                        ti.atomic_add(manos_libres[j], 1.0)
                        ti.atomic_sub(total_bonds_count[None], 1)
                    else:
                        direction = diff / dist
                        f_spring = direction * (dist - dist_equilibrio[None]) * spring_k[None]
                        v_rel = vel[i] - vel[j]
                        f_damp = direction * v_rel.dot(direction) * damping[None]
                        force += f_spring + f_damp
            
            f_norm = force.norm()
            if f_norm > max_fuerza[None]:
                force = force * (max_fuerza[None] / f_norm)
            vel[i] -= force * 0.3

@ti.kernel
def apply_brownian_motion_gpu():
    """Aplica movimiento Browniano (agitación térmica) GLOBAL."""
    T_total = BROWNIAN_BASE_TEMP + temperature[None]
    for i in range(n_particles[None]):
        if is_active[i]:
            atom_type = atom_types[i]
            mass = MASAS_ATOMICAS[atom_type]
            
            # Velocidad RMS = sqrt(k * T / m)
            v_rms = ti.sqrt(BROWNIAN_K * T_total / mass)
            
            # Dirección aleatoria
            dx = ti.random() - 0.5
            dy = ti.random() - 0.5
            length = ti.sqrt(dx*dx + dy*dy) + 1e-8
            dx /= length
            dy /= length
            
            # Magnitud aleatoria
            magnitude = v_rms * ti.random()
            
            vel[i] += ti.Vector([dx * magnitude, dy * magnitude])

@ti.kernel
def apply_coulomb_repulsion_gpu():
    """Repulsión de Coulomb GLOBAL."""
    charge_factor = 0.2
    for i in range(n_particles[None]):
        if is_active[i]:
            # Carga parcial basada en electronegatividad
            type_i = atom_types[i]
            q_i = (ELECTRONEG[type_i] - ELECTRONEG_AVG) * charge_factor
            mass_i = MASAS_ATOMICAS[type_i]
            
            # Buscar vecinos cercanos en el grid
            gx = int(pos[i][0] / GRID_CELL_SIZE)
            gy = int(pos[i][1] / GRID_CELL_SIZE)
            
            total_force = ti.Vector([0.0, 0.0])
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neighbors = ti.min(32, grid_count[nx, ny])
                    for k in range(num_neighbors):
                        j = grid_pids[nx, ny, k]
                        if i != j:
                            diff = pos[i] - pos[j]
                            dist = diff.norm()
                            
                            if REPULSION_MIN_DIST < dist < REPULSION_MAX_DIST:
                                type_j = atom_types[j]
                                q_j = (ELECTRONEG[type_j] - ELECTRONEG_AVG) * charge_factor
                                
                                # Solo repeler si ambos tienen misma carga (mismo signo)
                                if q_i * q_j > 0:
                                    # Ley de Coulomb: F = k * |q1 * q2| / r²
                                    dist_sq = ti.max(dist * dist, REPULSION_MIN_DIST * REPULSION_MIN_DIST)
                                    force_mag = COULOMB_K * ti.abs(q_i * q_j) / dist_sq
                                    
                                    direction = diff / dist
                                    total_force += direction * force_mag
            
            # Aplicar fuerza dividida por masa (F = ma → a = F/m)
            vel[i] += total_force / mass_i * 0.1

@ti.kernel
def shake_simulation():
    """Añade caos masivo para desatascar partículas."""
    for i in range(n_particles[None]):
        vel[i] += ti.Vector([ti.random()-0.5, ti.random()-0.5]) * 20.0

@ti.kernel
def physics_pre_step():
    """Fuerzas iniciales y predicción de posición - GLOBAL."""
    for i in range(n_particles[None]):
        if is_active[i]:
            vel[i].y += gravity[None] * 5.0
            vel[i] *= friction[None]
            
            if temperature[None] > 0:
                vel[i] += ti.Vector([ti.random()-0.5, ti.random()-0.5]) * temperature[None] * 20.0

            speed = vel[i].norm()
            if speed > max_speed[None]:
                vel[i] = vel[i] / speed * max_speed[None]
            
            pos_old[i] = pos[i]
            pos[i] += vel[i]

@ti.kernel
def resolve_constraints_grid():
    """Resolver colisiones y paredes - GLOBAL (via grid)."""
    for i in range(n_particles[None]):
        if is_active[i]:
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
                            diff = pos[i] - pos[j]
                            dist = diff.norm()
                            sum_radii = radii[i] + radii[j]
                            if 0.001 < dist < sum_radii:
                                overlap = sum_radii - dist
                                correction = (diff / dist) * overlap * 0.7
                                pos[i] += correction * 0.5
                                pos[j] -= correction * 0.5

@ti.kernel
def physics_post_step():
    """Derivar velocidad final - GLOBAL."""
    for i in range(n_particles[None]):
        if is_active[i]:
            vel[i] = (pos[i] - pos_old[i]) * 0.9

@ti.kernel
def count_active_particles_gpu():
    """Cuenta partículas activas (One-off per frame)."""
    active_particles_count[None] = 0
    min_x, min_y = sim_bounds[0], sim_bounds[1]
    max_x, max_y = sim_bounds[2], sim_bounds[3]
    
    for i in range(n_particles[None]):
         if is_active[i]:
             if (min_x < pos[i].x < max_x and min_y < pos[i].y < max_y):
                 ti.atomic_add(active_particles_count[None], 1)

def simulation_step_gpu():
    """Ejecuta un único paso de simulación completo en GPU."""
    # Actualizar grid espacial
    update_grid()
    
    # Física pre-step (gravedad, fricción, predicción)
    physics_pre_step()
    
    # Resolver restricciones (Iterative Solver)
    for _solver in range(SOLVER_ITERATIONS):
        resolve_constraints_grid()
        
    physics_post_step()
    
    # Química (O(active) usando el mismo grid)
    check_bonding_gpu()
    apply_bond_forces_gpu()
    
    # Física realista (Brownian + Coulomb)
    apply_brownian_motion_gpu()
    apply_coulomb_repulsion_gpu()
    
    # Efectos evolutivos (Mutación + Túnel) - Restaurados
    apply_evolutionary_effects_gpu()

@ti.kernel
def apply_force_pulse(center_x: ti.f32, center_y: ti.f32, power_mult: ti.f32):
    """Aplica una onda de choque expansiva en una coordenada (O(N))."""
    center = ti.Vector([center_x, center_y])
    for i in range(n_particles[None]):
        if is_active[i]:
            diff = pos[i] - center
            dist = diff.norm()
            radio_efecto = click_radius[None] * 4.0 
            if dist < radio_efecto and dist > 0.1:
                # Fuerza inversamente proporcional para efecto de onda suave
                strength = (1.0 - dist / radio_efecto) * click_force[None] * power_mult
                vel[i] += diff.normalized() * strength

@ti.kernel
def apply_evolutionary_effects_gpu():
    """Introduce Mutaciones y Efecto Túnel (O(N))."""
    for i in range(n_particles[None]):
        if is_active[i]:
            # 1. MUTACIÓN (Evolución de tipo) - Muy rara
            if ti.random() < 0.00005: 
                new_type = ti.random(ti.i32) % NUM_ELEMENTS # Escalamiento dinámico
                atom_types[i] = new_type
                ti.atomic_add(total_mutations[None], 1)
            
            # 2. EFECTO TÚNEL (Teletransportación)
            v_norm = vel[i].norm()
            if v_norm > max_speed[None] * 0.95 and ti.random() < 0.01:
                jump_dist = 60.0 # Salto cuántico
                pos[i] += vel[i].normalized() * jump_dist
                ti.atomic_add(total_tunnels[None], 1)

def run_simulation_fast(n_steps: int):
    """
    Ejecuta N pasos de simulación con un solo update de Grid por paso (Alta Velocidad).
    """
    for _ in range(n_steps):
        simulation_step_gpu()

def sync_to_gpu(universe):
    """Sincroniza datos de CPU a GPU."""
    n = len(universe.pos)
    n_particles[None] = n
    
    # Arrays padded
    pos_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
    vel_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
    radii_np = np.zeros(MAX_PARTICLES, dtype=np.float32)
    active_np = np.zeros(MAX_PARTICLES, dtype=np.int32)
    manos_np = np.zeros(MAX_PARTICLES, dtype=np.float32)
    enlaces_np = np.zeros((MAX_PARTICLES, MAX_PARTICLES), dtype=np.int32)
    
    pos_np[:n] = universe.pos.astype(np.float32)
    vel_np[:n] = universe.vel.astype(np.float32)
    radii_np[:n] = universe.radios_asignados.astype(np.float32)
    active_np[:n] = 1
    manos_np[:n] = universe.manos_libres.astype(np.float32)
    # [IMPORTANTE] Re-inicializar enlaces en GPU cada vez que sincronizamos CPU->GPU
    enlaces_idx.fill(-1)
    num_enlaces.fill(0)
    # Si universe tiene enlaces, poblarlos (Lento pero necesario si se hereda estado)
    for i in range(n):
        count = 0
        for j in range(n):
            if universe.enlaces[i, j] and count < MAX_VALENCE:
                enlaces_idx[i, count] = j
                count += 1
        num_enlaces[i] = count
    
    pos.from_numpy(pos_np)
    vel.from_numpy(vel_np)
    radii.from_numpy(radii_np)
    is_active.from_numpy(active_np)
    manos_libres.from_numpy(manos_np)
    enlaces.from_numpy(enlaces_np)
    
    # Parámetros
    gravity[None] = universe.config.GRAVITY
    friction[None] = universe.config.FRICTION
    temperature[None] = universe.config.TEMPERATURE
    max_speed[None] = universe.config.MAX_VELOCIDAD
    world_width[None] = universe.config.WIDTH - 200
    world_height[None] = universe.config.HEIGHT
    dist_equilibrio[None] = universe.config.DIST_EQUILIBRIO
    spring_k[None] = universe.config.SPRING_K
    damping[None] = universe.config.DAMPING
    rango_enlace_min[None] = universe.config.RANGO_ENLACE_MIN
    rango_enlace_max[None] = universe.config.RANGO_ENLACE_MAX
    dist_rotura[None] = universe.config.DIST_ROTURA
    max_fuerza[None] = universe.config.MAX_FUERZA

def sync_from_gpu(universe):
    """Sincroniza datos de GPU a CPU."""
    n = len(universe.pos)
    universe.pos = pos.to_numpy()[:n]
    universe.vel = vel.to_numpy()[:n]
    universe.manos_libres = manos_libres.to_numpy()[:n]
    
    # Reconstruir matriz de enlaces para CPU (Compatibilidad)
    idx_np = enlaces_idx.to_numpy()[:n]
    num_np = num_enlaces.to_numpy()[:n]
    universe.enlaces.fill(False)
    for i in range(n):
        for k in range(num_np[i]):
            j = idx_np[i, k]
            if j >= 0:
                universe.enlaces[i, j] = True
    
    universe.pos_old = universe.pos.copy()

def sync_positions_only(universe):
    """Solo sincroniza posiciones para renderizado (rápido)."""
    n = len(universe.pos)
    universe.pos = pos.to_numpy()[:n]

def run_simulation_gpu(universe, time_scale=1, sync_full=False):
    """
    Ejecuta múltiples pasos de simulación en GPU.
    
    Args:
        universe: Universo de simulación
        time_scale: Número de pasos a ejecutar
        sync_full: Si True, sincroniza todo (lento). Si False, solo posiciones (rápido).
    """
    sync_to_gpu(universe)
    
    for _ in range(time_scale):
        simulation_step_gpu()
    
    if sync_full:
        sync_from_gpu(universe)
    else:
        # Solo sync posiciones para render (mucho más rápido)
        sync_positions_only(universe)

# Test
if __name__ == "__main__":
    print("\n=== TEST GPU SIMULATION (Physics + Chemistry) ===")
    
    n_test = 50
    n_particles[None] = n_test
    world_width[None] = 600
    world_height[None] = 500
    gravity[None] = 0.1
    friction[None] = 0.95
    max_speed[None] = 7.5
    dist_equilibrio[None] = 26
    spring_k[None] = 0.9
    damping[None] = 4.2
    rango_enlace_min[None] = 15
    rango_enlace_max[None] = 33
    dist_rotura[None] = 51
    max_fuerza[None] = 11.5
    
    # Inicializar
    pos_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:n_test, 0] = np.random.rand(n_test) * 600
    pos_np[:n_test, 1] = np.random.rand(n_test) * 500
    pos.from_numpy(pos_np)
    
    vel.from_numpy(np.zeros((MAX_PARTICLES, 2), dtype=np.float32))
    radii.from_numpy(np.ones(MAX_PARTICLES, dtype=np.float32) * 10)
    is_active.from_numpy(np.ones(MAX_PARTICLES, dtype=np.int32))
    manos_libres.from_numpy(np.ones(MAX_PARTICLES, dtype=np.float32) * 4)
    enlaces.from_numpy(np.zeros((MAX_PARTICLES, MAX_PARTICLES), dtype=np.int32))
    
    import time
    start = time.time()
    
    # Simular 200 pasos (como TIME_SCALE=200)
    for _ in range(200):
        simulation_step_gpu()
    
    elapsed = time.time() - start
    
    # Contar enlaces formados
    enlaces_np = enlaces.to_numpy()
    n_enlaces = np.sum(enlaces_np[:n_test, :n_test]) // 2
    
    print(f"200 pasos en {elapsed*1000:.1f}ms")
    print(f"FPS equivalente: {200/elapsed:.0f}")
    print(f"Enlaces formados: {n_enlaces}")
    print("✓ GPU Simulation funcionando!")
