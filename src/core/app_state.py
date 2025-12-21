"""
AppState - Estado global de la aplicación y simulación.
Extraído de main.py con inyección de dependencias para campos Taichi.
"""

import time
import numpy as np
from src.core.context import get_context
import src.config as cfg


class AppState:
    """
    Estado global de la aplicación.
    
    Mantiene el estado de la cámara, selección, tiempo y métricas.
    Usa inyección de dependencias para los campos Taichi.
    """
    
    def __init__(self, world_size: float, simulation_fields: dict):
        """
        Args:
            world_size: Tamaño del mundo de simulación
            simulation_fields: Dict con referencias a campos Taichi:
                - 'n_particles', 'pos', 'vel', 'radii', 'is_active'
                - 'atom_types', 'colors', 'manos_libres'
                - 'enlaces_idx', 'num_enlaces'
                - 'gravity', 'friction', 'temperature', 'max_speed'
                - 'world_width', 'world_height'
                - 'dist_equilibrio', 'spring_k', 'damping'
                - 'rango_enlace_min', 'rango_enlace_max', 'dist_rotura', 'max_fuerza'
                - 'prob_enlace_base', 'click_force', 'click_radius'
                - 'MAX_PARTICLES' (constante)
        """
        self.world_size = world_size
        self.sim = simulation_fields  # Referencia a campos Taichi
        
        # Contexto OpenGL y Cámara
        self.ctx_global = get_context()
        self.camera = self.ctx_global.init_camera(world_size, 1280, 720)
        self.camera.set_zoom(cfg.sim_config.INITIAL_ZOOM)
        
        # Estado de simulación
        self.paused = False
        self.time_scale = cfg.sim_config.TIME_SCALE
        self.show_debug = False
        self.n_particles_val = 5000
        self.renderer = None
        
        # Timing
        self.last_time = time.time()
        self.fps = 0.0
        
        # Logging y Selección
        self.event_log = []
        self.selected_idx = -1
        self.selected_mol = []
        
        # Gestión de Tiempo y Boost
        self.boost_active = False
        self.stored_speed = 1.0
        self.pause_timer = 0.0
        self.last_tab_time = 0.0
        
        # Métricas Acumulativas
        self.stats = {
            "bonds_formed": 0,
            "bonds_broken": 0,
            "mutations": 0,
            "tunnels": 0
        }
        
        self.init_world()
    
    def get_molecule_indices(self, start_idx: int) -> list:
        """Traversa los enlaces para encontrar toda la molécula conectada."""
        if start_idx < 0:
            return []
        
        mol = {start_idx}
        stack = [start_idx]
        
        # Obtenemos los enlaces del buffer Taichi
        all_enlaces = self.sim['enlaces_idx'].to_numpy()
        num_v_enlaces = self.sim['num_enlaces'].to_numpy()
        
        while stack:
            curr = stack.pop()
            for i in range(num_v_enlaces[curr]):
                neighbor = all_enlaces[curr, i]
                if neighbor >= 0 and neighbor not in mol:
                    mol.add(neighbor)
                    stack.append(neighbor)
        return list(mol)
    
    def get_formula(self, indices: list) -> str:
        """Genera una fórmula simplificada (ej: H2 O)."""
        if not indices:
            return ""
        
        counts = {}
        a_types = self.sim['atom_types'].to_numpy()
        
        for i in indices:
            t = a_types[i]
            sym = cfg.TIPOS_NOMBRES[t]
            counts[sym] = counts.get(sym, 0) + 1
        
        formula = ""
        # Orden preferido: C, H, O, N, P, S
        for s in ["C", "H", "O", "N", "P", "S"]:
            if s in counts:
                formula += f"{s}{counts[s] if counts[s] > 1 else ''} "
        for s, c in counts.items():
            if s not in ["C", "H", "O", "N", "P", "S"]:
                formula += f"{s}{c if c > 1 else ''} "
        return formula.strip()
    
    def add_log(self, text: str):
        """Añade una entrada al log de eventos."""
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.insert(0, f"[{timestamp}] {text}")
        if len(self.event_log) > 15:
            self.event_log.pop()
    
    def init_world(self):
        """Inicializa el mundo con partículas aleatorias."""
        sim = self.sim
        max_particles = sim['MAX_PARTICLES']
        
        sim['n_particles'][None] = self.n_particles_val
        
        # Sincronizar parámetros desde Config Central
        sim['gravity'][None] = cfg.sim_config.GRAVITY
        sim['friction'][None] = cfg.sim_config.FRICTION
        sim['temperature'][None] = cfg.sim_config.TEMPERATURE
        sim['max_speed'][None] = cfg.sim_config.MAX_VELOCIDAD
        sim['world_width'][None] = float(self.world_size)
        sim['world_height'][None] = float(self.world_size)
        
        # Parámetros de enlaces
        sim['dist_equilibrio'][None] = cfg.sim_config.DIST_EQUILIBRIO
        sim['spring_k'][None] = cfg.sim_config.SPRING_K
        sim['damping'][None] = cfg.sim_config.DAMPING
        sim['rango_enlace_min'][None] = cfg.sim_config.RANGO_ENLACE_MIN
        sim['rango_enlace_max'][None] = cfg.sim_config.RANGO_ENLACE_MAX
        sim['dist_rotura'][None] = cfg.sim_config.DIST_ROTURA
        sim['max_fuerza'][None] = cfg.sim_config.MAX_FUERZA
        
        # Parámetros de Interacción
        sim['prob_enlace_base'][None] = cfg.sim_config.PROB_ENLACE_BASE
        sim['click_force'][None] = cfg.sim_config.CLICK_FORCE
        sim['click_radius'][None] = cfg.sim_config.CLICK_RADIUS

        # Spawning balanceado para CHONPS
        # H (40%), O (20%), C (20%), N (10%), P (5%), S (5%)
        tipos = np.random.choice(
            [0, 1, 2, 3, 4, 5],
            size=self.n_particles_val,
            p=[0.4, 0.2, 0.2, 0.1, 0.05, 0.05]
        )
        
        atom_types_full = np.pad(
            tipos, (0, max_particles - self.n_particles_val), constant_values=0
        ).astype(np.int32)
        sim['atom_types'].from_numpy(atom_types_full)
        
        colors_table = (cfg.COLORES / 255.0).astype(np.float32)
        col_np = colors_table[atom_types_full]
        sim['colors'].from_numpy(col_np)
        
        radii_np = np.zeros(max_particles, dtype=np.float32)
        radii_np[:self.n_particles_val] = (cfg.RADIOS[tipos] * 1.5 + 5.0) * cfg.sim_config.SCALE
        sim['radii'].from_numpy(radii_np)
        
        manos_np = np.zeros(max_particles, dtype=np.float32)
        manos_np[:self.n_particles_val] = cfg.VALENCIAS[tipos]
        sim['manos_libres'].from_numpy(manos_np)
        
        margin = 1000
        pos_np = np.zeros((max_particles, 2), dtype=np.float32)
        pos_np[:self.n_particles_val, 0] = np.random.uniform(
            margin, self.world_size - margin, self.n_particles_val
        )
        pos_np[:self.n_particles_val, 1] = np.random.uniform(
            margin, self.world_size - margin, self.n_particles_val
        )
        sim['pos'].from_numpy(pos_np)
        
        is_active_np = np.pad(
            np.ones(self.n_particles_val, dtype=np.int32),
            (0, max_particles - self.n_particles_val),
            constant_values=0
        )
        sim['is_active'].from_numpy(is_active_np)
        
        print(f"[RESTORATION] Mundo {self.world_size}x{self.world_size} con {self.n_particles_val} partículas.")
