"""
Zone Manager - Sistema de Gestión de Zonas y Catálisis
======================================================
Gestiona áreas especiales en el mundo (Arcilla, Ventilas Termales).
"""

import numpy as np
from enum import Enum

class ZoneType(Enum):
    CLAY = "Clay"           # Estabilización y anillos
    THERMAL_VENT = "Vent"   # Alta energía y entropia

class Zone:
    def __init__(self, x: float, y: float, radius: float, ztype: ZoneType, name: str):
        self.pos = np.array([x, y])
        self.radius = radius
        self.type = ztype
        self.name = name

class ZoneManager:
    def __init__(self, world_size: float):
        self.world_size = world_size
        self.zones = []
        self._generate_zones()
        
    def _generate_zones(self):
        """Genera zonas estratégicas en el mundo."""
        w = self.world_size
        self.zones = [
            # Depósitos de Arcilla (Catalizadores de anillos)
            Zone(w * 0.2, w * 0.2, 1200.0, ZoneType.CLAY, "Arcilla Norte"),
            Zone(w * 0.8, w * 0.8, 1500.0, ZoneType.CLAY, "Arcilla Sur"),
            Zone(w * 0.2, w * 0.8, 1000.0, ZoneType.CLAY, "Arcilla Oeste"),
            
            # Ventilas Termales (Alta energía / Reactividad)
            Zone(w * 0.5, w * 0.5, 1200.0, ZoneType.THERMAL_VENT, "Ventila Central"),
            Zone(w * 0.1, w * 0.9, 1100.0, ZoneType.THERMAL_VENT, "Abismo Caliente"),
            Zone(w * 0.9, w * 0.1, 1300.0, ZoneType.THERMAL_VENT, "Grieta de Fuego"),
            Zone(w * 0.7, w * 0.4, 900.0, ZoneType.THERMAL_VENT, "Canal de Magma"),
        ]
        print(f"[ZONES] Gestionando {len(self.zones)} zonas (Arcilla y Ventilas).")

    def get_zone_at(self, particle_pos: np.ndarray):
        """Retorna la zona en una posición dada."""
        for zone in self.zones:
            dist_sq = np.sum((zone.pos - particle_pos)**2)
            if dist_sq < zone.radius**2:
                return zone
        return None

    def is_in_clay(self, particle_pos: np.ndarray) -> bool:
        zone = self.get_zone_at(particle_pos)
        return zone is not None and zone.type == ZoneType.CLAY

    def is_in_vent(self, particle_pos: np.ndarray) -> bool:
        zone = self.get_zone_at(particle_pos)
        return zone is not None and zone.type == ZoneType.THERMAL_VENT

_zone_manager = None

def get_zone_manager(world_size: float = 15000.0):
    global _zone_manager
    if _zone_manager is None:
        _zone_manager = ZoneManager(world_size)
    return _zone_manager
