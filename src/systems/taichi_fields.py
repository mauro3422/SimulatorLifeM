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
from src.config.system_constants import (
    MAX_PARTICLES, MAX_VALENCE, MAX_BONDS,
    GRID_CELL_SIZE, GRID_RES, MAX_PER_CELL,
    WORLD_SIZE
)

# ===================================================================
# INICIALIZACIÓN TAICHI (Condicional para evitar duplicación)
# ===================================================================
def _init_taichi_if_needed():
    """Initialize Taichi only if not already initialized."""
    try:
        # Check if already initialized by trying to access the arch
        ti.lang.impl.current_cfg()
        # If we get here, Taichi is already initialized
    except:
        # Not initialized, do it now
        try:
            ti.init(arch=ti.vulkan, offline_cache=True)
            print("[GPU] Modo Vulkan Activo (Cache Activo)")
        except:
            ti.init(arch=ti.opengl)
            print("[GPU] Modo OpenGL Activo")

_init_taichi_if_needed()


# ===================================================================
# CONSTANTES (desde módulos centralizados)
# ===================================================================
SOLVER_ITERATIONS = phys.SOLVER_ITERATIONS

# Física (desde physics_constants.py)
BROWNIAN_K = phys.BROWNIAN_K
BROWNIAN_BASE_TEMP = phys.BROWNIAN_BASE_TEMP
COULOMB_K = phys.COULOMB_K
REPULSION_MIN_DIST = phys.REPULSION_MIN_DIST
REPULSION_MAX_DIST = phys.REPULSION_MAX_DIST
ELECTRONEG_AVG = phys.ELECTRONEG_AVERAGE
NUM_ELEMENTS = len(cfg.TIPOS_NOMBRES)

# Efectos evolutivos (desde physics_constants.py)
MUTATION_PROBABILITY = phys.MUTATION_PROBABILITY
TUNNEL_VELOCITY_THRESHOLD = phys.TUNNEL_VELOCITY_THRESHOLD
TUNNEL_PROBABILITY = phys.TUNNEL_PROBABILITY
TUNNEL_JUMP_DISTANCE = phys.TUNNEL_JUMP_DISTANCE

# Factores de fuerza (desde physics_constants.py)
BOND_FORCE_FACTOR = phys.BOND_FORCE_FACTOR
COULOMB_FORCE_FACTOR = phys.COULOMB_FORCE_FACTOR

# PBD Constants (desde physics_constants.py)
VELOCITY_DERIVATION = phys.VELOCITY_DERIVATION
COLLISION_CORRECTION = phys.COLLISION_CORRECTION

# VSEPR Geometry Constants (desde chemistry_constants.py)
from src.systems import chemistry_constants as chem
ANGULAR_SPRING_K = chem.ANGULAR_SPRING_K
ANGULAR_DAMPING = chem.ANGULAR_DAMPING
ANGULAR_FORCE_FACTOR = chem.ANGULAR_FORCE_FACTOR
ANGLE_TOLERANCE_RAD = chem.ANGLE_TOLERANCE * chem.DEG_TO_RAD

# Torsiones (Diedros)
DIHEDRAL_K = phys.DIHEDRAL_K
DIHEDRAL_DAMPING = phys.DIHEDRAL_DAMPING

# Ángulos ideales VSEPR por número de enlaces (en radianes para GPU)
import math
VSEPR_ANGLES_RAD = ti.field(dtype=ti.f32, shape=9)  # índice = num_enlaces

# ===================================================================
# CAMPOS TAICHI - PARTÍCULAS (Sistema 2.5D: física en X,Y,Z)
# ===================================================================
pos = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)      # Posición X,Y
vel = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)      # Velocidad X,Y
pos_old = ti.Vector.field(2, dtype=ti.f32, shape=MAX_PARTICLES)
radii = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
is_active = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
atom_types = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

# 2.5D: Coordenada Z para geometría molecular 3D real
pos_z = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)   # Posición Z (profundidad)
vel_z = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)   # Velocidad Z (NUEVO: física 2.5D)
partial_charge = ti.field(dtype=ti.f32, shape=MAX_PARTICLES) # Carga parcial dinámica (UFF)

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
# CAMPOS TAICHI - MOLECULE ID PROPAGATION (Event-Driven)
# ===================================================================
# Cada partícula tiene un molecule_id que indica a qué molécula pertenece
# Inicialmente molecule_id[i] = i (cada átomo es su propia molécula)
molecule_id = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
# Siguiente ID disponible para nuevas moléculas (al romper)
next_molecule_id = ti.field(dtype=ti.i32, shape=())
# Flag para indicar qué partículas necesitan propagar su ID
needs_propagate = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

# ===================================================================
# CAMPOS TAICHI - GRID ESPACIAL
# ===================================================================
grid_count = ti.field(dtype=ti.i32, shape=(GRID_RES, GRID_RES))
grid_pids = ti.field(dtype=ti.i32, shape=(GRID_RES, GRID_RES, MAX_PER_CELL))
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
n_simulated_physics = ti.field(dtype=ti.i32, shape=()) # Counter for actual physics computations
total_bonds_broken_dist = ti.field(dtype=ti.i32, shape=()) # Counter: Breakage by distance

# ===================================================================
# CAMPOS TAICHI - JUGADOR
# ===================================================================
player_idx = ti.field(dtype=ti.i32, shape=())  # Índice del átomo del jugador
player_idx[None] = 0  # Por defecto, jugador es índice 0

# ===================================================================
# CAMPOS TAICHI - PARÁMETROS DE FÍSICA
# ===================================================================
gravity = ti.field(dtype=ti.f32, shape=())
friction = ti.field(dtype=ti.f32, shape=())
temperature = ti.field(dtype=ti.f32, shape=())
max_speed = ti.field(dtype=ti.f32, shape=())
world_width = ti.field(dtype=ti.f32, shape=())
world_height = ti.field(dtype=ti.f32, shape=())
charge_factor = ti.field(dtype=ti.f32, shape=()) # Factor global de carga eléctrica

# Parámetros de enlaces
dist_equilibrio = ti.field(dtype=ti.f32, shape=())
spring_k = ti.field(dtype=ti.f32, shape=())
damping = ti.field(dtype=ti.f32, shape=())
rango_enlace_min = ti.field(dtype=ti.f32, shape=())
rango_enlace_max = ti.field(dtype=ti.f32, shape=())
dist_rotura = ti.field(dtype=ti.f32, shape=())
max_fuerza = ti.field(dtype=ti.f32, shape=())

# Medio (Solvatación)
medium_type = ti.field(dtype=ti.i32, shape=())
medium_viscosity = ti.field(dtype=ti.f32, shape=())
medium_polarity = ti.field(dtype=ti.f32, shape=())

# Interacción (click/poderes)
click_force = ti.field(dtype=ti.f32, shape=())
click_radius = ti.field(dtype=ti.f32, shape=())

# DEBUG: Bond formation counters
debug_particles_checked = ti.field(dtype=ti.i32, shape=())
debug_neighbors_found = ti.field(dtype=ti.i32, shape=())
debug_distance_passed = ti.field(dtype=ti.i32, shape=())
debug_prob_passed = ti.field(dtype=ti.i32, shape=())


# ===================================================================
# CAMPOS TAICHI - DATOS ATÓMICOS DINÁMICOS
# ===================================================================
ELECTRONEG = ti.field(dtype=ti.f32, shape=NUM_ELEMENTS)
MASAS_ATOMICAS = ti.field(dtype=ti.f32, shape=NUM_ELEMENTS)
VALENCIAS_MAX = ti.field(dtype=ti.i32, shape=NUM_ELEMENTS)  # Regla del octeto
VALENCIA_ELECTRONES = ti.field(dtype=ti.i32, shape=NUM_ELEMENTS)
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
    
    # 3. Valencias y Electrones
    VALENCIAS_MAX.from_numpy(cfg.VALENCIAS.astype(np.int32))
    VALENCIA_ELECTRONES.from_numpy(cfg.VALENCIA_ELECTRONS.astype(np.int32))
    
    # 4. Afinidades
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
