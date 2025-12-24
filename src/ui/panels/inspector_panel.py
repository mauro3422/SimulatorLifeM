"""
Inspector Panel - Panel de inspección de átomos y moléculas.
"""

import numpy as np
from imgui_bundle import imgui
from src.config import UIConfig
import src.config as cfg
from src.ui.components.periodic_widget import draw_atom_infographic, draw_molecule_infographic


def draw_inspector_panel(state, synced_data, win_h: float):
    """
    Dibuja el panel de inspección molecular mejorado.
    Optimización V4: Usa arrays sincronizados para evitar latencia GPU.
    """
    if state.selected_idx < 0 or synced_data is None:
        return
        
    # Extraer arrays locales (Numpy)
    atom_types_np = synced_data.get('atom_types')
    num_enlaces_np = synced_data.get('num_enlaces')
    
    if atom_types_np is None or num_enlaces_np is None:
        # Fallback si no hay sync este frame (raro si hay selección)
        return
    
    panel_w = UIConfig.PANEL_INSPECT_W
    panel_h = UIConfig.PANEL_INSPECT_H
    
    # Obtener datos del átomo seleccionado sin bloquear GPU
    a_type = int(atom_types_np[state.selected_idx])
    name = cfg.TIPOS_NOMBRES[a_type]
    info = cfg.ATOMS[name]
    col = np.array(info['color']) / 255.0
    current_bonds = int(num_enlaces_np[state.selected_idx])
    max_valence = info['valence']
    
    # Posición y tamaño del panel
    imgui.set_next_window_pos((20, win_h - panel_h - 20), imgui.Cond_.always)
    imgui.set_next_window_size((panel_w, panel_h), imgui.Cond_.always)
    
    # Color de fondo dinámico basado en átomo (oscurecido)
    bg_col = (float(col[0] * 0.15), float(col[1] * 0.15), float(col[2] * 0.15), 0.95)
    title_col = (float(col[0] * 0.3), float(col[1] * 0.3), float(col[2] * 0.3), 1.0)
    imgui.push_style_color(imgui.Col_.window_bg, bg_col)
    imgui.push_style_color(imgui.Col_.title_bg_active, title_col)
    
    full_name = info.get('name', name).upper()
    imgui.begin(f"[+] {full_name}", None, UIConfig.WINDOW_FLAGS_STATIC)
    
    # Header con nombre del átomo
    imgui.text_colored((col[0], col[1], col[2], 1.0), f">> {full_name}")
    imgui.same_line()
    imgui.text_disabled(f"(ID: {state.selected_idx})")
    
    if state.selected_idx == state.player_idx:
        imgui.same_line()
        imgui.text_colored(UIConfig.COLOR_GREEN_NEON, " [TÚ]")
    
    imgui.separator()
    
    if not state.selected_mol:
        _draw_atom_info(info, current_bonds, max_valence, col)
    else:
        _draw_molecule_info_v4(state, atom_types_np)

    imgui.spacing()
    if imgui.button("✕ CERRAR", imgui.ImVec2(-1, 0)):
        state.selected_idx = -1
        state.selected_mol = []
    
    imgui.pop_style_color(2)
    imgui.end()


def _draw_atom_info(info: dict, current_bonds: int, max_valence: int, col):
    """
    Dibuja información de un átomo usando el widget modular.
    """
    draw_atom_infographic(info['name'], info, current_bonds, max_valence, show_origin=False)
    
    imgui.spacing()
    imgui.spacing()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "[i] Clic de nuevo -> Ver molecula")


from src.gameplay.inventory import get_inventory
from src.config.molecules import get_molecule_name

def _draw_molecule_info_v4(state, atom_types_np):
    """Dibuja información BÁSICA de una molécula (sin lore detallado)."""
    from src.ui.components.periodic_widget import draw_molecule_box, get_family_color
    
    # Obtain raw formula (e.g., H2O1)
    raw_formula = state.get_formula(state.selected_mol)
    # Identify Name
    mol_name = get_molecule_name(raw_formula)
    
    # Obtener datos reales del inventario
    inventory = get_inventory()
    collection = inventory.get_collection()
    
    # Consultar inventario (redirigir si es agregado)
    search_key = raw_formula
    if mol_name == "Agregado Orgánico Amorfo":
        search_key = "AGGREGATE_AMORPHOUS"
    
    inv_data = collection.get(search_key, {})
    
    # Si en el inventario tiene un nombre mejor (no genérico), usar ese
    display_name = inv_data.get('name', mol_name)
    category = inv_data.get('category', 'Estable')
    count = inv_data.get('count', 1)
    
    # --- VISTA SIMPLIFICADA ---
    draw_list = imgui.get_window_draw_list()
    p_min = imgui.get_cursor_screen_pos()
    size = 70
    
    # Obtener color de familia
    f_color = get_family_color(raw_formula)[:3]
    f_color = [int(c * 255) for c in f_color]
    
    # Dibujar caja de molécula
    draw_molecule_box(draw_list, (p_min.x, p_min.y), size, raw_formula, display_name, f_color)
    imgui.dummy((size, size))
    
    # Info a la derecha
    imgui.same_line(offset_from_start_x=90.0)
    imgui.begin_group()
    imgui.text_colored((1, 1, 1, 1), display_name.upper())
    imgui.text_disabled(f"Fórmula: {raw_formula}")
    imgui.text_disabled(f"Estado: {category}")
    imgui.text(f"Hallazgos: {count}")
    imgui.end_group()
    
    imgui.spacing()
    imgui.separator()
    
    # Listado de Átomos
    imgui.spacing()
    imgui.text_disabled("COMPOSICIÓN:")
    
    # Contador rápido de tipos
    unique, counts = np.unique(atom_types_np[state.selected_mol], return_counts=True)
    for t_idx, c in zip(unique, counts):
        a_name = cfg.TIPOS_NOMBRES[int(t_idx)]
        a_info = cfg.ATOMS[a_name]
        a_col = np.array(a_info['color']) / 255.0
        imgui.text_colored((a_col[0], a_col[1], a_col[2], 1.0), f"  {a_name}:")
        imgui.same_line()
        imgui.text(f" {c}")
    
    imgui.spacing()
    imgui.separator()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "[i] Presiona [P] -> Enciclopedia completa")

