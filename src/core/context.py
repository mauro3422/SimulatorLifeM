"""
AppContext - Contexto Global Unificado de la Aplicación.
=========================================================
Singleton que gestiona todo el estado de la aplicación:
- Cámara y visualización
- Campos de simulación Taichi
- Timeline y eventos
- Estado de boost/pausa
- Estadísticas y métricas
"""

import time
import numpy as np
import src.config as cfg
from src.renderer.camera import Camera
from src.core.event_system import get_event_system, SimulationTimeline, EventHistory, EventDetector
from src.systems.zone_manager import get_zone_manager


class AppContext:
    """
    Contexto global unificado de la aplicación (Singleton).
    
    Combina la funcionalidad de AppContext + AppState en un único punto
    de acceso para todo el estado de la aplicación.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContext, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # ========== CONFIGURACIÓN GLOBAL ==========
        self.cfg = cfg
        
        # ========== CORE SYSTEMS ==========
        self.camera = None
        self.renderer = None
        self.sim = None  # Diccionario de campos Taichi (inyectado)
        
        # ========== TIMELINE & EVENTOS ==========
        event_sys = get_event_system()
        self.timeline: SimulationTimeline = event_sys['timeline']
        self.event_history: EventHistory = event_sys['history']
        self.event_detector: EventDetector = event_sys['detector']
        self.event_log = []
        
        # ========== ESTADO DE SIMULACIÓN ==========
        self.running = True
        self.paused = False
        self.show_debug = False
        self.show_quimidex = [False] # Toggle para la ventana de QuimiDex
        self.show_labels = True  # Mostrar etiquetas de elementos (H, C, O)
        self.show_molecules = False  # Highlight de moléculas (partículas con enlaces)
        self.lod_threshold = 2.2 # Umbral para cambio a modo Macro (Burbujas)
        self.time_scale = cfg.sim_config.TIME_SCALE
        
        # ========== PROGRESIÓN & METABOLISMO ==========
        from src.systems.progression import get_progression_manager
        self.progression = get_progression_manager(self)
        self.atp = self.progression.atp # Shortcut

        self.world_size = cfg.sim_config.WORLD_SIZE
        self.n_particles_val = 5000
        
        # Datos de render para UI (updateado cada frame)
        self.render_data = {}
        
        # ========== TIMING ==========
        self.last_time = time.time()
        self.fps = 0.0
        
        # ========== SELECCIÓN ==========
        self.selected_idx = -1
        self.selected_mol = []
        
        # ========== JUGADOR ==========
        self.player_idx = 0  # El jugador siempre es la partícula 0 (H atom)
        self.player_force = [0.0, 0.0]  # Fuerza a aplicar este frame
        
        # ========== BOOST & VELOCIDAD ==========
        self.boost_active = False
        self.stored_speed = 1.0
        self.pause_timer = 0.0
        self.last_tab_time = 0.0
        
        # ========== ESTADÍSTICAS ==========
        self.stats = {
            "bonds_formed": 0,
            "bonds_broken": 0,
            "mutations": 0,
            "tunnels": 0
        }
        self.last_bonds = 0
        self.last_mutations = 0
        self.last_tunnels = 0
        
        self._initialized = True

    # ==================== INICIALIZACIÓN ====================
    
    def init_camera(self, world_size: float, win_w: int, win_h: int):
        """Inicializa el sistema de cámara."""
        self.world_size = world_size
        self.camera = Camera(world_size, win_w, win_h)
        self.camera.set_zoom(cfg.sim_config.INITIAL_ZOOM)
        return self.camera

    def init_simulation(self, simulation_fields: dict):
        """
        Inyecta el diccionario de campos Taichi.
        
        Args:
            simulation_fields: Dict con referencias a campos Taichi:
                - 'n_particles', 'pos', 'vel', 'radii', 'is_active'
                - 'atom_types', 'colors', 'manos_libres'
                - 'enlaces_idx', 'num_enlaces'
                - 'gravity', 'friction', 'temperature', 'max_speed'
                - 'world_width', 'world_height'
                - etc.
        """
        self.sim = simulation_fields
        self.init_world()

    def init_world(self):
        """Inicializa el mundo con partículas aleatorias."""
        if self.sim is None:
            print("[ERROR] Campos de simulación no inicializados")
            return
            
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

        # Spawning balanceado para CHONPS+Si (Realista con Silicatos)
        # Atom order: [C, H, N, O, P, S, Si] (indices 0-6)
        
        # 1. Generar Posiciones Primero
        margin = 1000
        pos_np = np.zeros((max_particles, 2), dtype=np.float32)
        pos_np[:self.n_particles_val, 0] = np.random.uniform(margin, self.world_size - margin, self.n_particles_val)
        pos_np[:self.n_particles_val, 1] = np.random.uniform(margin, self.world_size - margin, self.n_particles_val)
        
        # 2. Decidir tipos basados en la posición (Zonas)
        zm = get_zone_manager(self.world_size)
        tipos = np.zeros(self.n_particles_val, dtype=np.int32)
        
        # Probabilidades Base (Oceano Abierto)
        p_base = [0.15, 0.50, 0.05, 0.25, 0.02, 0.02, 0.01] # C, H, N, O, P, S, Si
        # Probabilidades en Arcilla (Rico en Si, C, N)
        p_clay = [0.25, 0.35, 0.15, 0.15, 0.02, 0.03, 0.05]
        # Probabilidades en Ventila (Rico en P, S, metales/C)
        p_vent = [0.25, 0.35, 0.05, 0.15, 0.10, 0.10, 0.00]
        
        for idx in range(self.n_particles_val):
            p_to_use = p_base
            zone = zm.get_zone_at(pos_np[idx])
            if zone:
                from src.systems.zone_manager import ZoneType
                if zone.type == ZoneType.CLAY:
                    p_to_use = p_clay
                elif zone.type == ZoneType.THERMAL_VENT:
                    p_to_use = p_vent
                    
            tipos[idx] = np.random.choice([0, 1, 2, 3, 4, 5, 6], p=p_to_use)

        # JUGADOR: Índice 0 siempre es un átomo de H (si el usuario lo controla)
        tipos[0] = 1  # H = tipo 1
        self.player_idx = 0
        
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
        
        sim['pos'].from_numpy(pos_np)
        
        is_active_np = np.pad(
            np.ones(self.n_particles_val, dtype=np.int32),
            (0, max_particles - self.n_particles_val),
            constant_values=0
        )
        sim['is_active'].from_numpy(is_active_np)
        
        print(f"[INIT] Mundo {self.world_size}x{self.world_size} con {self.n_particles_val} partículas.")

    # ==================== CÁMARA ====================
    
    def get_camera(self):
        """Retorna la instancia de cámara activa."""
        return self.camera

    # ==================== TIMELINE ====================
    
    def tick_simulation(self, n_steps: int = 1):
        """Avanza el tiempo de simulación."""
        self.timeline.tick(n_steps * self.timeline.speed)
    
    def get_sim_time(self) -> str:
        """Retorna el tiempo de simulación formateado."""
        return self.timeline.get_formatted_time()
    
    def get_sim_frame(self) -> int:
        """Retorna el frame actual."""
        return self.timeline.frame
    
    def speed_up(self):
        """Aumenta velocidad de simulación."""
        return self.timeline.speed_up()
    
    def speed_down(self):
        """Reduce velocidad de simulación."""
        return self.timeline.speed_down()

    # ==================== EVENTOS ====================
    
    def get_recent_events(self, n: int = 5):
        """Retorna los últimos N eventos."""
        return self.event_history.get_recent(n)
    
    def add_log(self, text: str, category: str = "info"):
        """Añade una entrada al log de eventos."""
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.insert(0, f"[{timestamp}] {text}")
        if len(self.event_log) > 20:
            self.event_log.pop()

    def get_player_pos(self) -> np.ndarray:
        """Retorna la posición del jugador en el mundo."""
        if self.sim and 'pos' in self.sim:
            pos_np = self.sim['pos'].to_numpy()
            return pos_np[self.player_idx]
        return None

    def get_molecule_indices(self, atom_idx: int):
        """Retorna los índices de todos los átomos conectados al dado."""
        from src.systems.molecular_analyzer import get_molecular_analyzer
        analyzer = get_molecular_analyzer()
        for mid, mol in analyzer.active_molecules.items():
            if atom_idx in mol.atom_indices:
                return mol.atom_indices
        return [atom_idx]

    def get_formula(self, indices):
        """Obtiene la fórmula química para un set de índices."""
        from src.systems.molecular_analyzer import get_molecular_analyzer
        return get_molecular_analyzer().get_formula(indices, self.sim['atom_types'].to_numpy())


    def get_valence(self, idx: int) -> int:
        """Retorna la valencia máxima de un átomo."""
        if self.sim is None: return 4
        atom_types = self.sim.get('atom_types')
        if atom_types is not None:
            types_np = atom_types.to_numpy()
            if idx < len(types_np):
                a_type = types_np[idx]
                return cfg.VALENCIAS[a_type]
        return 4 # Default


    def sync_to_gpu(self):
        """Sincroniza el estado de Python a los campos Taichi en la GPU."""
        sim = self.sim
        if sim is None:
            return
        
        # 1. Aplicar BUFFS de progresión a los parámetros de Config
        base_rotura = cfg.sim_config.DIST_ROTURA
        base_speed = cfg.sim_config.MAX_VELOCIDAD
        
        if "stability" in self.progression.active_buffs:
            # Los enlaces aguantan un 50% más de estiramiento
            sim['dist_rotura'][None] = base_rotura * 1.5
        else:
            sim['dist_rotura'][None] = base_rotura
            
        if "speed" in self.progression.active_buffs:
            sim['max_speed'][None] = base_speed * 1.2
        else:
            sim['max_speed'][None] = base_speed

        # 2. Catálisis de Arcilla
        if self.progression.in_clay:
            sim['prob_enlace_base'][None] = 0.95 # Muy alta probabilidad en arcilla
        else:
            sim['prob_enlace_base'][None] = cfg.sim_config.PROB_ENLACE_BASE
        
        # 3. Sincronizar parámetros estáticos o HUD
        sim['gravity'][None] = cfg.sim_config.GRAVITY
        sim['friction'][None] = cfg.sim_config.FRICTION
        sim['temperature'][None] = cfg.sim_config.TEMPERATURE
        
        # Parámetros de enlaces
        sim['dist_equilibrio'][None] = cfg.sim_config.DIST_EQUILIBRIO
        sim['spring_k'][None] = cfg.sim_config.SPRING_K
        sim['damping'][None] = cfg.sim_config.DAMPING
        sim['rango_enlace_min'][None] = cfg.sim_config.RANGO_ENLACE_MIN
        sim['rango_enlace_max'][None] = cfg.sim_config.RANGO_ENLACE_MAX
        sim['max_fuerza'][None] = cfg.sim_config.MAX_FUERZA
        
        # Parámetros de Interacción
        sim['click_force'][None] = cfg.sim_config.CLICK_FORCE
        sim['click_radius'][None] = cfg.sim_config.CLICK_RADIUS

    # --- Input Handler updates --- 

    
    def get_molecule_indices(self, start_idx: int) -> list:
        """Traversa los enlaces para encontrar toda la molécula conectada."""
        if start_idx < 0 or self.sim is None:
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
        """Genera fórmula estricta para identificación (ej: H2O1, C1H4)."""
        if not indices or self.sim is None:
            return ""
        
        counts = {}
        # Acceso directo para evitar overhead de to_numpy() si son pocos indices
        types = self.sim['atom_types']
        
        for i in indices:
            t = types[i]
            sym = cfg.TIPOS_NOMBRES[t]
            counts[sym] = counts.get(sym, 0) + 1
        
        # Orden alfabético estricto para consistencia con diccionario
        sorted_syms = sorted(counts.keys())
        formula = ""
        for s in sorted_syms:
            count = counts[s]
            if count > 1:
                formula += f"{s}{count}"
            else:
                formula += f"{s}"
            
        return formula


# ==================== ACCESO GLOBAL ====================

def get_context() -> AppContext:
    """Retorna la instancia singleton del contexto."""
    return AppContext()
