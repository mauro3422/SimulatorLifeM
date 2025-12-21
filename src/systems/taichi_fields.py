"""
Taichi Fields - Definiciones de Campos GPU
===========================================
Centraliza todos los campos Taichi para evitar duplicación
y permitir importación limpia desde otros módulos.
"""
import taichi as ti
import numpy as np
import src.config as cfg
from src.systems import physics_constants as phys

# ===================================================================
# INICIALIZACIÓN TAICHI
# ===================================================================
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

# ===================================================================
# CONSTANTES
# ===================================================================
MAX_PARTICLES = 10000
SOLVER_ITERATIONS = phys.SOLVER_ITERATIONS
MAX_VALENCE = 8
MAX_BONDS = MAX_PARTICLES * 4

# Grid Espacial
GRID_CELL_SIZE = 60.0
GRID_RES = int(cfg.sim_config.WORLD_SIZE * 1.5 / GRID_CELL_SIZE) + 1

# Física (desde physics_constants.py)
BROWNIAN_K = phys.BROWNIAN_K
BROWNIAN_BASE_TEMP = phys.BROWNIAN_BASE_TEMP
COULOMB_K = phys.COULOMB_K
REPULSION_MIN_DIST = phys.REPULSION_MIN_DIST
REPULSION_MAX_DIST = phys.REPULSION_MAX_DIST
ELECTRONEG_AVG = phys.ELECTRONEG_AVERAGE
NUM_ELEMENTS = len(cfg.TIPOS_NOMBRES)

# ===================================================================
# CAMPOS TAICHI - PARTÍCULAS
# ===================================================================
pos = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
vel = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
pos_old = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
radii = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
is_active = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
atom_types = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

# Rendering (normalizadas 0-1)
pos_normalized = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
colors = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
radii_normalized = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)

# ===================================================================
# CAMPOS TAICHI - QUÍMICA Y ENLACES
# ===================================================================
manos_libres = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
enlaces_idx = ti.field(dtype=ti.i32, shape=(MAX_PARTICLES, MAX_VALENCE))
enlaces_idx.fill(-1)
num_enlaces = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
prob_enlace_base = ti.field(dtype=ti.f32, shape=())

# Líneas de enlaces para render
bond_lines = ti.Vector.field(2, dtype=ti.f32, shape=(MAX_BONDS, 2))
n_bonds_to_draw = ti.field(dtype=ti.i32, shape=())

# ===================================================================
# CAMPOS TAICHI - GRID ESPACIAL
# ===================================================================
grid_count = ti.field(dtype=ti.i32, shape=(GRID_RES, GRID_RES))
grid_pids = ti.field(dtype=ti.i32, shape=(GRID_RES, GRID_RES, 32))
sim_bounds = ti.field(dtype=ti.f32, shape=4)  # [min_x, min_y, max_x, max_y]

# Buffer de partículas visibles (optimización O(visible) vs O(N))
visible_indices = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
n_visible = ti.field(dtype=ti.i32, shape=())

# ===================================================================
# CAMPOS TAICHI - CONTADORES
# ===================================================================
n_particles = ti.field(dtype=ti.i32, shape=())
active_particles_count = ti.field(dtype=ti.i32, shape=())
total_bonds_count = ti.field(dtype=ti.i32, shape=())
total_mutations = ti.field(dtype=ti.i32, shape=())
total_tunnels = ti.field(dtype=ti.i32, shape=())

# ===================================================================
# CAMPOS TAICHI - PARÁMETROS DE FÍSICA
# ===================================================================
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

# Interacción (click/poderes)
click_force = ti.field(dtype=ti.f32, shape=())
click_radius = ti.field(dtype=ti.f32, shape=())

# ===================================================================
# CAMPOS TAICHI - DATOS ATÓMICOS DINÁMICOS
# ===================================================================
ELECTRONEG = ti.field(dtype=ti.f32, shape=NUM_ELEMENTS)
MASAS_ATOMICAS = ti.field(dtype=ti.f32, shape=NUM_ELEMENTS)
AFINIDAD_MATRIX = ti.field(dtype=ti.f32, shape=(NUM_ELEMENTS, NUM_ELEMENTS))


# ===================================================================
# INICIALIZACIÓN DE DATOS ATÓMICOS
# ===================================================================
def sync_atomic_data():
    """Sincroniza datos de JSON (cfg) con campos Taichi."""
    # 1. Electronegatividades
    ELECTRONEG.from_numpy(cfg.ELECTRONEG_DATA.astype(np.float32))
    
    # 2. Masas
    MASAS_ATOMICAS.from_numpy(cfg.MASAS.astype(np.float32))
    
    # 3. Matriz de afinidad
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
    print(f"[GPU] Sincronizados {NUM_ELEMENTS} elementos químicos.")


# Inicializar al importar
sync_atomic_data()
