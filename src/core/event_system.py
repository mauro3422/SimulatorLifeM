"""
Sistema de Eventos - QuimicPYTHON
==================================
Gestiona eventos de la simulación para narración y análisis.
Diseñado para futura integración con LLM.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time

class EventType(Enum):
    """Tipos de eventos detectables."""
    MOLECULE_FORMED = "molecule_formed"     # Nueva molécula formada
    MOLECULE_BROKEN = "molecule_broken"     # Molécula se rompió
    BOND_CREATED = "bond_created"           # Enlace individual creado
    BOND_BROKEN = "bond_broken"             # Enlace individual roto
    COMPLEX_STRUCTURE = "complex_structure" # Estructura de 5+ átomos
    WATER_FORMED = "water_formed"           # H₂O específico
    ORGANIC_CHAIN = "organic_chain"         # Cadena C-C-C+
    STABLE_CLUSTER = "stable_cluster"       # Cluster que no cambia
    TEMPERATURE_SPIKE = "temp_spike"        # Cambio brusco de temperatura
    MILESTONE = "milestone"                 # Hito general

@dataclass
class SimEvent:
    """Representa un evento en la simulación."""
    timestamp: int              # Frame en que ocurrió
    event_type: EventType       # Tipo de evento
    description: str            # Descripción legible
    data: Dict[str, Any] = field(default_factory=dict)  # Datos adicionales
    real_time: float = field(default_factory=time.time) # Tiempo real
    
    def to_dict(self) -> Dict:
        """Exporta el evento como diccionario (para JSON/LLM)."""
        return {
            "timestamp": self.timestamp,
            "type": self.event_type.value,
            "description": self.description,
            "data": self.data,
            "real_time": self.real_time
        }
    
    def __str__(self):
        return f"[t={self.timestamp}] {self.description}"

class EventHistory:
    """Almacena y gestiona el historial de eventos."""
    
    def __init__(self, max_events: int = 1000):
        self.events: List[SimEvent] = []
        self.max_events = max_events
        self.event_counts: Dict[EventType, int] = {t: 0 for t in EventType}
    
    def add_event(self, event: SimEvent):
        """Añade un evento al historial."""
        self.events.append(event)
        self.event_counts[event.event_type] += 1
        
        # Limitar tamaño del historial
        if len(self.events) > self.max_events:
            removed = self.events.pop(0)
            self.event_counts[removed.event_type] -= 1
    
    def get_recent(self, n: int = 10) -> List[SimEvent]:
        """Retorna los últimos N eventos."""
        return self.events[-n:]
    
    def get_by_type(self, event_type: EventType) -> List[SimEvent]:
        """Retorna eventos de un tipo específico."""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_summary(self) -> Dict[str, int]:
        """Resumen de conteos por tipo."""
        return {t.value: c for t, c in self.event_counts.items() if c > 0}
    
    def export_json(self) -> List[Dict]:
        """Exporta todo el historial como lista de diccionarios."""
        return [e.to_dict() for e in self.events]
    
    def find_similar(self, event: SimEvent, threshold: int = 100) -> Optional[SimEvent]:
        """Busca eventos similares recientes (para referencias cruzadas)."""
        for past_event in reversed(self.events[:-1]):  # Excluir el actual
            if past_event.event_type == event.event_type:
                if abs(past_event.timestamp - event.timestamp) > threshold:
                    return past_event
        return None

class SimulationTimeline:
    """Controla el tiempo de simulación y velocidad."""
    
    def __init__(self):
        self.frame = 0              # Frame actual
        self.speed = 1              # Multiplicador de velocidad
        self.paused = False         # Estado de pausa
        self.start_real_time = time.time()
        
        # Velocidades disponibles
        self.speed_options = [1, 2, 5, 10, 25, 50, 100]
        self.speed_index = 0
    
    def tick(self, n: int = 1):
        """Avanza el tiempo N frames."""
        if not self.paused:
            self.frame += n
    
    def toggle_pause(self):
        """Alterna pausa."""
        self.paused = not self.paused
        return self.paused
    
    def speed_up(self):
        """Aumenta velocidad."""
        if self.speed_index < len(self.speed_options) - 1:
            self.speed_index += 1
            self.speed = self.speed_options[self.speed_index]
        return self.speed
    
    def speed_down(self):
        """Reduce velocidad."""
        if self.speed_index > 0:
            self.speed_index -= 1
            self.speed = self.speed_options[self.speed_index]
        return self.speed
    
    def get_formatted_time(self) -> str:
        """Retorna tiempo formateado como string."""
        # Convertir frames a "unidades de tiempo" ficticias
        seconds = self.frame // 60
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            return f"{hours}h {minutes % 60}m"
        elif minutes > 0:
            return f"{minutes}m {seconds % 60}s"
        else:
            return f"{self.frame}f"
    
    def get_real_elapsed(self) -> float:
        """Tiempo real transcurrido desde inicio."""
        return time.time() - self.start_real_time

class EventDetector:
    """Detecta eventos significativos en la simulación."""
    
    def __init__(self, history: EventHistory, timeline: SimulationTimeline):
        self.history = history
        self.timeline = timeline
        
        # Estado para detección
        self.last_bond_count = 0
        self.last_molecule_hashes = set()
        self.stable_clusters = {}  # {hash: frames_estable}
    
    def create_event(self, event_type: EventType, description: str, **data) -> SimEvent:
        """Crea y registra un evento."""
        event = SimEvent(
            timestamp=self.timeline.frame,
            event_type=event_type,
            description=description,
            data=data
        )
        self.history.add_event(event)
        return event
    
    def check_water_molecule(self, atom_types, enlaces_matrix, atom_i) -> bool:
        """
        Detecta si atom_i es parte de una molécula de agua H₂O.
        Agua = 1 Oxígeno con 2 Hidrógenos
        """
        # Si el átomo es Oxígeno (tipo 1)
        if atom_types[atom_i] == 1:
            # Contar hidrógenos enlazados
            h_count = 0
            for j, is_bonded in enumerate(enlaces_matrix[atom_i]):
                if is_bonded and atom_types[j] == 0:  # Hidrógeno = 0
                    h_count += 1
            if h_count == 2:
                return True
        return False
    
    def check_carbon_chain(self, atom_types, enlaces_matrix, atom_i, min_length=3) -> int:
        """
        Detecta cadenas de carbono. Retorna longitud de la cadena.
        """
        if atom_types[atom_i] != 2:  # C = 2
            return 0
        
        # BFS para encontrar cadena de carbonos
        visited = {atom_i}
        queue = [atom_i]
        chain_length = 1
        
        while queue:
            current = queue.pop(0)
            for j, is_bonded in enumerate(enlaces_matrix[current]):
                if is_bonded and j not in visited and atom_types[j] == 2:
                    visited.add(j)
                    queue.append(j)
                    chain_length += 1
        
        return chain_length if chain_length >= min_length else 0

# Singleton global para acceso fácil
_event_system = None

def get_event_system():
    """Obtiene el sistema de eventos global."""
    global _event_system
    if _event_system is None:
        timeline = SimulationTimeline()
        history = EventHistory()
        _event_system = {
            'timeline': timeline,
            'history': history,
            'detector': EventDetector(history, timeline)
        }
    return _event_system
