"""
Configuración de Simulación
===========================
Parámetros dinámicos que controlan la física y comportamiento de la simulación.
"""


class SimulationConfig:
    """Configuración dinámica de la simulación (modificable en runtime)."""
    
    def __init__(self):
        # FACTOR DE ESCALA MAESTRO
        # Cambia este valor y todo el universo se re-escala
        self.SCALE = 3.0
        
        # --- PARÁMETROS BASE (Para SCALE = 1.0) ---
        self.BASE_ATOM_SIZE = 10.0
        self.BASE_BOND_WIDTH = 1.5
        self.BASE_DIST_EQ = 35.0
        self.BASE_ENLACE_MIN = 2.0
        self.BASE_ENLACE_MAX = 70.0
        
        # --- VALORES DERIVADOS ---
        self.WORLD_SIZE = 15000
        self.ATOM_SIZE_GL = self.BASE_ATOM_SIZE * self.SCALE
        self.BOND_WIDTH = self.BASE_BOND_WIDTH * self.SCALE
        self.INITIAL_ZOOM = 4.15
        
        # --- FÍSICA ---
        self.FRICTION = 0.95
        self.DAMPING = 2.0 * self.SCALE
        self.SPRING_K = 2.5
        self.DIST_EQUILIBRIO = self.BASE_DIST_EQ * self.SCALE
        self.TEMPERATURE = 0.1
        self.GRAVITY = 0.0
        self.TIME_SCALE = 1.0
        
        # Límites de seguridad
        self.MAX_VELOCIDAD = 8.0 * self.SCALE
        self.MAX_FUERZA = 20.0 * self.SCALE
        
        # Rangos de enlace
        self.RANGO_ENLACE_MIN = self.BASE_ENLACE_MIN * self.SCALE
        self.RANGO_ENLACE_MAX = self.BASE_ENLACE_MAX * self.SCALE
        self.DIST_ROTURA = self.RANGO_ENLACE_MAX * 1.5
        
        # --- MODO REALISMO ---
        self.REALISM_MODE = True
        self.PROB_ENLACE_BASE = 0.3
        
        # --- INTERACCIÓN ---
        self.CLICK_FORCE = 50.0 * self.SCALE
        self.CLICK_RADIUS = 30.0 * self.SCALE
        
        # Flags de visualización
        self.SHOW_DEBUG = True
        self.SHOW_GRID = True
        
        # Config visual del debugger
        self.DEBUG_CONFIG = {
            "border_color": (0.8, 0.2, 0.2),
            "screen_color": (0.4, 0.8, 1.0),
            "line_width": 0.005,
            "font_size": 18,
            "panel_alpha": 0.7
        }

    def toggle_realism(self):
        """Alterna entre modo realista y arcade."""
        self.REALISM_MODE = not self.REALISM_MODE
        if self.REALISM_MODE:
            self.PROB_ENLACE_BASE = 0.3
            self.BASE_ENLACE_MAX = 45.0
        else:
            self.PROB_ENLACE_BASE = 0.8
            self.BASE_ENLACE_MAX = 70.0
        
        self.RANGO_ENLACE_MAX = self.BASE_ENLACE_MAX * self.SCALE
        self.DIST_ROTURA = self.RANGO_ENLACE_MAX * 1.5

    def reset_to_defaults(self):
        """Restaura valores por defecto."""
        self.FRICTION = 0.9354
        self.DAMPING = 4.2
        self.SPRING_K = 0.9
        self.TEMPERATURE = 0.0
        self.GRAVITY = 0.0
        self.TIME_SCALE = 1
        self.SHOW_DEBUG = False


# Instancia global
sim_config = SimulationConfig()
