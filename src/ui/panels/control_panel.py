"""
Control Panel - Panel izquierdo de control de simulación.
"""

from imgui_bundle import imgui
from src.ui_config import UIConfig, UIWidgets
import src.config as cfg


def draw_control_panel(state, physics_controls: dict, win_h: float):
    """
    Dibuja el panel de control izquierdo.
    
    Args:
        state: AppState instance
        physics_controls: Dict con referencias a campos Taichi:
            {'gravity', 'friction', 'temperature', 'prob_enlace_base', 
             'rango_enlace_max', 'dist_rotura'}
        win_h: Window height
    """
    panel_w = UIConfig.PANEL_LEFT_W
    panel_h = min(680, win_h * 0.85)
    
    imgui.set_next_window_pos((20, 20), imgui.Cond_.always)
    imgui.set_next_window_size((panel_w, panel_h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.75)
    
    imgui.begin(
        "CENTRO DE CONTROL", 
        None, 
        imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_resize | imgui.WindowFlags_.always_vertical_scrollbar
    )
    
    # Header
    imgui.push_style_color(imgui.Col_.text, (0.4, 1.0, 0.8, 1.0))
    imgui.text("SISTEMA DE GESTIÓN EVOLUTIVA (CHONPS)")
    imgui.pop_style_color()
    imgui.separator()
    
    # Controles de Tiempo
    UIWidgets.speed_selector(state)
    
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # Propiedades Físicas
    _draw_physics_section(physics_controls, panel_w)
    
    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    
    # Gestión de Mundo
    _draw_world_section(state, physics_controls, panel_w)
    
    imgui.end()


def _draw_physics_section(physics_controls: dict, panel_w: float):
    """Dibuja la sección de propiedades físicas."""
    if imgui.collapsing_header("PROPIEDADES FÍSICAS", imgui.TreeNodeFlags_.default_open):
        imgui.push_item_width(panel_w * 0.6)
        
        gravity = physics_controls['gravity']
        friction = physics_controls['friction']
        temperature = physics_controls['temperature']
        
        changed_g, new_g = imgui.slider_float("Gravedad", gravity[None], -10.0, 10.0, "%.3f")
        if changed_g: 
            gravity[None] = new_g
        
        changed_f, new_f = imgui.slider_float("Fricción", friction[None], 0.8, 1.0, "%.3f")
        if changed_f: 
            friction[None] = new_f
        
        changed_t, new_t = imgui.slider_float("Agitación", temperature[None], 0.0, 1.0, "%.3f")
        if changed_t: 
            temperature[None] = new_t
        
        imgui.pop_item_width()


def _draw_world_section(state, physics_controls: dict, panel_w: float):
    """Dibuja la sección de gestión de mundo."""
    UIWidgets.section_header("Mundo", "🌍")
    
    changed_real, val_real = imgui.checkbox("Modo Realismo (Científico)", cfg.sim_config.REALISM_MODE)
    if changed_real:
        cfg.sim_config.toggle_realism()
        # Sincronizar cambios inmediatos a la GPU
        physics_controls['prob_enlace_base'][None] = cfg.sim_config.PROB_ENLACE_BASE
        physics_controls['rango_enlace_max'][None] = cfg.sim_config.RANGO_ENLACE_MAX
        physics_controls['dist_rotura'][None] = cfg.sim_config.DIST_ROTURA
        print(f"[UI] Modo Realismo: {'ON' if cfg.sim_config.REALISM_MODE else 'OFF'}")

    imgui.spacing()
    
    if imgui.button("RESTABLECER CÁMARA", (panel_w - 30, 35)):
        state.camera.center()
    
    if imgui.button("REINICIAR ÁTOMOS", (panel_w - 30, 35)):
        state.init_world()
