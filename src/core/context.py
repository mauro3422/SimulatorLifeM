import src.config as cfg
from src.renderer.camera import Camera
from src.core.event_system import get_event_system, SimulationTimeline, EventHistory, EventDetector

class AppContext:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContext, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        # Global Configuration
        self.cfg = cfg
        self.show_debug = True
        
        # Core Systems
        self.camera = None
        self.universe = None
        
        # Timeline & Events (Sistema de Narración)
        event_sys = get_event_system()
        self.timeline: SimulationTimeline = event_sys['timeline']
        self.event_history: EventHistory = event_sys['history']
        self.event_detector: EventDetector = event_sys['detector']
        
        # State
        self.running = True
        self.paused = False
        self.selected_atom = -1
        
        self.initialized = True

    def init_camera(self, world_size, win_w, win_h):
        """Initialize the camera system."""
        self.camera = Camera(world_size, win_w, win_h)
        return self.camera

    def get_camera(self):
        """Get the active camera instance."""
        return self.camera
    
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
    
    def get_recent_events(self, n: int = 5):
        """Retorna los últimos N eventos."""
        return self.event_history.get_recent(n)

# Global Accessor
def get_context():
    return AppContext()
