"""
UI Panels Module - Paneles de ImGui para la interfaz de usuario.
"""

from src.ui.panels.control_panel import draw_control_panel
from src.ui.panels.telemetry_panel import draw_telemetry_panel
from src.ui.panels.monitor_panel import draw_monitor_panel
from src.ui.panels.inspector_panel import draw_inspector_panel

__all__ = [
    'draw_control_panel',
    'draw_telemetry_panel', 
    'draw_monitor_panel',
    'draw_inspector_panel'
]
