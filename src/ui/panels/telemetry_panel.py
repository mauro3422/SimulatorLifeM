"""
Telemetry Panel - Panel de debug F3 con información de rendimiento.
"""

from imgui_bundle import imgui
from src.ui_config import UIConfig


def draw_telemetry_panel(state, n_visible_count: int, win_w: float):
    """
    Dibuja el panel de telemetría (solo visible con F3).
    
    Args:
        state: AppState instance
        n_visible_count: Número de partículas visibles
        win_w: Window width
    """
    if not state.show_debug:
        return
    
    panel_w = UIConfig.PANEL_STATS_W
    panel_h = UIConfig.PANEL_STATS_H
    
    imgui.set_next_window_pos((win_w - panel_w - 20, 20), imgui.Cond_.always)
    imgui.set_next_window_size((panel_w, panel_h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.6)
    
    imgui.begin(
        "TELEMETRÍA (F3)", 
        None, 
        imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_resize
    )
    
    imgui.text_colored((0.2, 0.8, 1.0, 1.0), "MONITOR DE SISTEMA")
    imgui.separator()
    imgui.text(f"FPS: {state.fps:.1f}")
    imgui.text(f"Átomos: {state.n_particles_val}")
    imgui.text_colored((1.0, 1.0, 0.4, 1.0), f"VisibleNodes: {n_visible_count}")
    imgui.text_disabled("Culling: Hardware-Accelerated")
    
    imgui.end()
