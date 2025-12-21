import numpy as np

# --- EL PANEL DE CONTROL (Configuración Dinámica) ---
# Usamos una clase para que los cambios se reflejen en tiempo real
class SimulationConfig:
    def __init__(self):
        # FACTOR DE ESCALA MAESTRO (Generalización Total)
        # Cambia este valor y todo el universo se re-escala visual y físicamente.
        self.SCALE = 3.0              
        
        # --- PARÁMETROS BASE (Para SCALE = 1.0) ---
        self.BASE_ATOM_SIZE = 10.0
        self.BASE_BOND_WIDTH = 1.5
        self.BASE_DIST_EQ = 35.0      # Distancia de equilibrio base
        self.BASE_ENLACE_MIN = 2.0    # Mínimo para permitir uniones tras colisión
        self.BASE_ENLACE_MAX = 70.0   # Máximo para detectar vecinos
        
        # --- VALORES DERIVADOS (Automáticos) ---
        self.WORLD_SIZE = 15000
        self.ATOM_SIZE_GL = self.BASE_ATOM_SIZE * self.SCALE
        self.BOND_WIDTH = self.BASE_BOND_WIDTH * self.SCALE
        self.INITIAL_ZOOM = 4.15
        
        # Física Proporcional
        self.FRICTION = 0.95          
        self.DAMPING = 2.0 * self.SCALE
        self.SPRING_K = 1.5           
        self.DIST_EQUILIBRIO = self.BASE_DIST_EQ * self.SCALE 
        self.TEMPERATURE = 0.1        
        self.GRAVITY = 0.0            
        self.TIME_SCALE = 1.0         
        
        # Límites de seguridad escalados
        self.MAX_VELOCIDAD = 8.0 * self.SCALE
        self.MAX_FUERZA = 20.0 * self.SCALE
        
        # Rangos de enlace escalados
        self.RANGO_ENLACE_MIN = self.BASE_ENLACE_MIN * self.SCALE
        self.RANGO_ENLACE_MAX = self.BASE_ENLACE_MAX * self.SCALE 
        self.DIST_ROTURA = self.RANGO_ENLACE_MAX * 1.5
        
        # --- MODO REALISMO (Nuevos ajustes científicos) ---
        self.REALISM_MODE = True
        self.PROB_ENLACE_BASE = 0.3  # Mucho más raro por defecto (Realista)
        self.BASE_ENLACE_MAX = 45.0   # Rangos más cortos por defecto
        
        # --- PARÁMETROS DE INTERACCIÓN (Game Mechanics) ---
        self.CLICK_FORCE = 50.0 * self.SCALE
        self.CLICK_RADIUS = 30.0 * self.SCALE
        
        # Flags de Visualización
        self.SHOW_DEBUG = True
        self.SHOW_GRID = True
        
        # Configuración Visual del Debugger (F3)
        self.DEBUG_CONFIG = {
            "border_color": (0.8, 0.2, 0.2), # Rojo
            "screen_color": (0.4, 0.8, 1.0), # Cyan
            "line_width": 0.005,
            "font_size": 18,
            "panel_alpha": 0.7  # Futuro: Transparencia
        }

    def toggle_realism(self):
        self.REALISM_MODE = not self.REALISM_MODE
        if self.REALISM_MODE:
            self.PROB_ENLACE_BASE = 0.3  # Mucho más raro, más realista
            self.BASE_ENLACE_MAX = 45.0   # Rangos más cortos
        else:
            self.PROB_ENLACE_BASE = 0.8  # Denso y satisfactorio
            self.BASE_ENLACE_MAX = 70.0
        
        # Recalcular derivados
        self.RANGO_ENLACE_MAX = self.BASE_ENLACE_MAX * self.SCALE
        self.DIST_ROTURA = self.RANGO_ENLACE_MAX * 1.5

    def reset_to_defaults(self):
        self.FRICTION = 0.9354
        self.DAMPING = 4.2
        self.SPRING_K = 0.9
        self.TEMPERATURE = 0.0
        self.GRAVITY = 0.0
        self.TIME_SCALE = 1
        self.SHOW_DEBUG = False

import os
import json

# --- CARGADOR DINÁMICO DE DATOS (Data-Driven) ---
def load_atoms_from_json():
    atoms_path = os.path.join(os.getcwd(), "data", "atoms")
    atom_data = {}
    
    if not os.path.exists(atoms_path):
        os.makedirs(atoms_path)
        return {} # Retornar vacío si no hay datos
        
    for filename in os.listdir(atoms_path):
        if filename.endswith(".json"):
            with open(os.path.join(atoms_path, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                symbol = data.get("symbol", filename.split(".")[0].upper())
                atom_data[symbol] = data
                
    return atom_data

# Cargamos la tabla periódica dinámica
ATOMS = load_atoms_from_json()

# Si por alguna razón está vacío, fallback de seguridad
if not ATOMS:
    ATOMS = {
        "H": {"color": (255, 255, 255), "radius": 6, "mass": 1.0, "valence": 1, "electronegativity": 2.1, "description": "Error al cargar JSON"}
    }

# Pre-procesamiento de la tabla para NumPy (Índices numéricos)
TIPOS_NOMBRES = list(ATOMS.keys())
COLORES = np.array([a["color"] for a in ATOMS.values()])
RADIOS = np.array([a["radius"] for a in ATOMS.values()])
MASAS = np.array([a["mass"] for a in ATOMS.values()])
VALENCIAS = np.array([a["valence"] for a in ATOMS.values()])
# Nuevo: Electronegatividades dinámicas
ELECTRONEG_DATA = np.array([a.get("electronegativity", 2.0) for a in ATOMS.values()])

# Instancia global (Contexto de Configuración)
sim_config = SimulationConfig()
