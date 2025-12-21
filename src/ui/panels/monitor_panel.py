"""
Monitor Panel - Panel de monitoreo de actividad molecular.
"""

from imgui_bundle import imgui
from src.config import UIConfig, UIWidgets


def draw_monitor_panel(state, show_debug: bool, win_w: float):
    """
    Dibuja el panel de monitoreo de actividad molecular.
    
    Args:
        state: AppState instance
        show_debug: Si el panel de debug está visible
        win_w: Window width
    """
    panel_w = UIConfig.PANEL_STATS_W
    panel_h = UIConfig.PANEL_STATS_H
    log_h = UIConfig.LOG_H
    
    # Posición dinámica dependiendo de si telemetría está visible
    y_pos = 20 if not show_debug else panel_h + 40
    
    imgui.set_next_window_pos((win_w - panel_w - 20, y_pos), imgui.Cond_.always)
    imgui.set_next_window_size((panel_w, log_h), imgui.Cond_.always)
    imgui.begin("MONITOR DE ACTIVIDAD MOLECULAR", None, UIConfig.WINDOW_FLAGS_LOG)
    
    # Métricas de Evolución
    UIWidgets.section_header("MÉTRICAS DE EVOLUCIÓN", "📊")
    
    imgui.begin_table("StatsInfo", 2)
    UIWidgets.metric_row("Enlaces Formados:", state.stats['bonds_formed'], UIConfig.COLOR_BOND_FORMED)
    UIWidgets.metric_row("Enlaces Rotos:", state.stats['bonds_broken'], UIConfig.COLOR_BOND_BROKEN)
    UIWidgets.metric_row("Transiciones Energ.:", state.stats['tunnels'], (0.8, 0.6, 1.0, 1.0))
    imgui.end_table()
    
    # Bitácora de Eventos
    UIWidgets.section_header("BITÁCORA DE EVENTOS", "📝")
    UIWidgets.scrollable_log(state.event_log)
    
    imgui.end()
