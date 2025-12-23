"""
Constantes de Sistema - LifeSimulator
======================================
Archivo centralizado para todas las constantes de escala,
buffers y límites del sistema. Cualquier constante que defina
tamaños máximos o parámetros de escala debe estar aquí.

Uso:
    from src.config.system_constants import MAX_PARTICLES, WORLD_SIZE
"""

# ===================================================================
# ESCALA MAESTRA (SINGLE SOURCE OF TRUTH)
# ===================================================================
# Factor de escala maestro que afecta TODO el sistema
# Cambiar este valor escala proporcionalmente: visuales, física, química
MASTER_SCALE = 3.0

# Alias para compatibilidad (usar MASTER_SCALE en código nuevo)
VISUAL_SCALE = MASTER_SCALE

# ===================================================================
# ESCALA DEL MUNDO
# ===================================================================
# Tamaño del mundo de simulación en unidades
# Cambiar este valor afecta TODO el sistema de coordenadas
WORLD_SIZE = 15000

# Margen de simulación fuera de cámara (Chemical Culling)
# Rango extra donde los átomos se "despiertan" antes de ser visibles
CULLING_MARGIN = 1500.0

# Zoom inicial de la cámara
INITIAL_ZOOM = 4.15


# ===================================================================
# LÍMITES DE PARTÍCULAS
# ===================================================================
# Máximo absoluto de partículas en el sistema
# ADVERTENCIA: Cambiar esto requiere reiniciar Taichi
MAX_PARTICLES = 10000

# Número inicial de partículas al crear el mundo
DEFAULT_PARTICLES = 5000

# Máximo de enlaces por átomo (valencia máxima)
# NOTA: También definido en physics_constants.py para compatibilidad
MAX_VALENCE = 8

# Buffer de enlaces para rendering
MAX_BONDS = MAX_PARTICLES * 4


# ===================================================================
# GRID ESPACIAL
# ===================================================================
# Tamaño de cada celda del grid de colisiones
GRID_CELL_SIZE = 1000.0 # Wide cell for stress test cluster

# Resolución del grid (calculada automáticamente)
GRID_RES = int(WORLD_SIZE * 1.5 / GRID_CELL_SIZE) + 1

# Máximo de partículas por celda del grid
MAX_PER_CELL = 5000 # Full capacity for stress test cluster


# ===================================================================
# LÍMITES DE VELOCIDAD
# ===================================================================
# Velocidad máxima base (se escala con VISUAL_SCALE)
BASE_MAX_SPEED = 8.0
MAX_SPEED = BASE_MAX_SPEED * VISUAL_SCALE

# Fuerza máxima aplicable
BASE_MAX_FORCE = 20.0
MAX_FORCE = BASE_MAX_FORCE * VISUAL_SCALE


# ===================================================================
# TAMAÑOS VISUALES BASE (antes de escalar)
# ===================================================================
# Tamaño base de átomos
BASE_ATOM_SIZE = 10.0
ATOM_SIZE_GL = BASE_ATOM_SIZE * VISUAL_SCALE

# Ancho de enlaces
BASE_BOND_WIDTH = 1.5
BOND_WIDTH = BASE_BOND_WIDTH * VISUAL_SCALE

# Distancia de equilibrio base para enlaces
BASE_DIST_EQ = 35.0
DIST_EQUILIBRIO = BASE_DIST_EQ * VISUAL_SCALE


# ===================================================================
# RANGOS DE ENLACE
# ===================================================================
# Mínimo para permitir enlace (después de colisión)
BASE_ENLACE_MIN = 2.0
RANGO_ENLACE_MIN = BASE_ENLACE_MIN * VISUAL_SCALE

# Máximo para detectar vecinos enlazables
BASE_ENLACE_MAX = 70.0
RANGO_ENLACE_MAX = BASE_ENLACE_MAX * VISUAL_SCALE

# Distancia de rotura de enlace
DIST_ROTURA = RANGO_ENLACE_MAX * 1.5


# ===================================================================
# INTERACCIÓN (Click/Poderes)
# ===================================================================
# Fuerza del click
BASE_CLICK_FORCE = 50.0
CLICK_FORCE = BASE_CLICK_FORCE * VISUAL_SCALE

# Radio de efecto del click
BASE_CLICK_RADIUS = 30.0
CLICK_RADIUS = BASE_CLICK_RADIUS * VISUAL_SCALE


# ===================================================================
# DISTRIBUCIÓN DE ÁTOMOS (CHONPS)
# ===================================================================
# Probabilidades de spawn por tipo de átomo
# H (40%), O (20%), C (20%), N (10%), P (5%), S (5%)
ATOM_SPAWN_PROBS = [0.4, 0.2, 0.2, 0.1, 0.05, 0.05]


# ===================================================================
# HELPERS
# ===================================================================
def recalculate_scaled_values(new_scale: float):
    """
    Recalcula todos los valores escalados con un nuevo factor.
    Útil para cambios dinámicos de escala.
    """
    global VISUAL_SCALE, ATOM_SIZE_GL, BOND_WIDTH, DIST_EQUILIBRIO
    global RANGO_ENLACE_MIN, RANGO_ENLACE_MAX, DIST_ROTURA
    global CLICK_FORCE, CLICK_RADIUS, MAX_SPEED, MAX_FORCE
    
    VISUAL_SCALE = new_scale
    ATOM_SIZE_GL = BASE_ATOM_SIZE * VISUAL_SCALE
    BOND_WIDTH = BASE_BOND_WIDTH * VISUAL_SCALE
    DIST_EQUILIBRIO = BASE_DIST_EQ * VISUAL_SCALE
    RANGO_ENLACE_MIN = BASE_ENLACE_MIN * VISUAL_SCALE
    RANGO_ENLACE_MAX = BASE_ENLACE_MAX * VISUAL_SCALE
    DIST_ROTURA = RANGO_ENLACE_MAX * 1.5
    CLICK_FORCE = BASE_CLICK_FORCE * VISUAL_SCALE
    CLICK_RADIUS = BASE_CLICK_RADIUS * VISUAL_SCALE
    MAX_SPEED = BASE_MAX_SPEED * VISUAL_SCALE
    MAX_FORCE = BASE_MAX_FORCE * VISUAL_SCALE
