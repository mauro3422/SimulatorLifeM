"""
Inspector Panel - Panel de inspección de átomos y moléculas.
"""

import numpy as np
from imgui_bundle import imgui
from src.ui_config import UIConfig
import src.config as cfg


def draw_inspector_panel(state, atom_types_field, win_h: float):
    """
    Dibuja el panel de inspección molecular.
    
    Args:
        state: AppState instance
        atom_types_field: Referencia al campo Taichi de tipos de átomo
        win_h: Window height
    """
    if state.selected_idx < 0:
        return
    
    panel_w = UIConfig.PANEL_INSPECT_W
    panel_h = UIConfig.PANEL_INSPECT_H
    
    imgui.set_next_window_pos((20, win_h - panel_h - 20), imgui.Cond_.always)
    imgui.set_next_window_size((panel_w, panel_h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.9)
    
    imgui.begin("INSPECTOR", None, UIConfig.WINDOW_FLAGS_STATIC)
    
    # Obtener datos del átomo seleccionado
    a_type = atom_types_field[state.selected_idx]
    name = cfg.TIPOS_NOMBRES[a_type]
    info = cfg.ATOMS[name]
    col = np.array(info['color']) / 255.0
    
    imgui.text_colored((col[0], col[1], col[2], 1.0), f"ÁTOMO: {name} (#{state.selected_idx})")
    imgui.separator()
    
    if not state.selected_mol:
        _draw_atom_info(info)
    else:
        _draw_molecule_info(state)

    imgui.spacing()
    if imgui.button("CERRAR INSPECTOR", imgui.ImVec2(-1, 0)):
        state.selected_idx = -1
        state.selected_mol = []
    
    imgui.end()


def _draw_atom_info(info: dict):
    """Dibuja información de un átomo individual."""
    imgui.text(f"Masa: {info['mass']} u")
    imgui.text(f"Valencia: {info['valence']}")
    imgui.text(f"Electroneg: {info['electronegativity']}")
    imgui.spacing()
    imgui.text_wrapped(f"Info: {info['description']}")
    imgui.spacing()
    imgui.text_colored((0.2, 0.8, 1.0, 1.0), "ENLACES ADYACENTES")
    imgui.separator()
    imgui.spacing()
    imgui.text_colored((0.4, 1.0, 0.4, 1.0), "Clic de nuevo -> Expandir Molécula")


def _draw_molecule_info(state):
    """Dibuja información de una molécula."""
    formula = state.get_formula(state.selected_mol)
    imgui.text_colored(UIConfig.COLOR_CYAN_NEON, "SISTEMA MOLECULAR DINÁMICO")
    imgui.separator()
    imgui.text("Fórmula Química:")
    imgui.text_colored((1.0, 1.0, 1.0, 1.0), f"  {formula}")
    imgui.spacing()
    imgui.text(f"Total de Átomos: {len(state.selected_mol)}")
    imgui.spacing()
    imgui.text_disabled("(Clic para volver a inspección simple)")
    imgui.text_disabled("Estructura resaltada en Cian Eléctrico.")
