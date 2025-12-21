"""
GPU-Accelerated Simulation Engine (Physics + Chemistry)
========================================================
Todo en GPU para eliminar overhead de sincronización.
"""
import taichi as ti
import numpy as np
import src.config as cfg
from src.systems import physics_constants as phys

# Inicializar Taichi (Prioridad Vulkan - Restaurado por rendimiento)
try:
    ti.init(arch=ti.vulkan, offline_cache=True)
    print("[GPU] Modo Vulkan Activo (Alto Rendimiento)")
except:
    try:
        ti.init(arch=ti.opengl)
        print("[GPU] Fallback a OpenGL")
    except:
        ti.init(arch=ti.cpu)
        print("[GPU] Fallback a CPU")

# Constantes (Desde Config Central)
MAX_PARTICLES = 10000 # Buffer máximo de seguridad
SOLVER_ITERATIONS = phys.SOLVER_ITERATIONS


# Grid Espacial optimizado para WORLD_SIZE centralizado
GRID_CELL_SIZE = 60.0
GRID_RES = int(cfg.sim_config.WORLD_SIZE * 1.5 / GRID_CELL_SIZE) + 1
grid_count = ti.field(dtype=ti.i32, shape=(GRID_RES, GRID_RES))
grid_pids = ti.field(dtype=ti.i32, shape=(GRID_RES, GRID_RES, 32)) # Max 32 por celda
sim_bounds = ti.field(dtype=ti.f32, shape=4) # [min_x, min_y, max_x, max_y]
active_particles_count = ti.field(dtype=ti.i32, shape=())
total_bonds_count = ti.field(dtype=ti.i32, shape=()) # Atomic counter

# [OPTIMIZACIÓN] Buffer compactado de partículas visibles
# En lugar de iterar 6000, iteramos solo las visibles (O(active) vs O(N))
visible_indices = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
n_visible = ti.field(dtype=ti.i32, shape=())

# --- CAMPOS TAICHI (Datos en GPU) ---
pos = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
vel = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
pos_old = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
radii = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
is_active = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
atom_types = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

# Para GGUI rendering (posiciones normalizadas 0-1)
pos_normalized = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
colors = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)  # RGB
radii_normalized = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)

# Para dibujar enlaces (líneas)
MAX_BONDS = MAX_PARTICLES * 4  # Max enlaces posibles
bond_lines = ti.Vector.field(2, dtype=ti.f32, shape=(MAX_BONDS, 2))  
n_bonds_to_draw = ti.field(dtype=ti.i32, shape=())

# Química y Parámetros Dinámicos
MAX_VALENCE = 8
manos_libres = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
enlaces_idx = ti.field(dtype=ti.i32, shape=(MAX_PARTICLES, MAX_VALENCE)) # IDs de vecinos enlazados
enlaces_idx.fill(-1)
num_enlaces = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
prob_enlace_base = ti.field(dtype=ti.f32, shape=())

# Contadores de Eventos "Evolutivos" (Restaurados)
total_mutations = ti.field(dtype=ti.i32, shape=())   # Evolución/Transmutación
total_tunnels = ti.field(dtype=ti.i32, shape=())      # Teletransportación/Efecto Túnel

# Campos de Interacción (Click/Powers)
click_force = ti.field(dtype=ti.f32, shape=())
click_radius = ti.field(dtype=ti.f32, shape=())

# Parámetros
n_particles = ti.field(dtype=ti.i32, shape=())
gravity = ti.field(dtype=ti.f32, shape=())
friction = ti.field(dtype=ti.f32, shape=())
temperature = ti.field(dtype=ti.f32, shape=())
max_speed = ti.field(dtype=ti.f32, shape=())
world_width = ti.field(dtype=ti.f32, shape=())
world_height = ti.field(dtype=ti.f32, shape=())

# Parámetros de enlaces
dist_equilibrio = ti.field(dtype=ti.f32, shape=())
spring_k = ti.field(dtype=ti.f32, shape=())
damping = ti.field(dtype=ti.f32, shape=())
rango_enlace_min = ti.field(dtype=ti.f32, shape=())
rango_enlace_max = ti.field(dtype=ti.f32, shape=())
dist_rotura = ti.field(dtype=ti.f32, shape=())
max_fuerza = ti.field(dtype=ti.f32, shape=())

# --- FÍSICA REALISTA (Desde physics_constants.py) ---
# Movimiento Browniano
BROWNIAN_K = phys.BROWNIAN_K
BROWNIAN_BASE_TEMP = phys.BROWNIAN_BASE_TEMP

# Repulsión de Coulomb
COULOMB_K = phys.COULOMB_K
REPULSION_MIN_DIST = phys.REPULSION_MIN_DIST
REPULSION_MAX_DIST = phys.REPULSION_MAX_DIST

# Electronegatividades dinámicas
ELECTRONEG = ti.field(dtype=ti.f32, shape=len(cfg.TIPOS_NOMBRES))
ELECTRONEG_AVG = phys.ELECTRONEG_AVERAGE

# Afinidad Química (matriz dinámica NxN)
NUM_ELEMENTS = len(cfg.TIPOS_NOMBRES)
AFINIDAD_MATRIX = ti.field(dtype=ti.f32, shape=(NUM_ELEMENTS, NUM_ELEMENTS))

# Masas atómicas dinámicas
MASAS_ATOMICAS = ti.field(dtype=ti.f32, shape=NUM_ELEMENTS)

# Inicializar constantes
@ti.kernel
def init_physics_constants():
    """Inicializa las constantes de física realista (Vacío, se llena vía Python)."""
    pass

def sync_atomic_data():
    """Sincroniza los datos cargados desde JSON (cfg) con los campos de Taichi."""
    # 1. Electronegatividades
    ELECTRONEG.from_numpy(cfg.ELECTRONEG_DATA.astype(np.float32))
    
    # 2. Masas
    MASAS_ATOMICAS.from_numpy(cfg.MASAS.astype(np.float32))
    
    # 3. Matriz de Afinidad (Complejo: Mapeo de Nombres a Índices)
    afinidad_np = np.zeros((NUM_ELEMENTS, NUM_ELEMENTS), dtype=np.float32)
    name_to_idx = {name: i for i, name in enumerate(cfg.TIPOS_NOMBRES)}
    
    for i, name_i in enumerate(cfg.TIPOS_NOMBRES):
        atom_info = cfg.ATOMS[name_i]
        affid_dict = atom_info.get("affinities", {})
        for name_j, strength in affid_dict.items():
            if name_j in name_to_idx:
                j = name_to_idx[name_j]
                afinidad_np[i, j] = strength
                
    AFINIDAD_MATRIX.from_numpy(afinidad_np)
    print(f"[GPU] Sincronizados {NUM_ELEMENTS} elementos químicos desde el sistema Data-Driven.")

# Llamar al inicio
init_physics_constants()
sync_atomic_data()

# --- KERNELS OPTIMIZADOS (GRID) ---

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
