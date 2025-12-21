import numpy as np
import src.config as cfg

class Universe:
    """
    El 'Contexto' de la simulación.
    """
    def __init__(self):
        # Referencia a la configuración ajustable
        self.config = cfg.sim_config
        
        # 1. Datos de las Partículas
        n = self.config.N_PARTICULAS
        self.tipos = np.random.randint(0, len(cfg.TIPOS_NOMBRES), n)
        self.pos = np.random.rand(n, 2)
        self.pos[:, 0] *= self.config.WIDTH - 200 # Dejar espacio para el panel
        self.pos[:, 1] *= self.config.HEIGHT
        self.pos_old = self.pos.copy()  # Para PBD: posición anterior
        self.vel = np.random.randn(n, 2) * 0.3  # Velocidad inicial baja
        
        # 2. Propiedades Visuales (Caché)
        self.colores_asignados = cfg.COLORES[self.tipos] 
        self.radios_asignados = cfg.RADIOS[self.tipos]

        # 3. Química y Enlaces
        self.valencias_max = cfg.VALENCIAS[self.tipos]
        self.manos_libres = self.valencias_max.copy().astype(float)
        self.enlaces = np.zeros((n, n), dtype=bool)
        
        # 4. Sistema de Sleeping (Optimización)
        self.is_sleeping = np.zeros(n, dtype=bool)  # True = partícula dormida
        self.sleep_counter = np.zeros(n, dtype=int)  # Frames sin movimiento
        self.SLEEP_THRESHOLD = 0.1  # Velocidad mínima para dormir
        self.SLEEP_FRAMES = 30  # Frames quieto antes de dormir

    def reset(self):
        """Reinicia la simulación al estado inicial."""
        self.__init__()
