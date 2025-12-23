"""
Energy Zones System - LifeSimulator
====================================
Define áreas con diferentes niveles de energía/temperatura.
Simula ambientes como fuentes hidrotermales, océano, etc.
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from src.config.system_constants import WORLD_SIZE


@dataclass
class EnergyZone:
    """Una zona de energía en el mundo."""
    name: str
    x: float  # Centro X
    y: float  # Centro Y
    radius: float  # Radio (zona circular)
    temp_boost: float  # Incremento de temperatura (0.0 = normal, 1.0 = muy caliente)
    color: Tuple[float, float, float, float]  # RGBA para visualización
    description: str = ""


# Definición de zonas por defecto
DEFAULT_ZONES = [
    # Fuente hidrotermal central
    EnergyZone(
        name="Fuente Hidrotermal",
        x=WORLD_SIZE * 0.5,
        y=WORLD_SIZE * 0.5,
        radius=1500,
        temp_boost=0.5,  # Muy caliente
        color=(1.0, 0.3, 0.1, 0.15),  # Rojo-naranja translúcido
        description="Zona de alta energía - reacciones rápidas"
    ),
    # Fuente secundaria arriba-izquierda
    EnergyZone(
        name="Chimenea Volcánica",
        x=WORLD_SIZE * 0.25,
        y=WORLD_SIZE * 0.25,
        radius=800,
        temp_boost=0.8,  # Muy muy caliente
        color=(1.0, 0.1, 0.0, 0.2),  # Rojo intenso
        description="Fuente de energía extrema"
    ),
    # Zona fría (océano profundo)
    EnergyZone(
        name="Océano Profundo",
        x=WORLD_SIZE * 0.75,
        y=WORLD_SIZE * 0.75,
        radius=2000,
        temp_boost=-0.1,  # Más frío que el ambiente
        color=(0.1, 0.3, 0.8, 0.1),  # Azul translúcido
        description="Zona fría - moléculas se estabilizan"
    ),
]


class EnergyZoneManager:
    """Gestiona las zonas de energía del mundo."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.zones: List[EnergyZone] = DEFAULT_ZONES.copy()
    
    def get_temp_boost_at(self, x: float, y: float) -> float:
        """
        Retorna el boost de temperatura en una posición.
        Si hay múltiples zonas, suma los efectos con falloff por distancia.
        """
        total_boost = 0.0
        
        for zone in self.zones:
            dx = x - zone.x
            dy = y - zone.y
            dist = np.sqrt(dx*dx + dy*dy)
            
            if dist < zone.radius:
                # Falloff lineal hacia el borde
                factor = 1.0 - (dist / zone.radius)
                total_boost += zone.temp_boost * factor
        
        return total_boost
    
    def add_zone(self, zone: EnergyZone):
        """Agrega una zona de energía."""
        self.zones.append(zone)
    
    def clear_zones(self):
        """Limpia todas las zonas."""
        self.zones.clear()
    
    def reset_to_default(self):
        """Restaura zonas por defecto."""
        self.zones = DEFAULT_ZONES.copy()
    
    def get_zones(self) -> List[EnergyZone]:
        """Retorna lista de zonas activas."""
        return self.zones


def get_energy_zones() -> EnergyZoneManager:
    """Singleton accessor."""
    return EnergyZoneManager()
