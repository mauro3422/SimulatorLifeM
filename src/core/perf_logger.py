"""
Performance Logger - Sistema de Logging para Métricas de Rendimiento
====================================================================
Captura tiempos de ejecución de GPU, física, química y render.
Persiste datos por 2 sesiones para análisis de cuellos de botella.
"""
import time
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


# ===================================================================
# CONFIGURACIÓN
# ===================================================================

LOG_DIR = Path("logs/performance")
MAX_SESSIONS = 2  # Mantener últimas 2 sesiones
SAMPLE_INTERVAL = 60  # Guardar cada 60 frames
MAX_SAMPLES_PER_SESSION = 1000  # Máximo muestras por sesión


# ===================================================================
# ESTRUCTURAS DE DATOS
# ===================================================================

@dataclass
class FrameMetrics:
    """Métricas de un frame individual."""
    frame_id: int = 0
    timestamp: float = 0.0
    
    # Tiempos en milisegundos
    total_ms: float = 0.0
    physics_ms: float = 0.0
    chemistry_ms: float = 0.0
    grid_ms: float = 0.0
    render_ms: float = 0.0
    logic_py_ms: float = 0.0
    data_transfer_ms: float = 0.0
    cpu_logic_ms: float = 0.0
    ui_ms: float = 0.0
    sync_ms: float = 0.0
    gpu_wait_ms: float = 0.0
    
    # Granular Physics/Chemistry
    phy_pre_ms: float = 0.0
    phy_pbd_ms: float = 0.0
    phy_post_ms: float = 0.0
    chem_bond_ms: float = 0.0
    phy_adv_ms: float = 0.0
    chem_evo_ms: float = 0.0
    
    # Contadores
    active_particles_count: int = 0
    simulated_count: int = 0
    n_visible: int = 0
    n_visible: int = 0
    bonds_count: int = 0
    bonds_broken_dist: int = 0  # <--- NEW METRIC
    
    # FPS
    fps: float = 0.0


@dataclass
class SessionStats:
    """Estadísticas agregadas de una sesión."""
    session_id: str = ""
    start_time: str = ""
    end_time: str = ""
    total_frames: int = 0
    
    # Promedios (ms)
    avg_total_ms: float = 0.0
    avg_physics_ms: float = 0.0
    avg_chemistry_ms: float = 0.0
    avg_chemistry_ms: float = 0.0
    avg_render_ms: float = 0.0
    avg_logic_py_ms: float = 0.0
    avg_fps: float = 0.0
    
    # Máximos (cuellos de botella)
    max_total_ms: float = 0.0
    max_physics_ms: float = 0.0
    max_chemistry_ms: float = 0.0
    max_render_ms: float = 0.0
    
    # Promedios Granulares
    avg_phy_pre_ms: float = 0.0
    avg_phy_pbd_ms: float = 0.0
    avg_phy_post_ms: float = 0.0
    avg_chem_bond_ms: float = 0.0
    avg_phy_adv_ms: float = 0.0
    avg_chem_evo_ms: float = 0.0
    
    # Muestras detalladas
    samples: List[Dict] = field(default_factory=list)


# ===================================================================
# PERFORMANCE LOGGER
# ===================================================================

class PerfLogger:
    """Sistema de logging de rendimiento con persistencia."""
    
    _instance: Optional["PerfLogger"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.enabled = True
        
        # Sesión actual
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        self.frame_count = 0
        
        # Métricas actuales
        self._current_metrics = FrameMetrics()
        self._timers: Dict[str, float] = {}
        
        # Acumuladores para promedios
        self._totals: Dict[str, float] = {
            "total_ms": 0, "physics_ms": 0, "chemistry_ms": 0,
            "grid_ms": 0, "render_ms": 0, "logic_py_ms": 0, 
            "data_transfer_ms": 0, "cpu_logic_ms": 0,
            "ui_ms": 0, "sync_ms": 0,
            "gpu_wait_ms": 0, "phy_adv_ms": 0,
            "active_particles_count": 0, "simulated_count": 0,
            "active_particles_count": 0, "simulated_count": 0,
            "n_visible": 0, "bonds_count": 0, "bonds_broken_dist": 0,
            "fps": 0
        }
        self._maxes: Dict[str, float] = {k: 0 for k in self._totals}
        
        # Muestras
        self._samples: List[Dict] = []
        
        # Crear directorio de logs
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Limpiar sesiones antiguas
        self._cleanup_old_sessions()
        
        print(f"[PERF] Logger iniciado - Sesión: {self.session_id}")
    
    # ===================================================================
    # API DE TIMING
    # ===================================================================
    
    def start(self, name: str):
        """Inicia un timer para una sección de código."""
        if not self.enabled:
            return
        self._timers[name] = time.perf_counter()
    
    def stop(self, name: str) -> float:
        """Detiene un timer y retorna el tiempo en ms."""
        if not self.enabled or name not in self._timers:
            return 0.0
        
        elapsed_ms = (time.perf_counter() - self._timers[name]) * 1000
        
        # Guardar en métrica actual (Acumular por si hay múltiples llamadas por frame)
        attr_name = f"{name}_ms"
        if hasattr(self._current_metrics, attr_name):
            current_val = getattr(self._current_metrics, attr_name)
            setattr(self._current_metrics, attr_name, current_val + elapsed_ms)
        
        return elapsed_ms
    
    def set_counter(self, name: str, value: int):
        """Establece un contador (partículas, enlaces, etc)."""
        if not self.enabled:
            return
        if hasattr(self._current_metrics, name):
            setattr(self._current_metrics, name, value)
    
    def end_frame(self, fps: float = 0.0):
        """Finaliza el frame actual y acumula métricas."""
        if not self.enabled:
            return
        
        self.frame_count += 1
        self._current_metrics.frame_id = self.frame_count
        self._current_metrics.timestamp = time.time()
        self._current_metrics.fps = fps
        
        # Acumular para promedios y máximos
        for key in self._totals:
            if hasattr(self._current_metrics, key):
                val = getattr(self._current_metrics, key)
                self._totals[key] += val
                self._maxes[key] = max(self._maxes[key], val)
        
        # Guardar muestra cada N frames
        if self.frame_count % SAMPLE_INTERVAL == 0:
            if len(self._samples) < MAX_SAMPLES_PER_SESSION:
                self._samples.append(asdict(self._current_metrics))
        
        # Reset para próximo frame
        self._current_metrics = FrameMetrics()
    
    # ===================================================================
    # PERSISTENCIA
    # ===================================================================
    
    def save_session(self):
        """Guarda la sesión actual a disco."""
        if self.frame_count == 0:
            return
        
        # Calcular estadísticas
        stats = SessionStats(
            session_id=self.session_id,
            start_time=self.start_time.isoformat(),
            end_time=datetime.now().isoformat(),
            total_frames=self.frame_count,
            avg_total_ms=self._totals["total_ms"] / self.frame_count,
            avg_physics_ms=self._totals["physics_ms"] / self.frame_count,
            avg_chemistry_ms=self._totals["chemistry_ms"] / self.frame_count,
            avg_render_ms=self._totals["render_ms"] / self.frame_count,
            avg_fps=self._totals["fps"] / self.frame_count,
            max_total_ms=self._maxes["total_ms"],
            max_physics_ms=self._maxes["physics_ms"],
            max_chemistry_ms=self._maxes["chemistry_ms"],
            max_render_ms=self._maxes["render_ms"],
            
            # Granular Averages
            avg_phy_pre_ms=self._totals.get("phy_pre_ms", 0.0) / self.frame_count,
            avg_phy_pbd_ms=self._totals.get("phy_pbd_ms", 0.0) / self.frame_count,
            avg_phy_post_ms=self._totals.get("phy_post_ms", 0.0) / self.frame_count,
            avg_chem_bond_ms=self._totals.get("chem_bond_ms", 0.0) / self.frame_count,
            avg_phy_adv_ms=self._totals.get("phy_adv_ms", 0.0) / self.frame_count,
            avg_chem_evo_ms=self._totals.get("chem_evo_ms", 0.0) / self.frame_count,
            
            samples=self._samples
        )
        
        # Guardar JSON
        filepath = LOG_DIR / f"session_{self.session_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(stats), f, indent=2)
        
        print(f"[PERF] Sesión guardada: {filepath}")
        print(f"[PERF] Frames: {self.frame_count}, FPS Avg: {stats.avg_fps:.1f}")
        print(f"[PERF] Máximos - Total: {stats.max_total_ms:.2f}ms, "
              f"Physics: {stats.max_physics_ms:.2f}ms, "
              f"Chemistry: {stats.max_chemistry_ms:.2f}ms")
    
    def _cleanup_old_sessions(self):
        """Elimina sesiones antiguas, manteniendo MAX_SESSIONS."""
        if not LOG_DIR.exists():
            return
        
        sessions = sorted(LOG_DIR.glob("session_*.json"))
        while len(sessions) > MAX_SESSIONS - 1:  # -1 para dejar espacio a la actual
            oldest = sessions.pop(0)
            oldest.unlink()
            print(f"[PERF] Sesión antigua eliminada: {oldest.name}")
    
    def get_last_sessions(self) -> List[SessionStats]:
        """Carga las últimas sesiones guardadas."""
        sessions = []
        for filepath in sorted(LOG_DIR.glob("session_*.json")):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    sessions.append(SessionStats(**data))
            except Exception as e:
                print(f"[PERF] Error cargando {filepath}: {e}")
        return sessions
    
    # ===================================================================
    # REPORTES
    # ===================================================================
    
    def print_summary(self):
        """Imprime resumen de la sesión actual."""
        if self.frame_count == 0:
            print("[PERF] Sin datos de sesión")
            return
        
        print("\n" + "=" * 60)
        print(f"RESUMEN DE PERFORMANCE - Sesión {self.session_id}")
        print("=" * 60)
        print(f"Frames: {self.frame_count}")
        print(f"FPS Promedio: {self._totals['fps'] / self.frame_count:.1f}")
        
        avg_alloc = self._totals.get("active_particles_count", 0) / self.frame_count
        avg_sim = self._totals.get("simulated_count", 0) / self.frame_count
        avg_vis = self._totals.get("n_visible", 0) / self.frame_count
        print(f"Partículas: Alloc={int(avg_alloc)} | Sim={int(avg_sim)} | Vis={int(avg_vis)}")
        
        print(f"\nTiempos Promedio (ms):")
        print(f"  Total:     {self._totals['total_ms'] / self.frame_count:.3f}")
        print(f"  Física:    {self._totals['physics_ms'] / self.frame_count:.3f}")
        print(f"  Química:   {self._totals['chemistry_ms'] / self.frame_count:.3f}")
        print(f"  Grid:      {self._totals['grid_ms'] / self.frame_count:.3f}")
        print(f"  Render:    {self._totals['render_ms'] / self.frame_count:.3f}")
        print(f"  LogicPy:   {self._totals['logic_py_ms'] / self.frame_count:.3f}")
        print(f"    - GPUWait: {self._totals.get('gpu_wait_ms', 0)/self.frame_count:.3f} <-- Real Physics Cost")
        print(f"    - DataTx:  {self._totals['data_transfer_ms'] / self.frame_count:.3f}")
        print(f"    - CPULog:  {self._totals['cpu_logic_ms'] / self.frame_count:.3f}")
        print(f"  UI:        {self._totals['ui_ms'] / self.frame_count:.3f}")
        
        # Physics Granular (If captured)
        if self._totals['phy_adv_ms'] > 0:
            print(f"  PhyAdv:    {self._totals['phy_adv_ms'] / self.frame_count:.3f} (Interleaved)")
            
        print(f"\nMáximos (Peak Latency):")
        print(f"  Total:     {self._maxes['total_ms']:.3f}ms")
        print(f"  Física:    {self._maxes['physics_ms']:.3f}ms")
        print(f"  Química:   {self._maxes['chemistry_ms']:.3f}ms")
        print("=" * 60)


# ===================================================================
# SINGLETON ACCESS
# ===================================================================

def get_perf_logger() -> PerfLogger:
    """Obtiene la instancia del logger de performance."""
    return PerfLogger()


# ===================================================================
# CONTEXT MANAGER
# ===================================================================

class PerfTimer:
    """Context manager para medir tiempos fácilmente."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_perf_logger()
    
    def __enter__(self):
        self.logger.start(self.name)
        return self
    
    def __exit__(self, *args):
        self.logger.stop(self.name)


# Alias para uso rápido
def perf_timer(name: str) -> PerfTimer:
    """Crea un timer de performance como context manager."""
    return PerfTimer(name)
