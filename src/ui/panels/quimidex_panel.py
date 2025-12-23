
import imgui_bundle
from imgui_bundle import imgui
import numpy as np
from src.gameplay.inventory import get_inventory
import time
from src.ui.components.periodic_widget import draw_atom_infographic, draw_molecule_infographic, get_family_color

def draw_quimidex_panel(state, open_quimidex: list):
    """
    Panel de 'Enciclopedia Molecular' (Quimidex).
    Muestra las moléculas descubiertas y la tabla de clasificación de átomos.
    """
    if not open_quimidex[0]:
        return

    # Estilo de ventana (Opaca y Oscura para máxima legibilidad)
    imgui.set_next_window_size((800, 600), imgui.Cond_.first_use_ever)
    imgui.set_next_window_bg_alpha(1.0) # Completamente opaca
    
    # Empujar estilo oscuro
    imgui.push_style_color(imgui.Col_.window_bg, (0.02, 0.02, 0.05, 1.0))
    expanded, is_open = imgui.begin("QUIMIDEX: Enciclopedia Estelar", open_quimidex[0])
    imgui.pop_style_color()
    open_quimidex[0] = is_open # Actualizar estado del toggle
    
    if expanded:
        if imgui.begin_tab_bar("quimidex_tabs"):
            
            # --- PESTAÑA 1: MOLÉCULAS ---
            if imgui.begin_tab_item("🧬 MOLÉCULAS")[0]:
                _draw_molecules_tab(state)
                imgui.end_tab_item()
                
            # --- PESTAÑA 2: ÁTOMOS (Origen Cósmico) ---
            if imgui.begin_tab_item("🌟 ÁTOMOS")[0]:
                _draw_atoms_origin_tab(state)
                imgui.end_tab_item()
                
            imgui.end_tab_bar()

    imgui.end()


def _draw_molecules_tab(state):
    """Pestaña de descubrimientos moleculares en Split-View."""
    inventory = get_inventory()
    collection = inventory.get_collection()
    
    # Filtrado: Solo conocidas (Incógnitas y Transitorias van a contadores numéricos abajo)
    known_collection = {f: d for f, d in collection.items() if d.get('name') not in ["Transitorio", "Desconocida"]}
    unknown_count = sum(1 for d in collection.values() if d.get('name') == "Desconocida")
    transitory_count = sum(1 for d in collection.values() if d.get('name') == "Transitorio")
    
    # --- COLUMNA IZQUIERDA: LISTA ---
    imgui.begin_child("mols_list_child", (240, 0), True)
    imgui.text_colored((0.1, 0.8, 1.0, 1.0), "DESCUBRIMIENTOS")
    imgui.separator()
    
    if len(known_collection) > 0:
        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.scroll_y
        if imgui.begin_table("mols_list_table", 1, flags):
            sorted_items = sorted(known_collection.items(), key=lambda x: x[1]['first_discovery'], reverse=True)
            for formula, data in sorted_items:
                imgui.table_next_row()
                imgui.table_set_column_index(0)
                
                is_selected = getattr(state, 'selected_quimidex_mol', None) == formula
                
                # Color dinámico: Manual -> Familia -> Default
                raw_col = data.get('color')
                if raw_col:
                    col_v4 = np.array(raw_col) / 255.0
                else:
                    # Usar el sistema de colores por familia
                    col_v4 = get_family_color(formula)
                
                # Nombre legible (fallback a la fórmula si no tiene nombre)
                display_name = data.get('name', formula)
                
                p = imgui.get_cursor_screen_pos()
                draw_list = imgui.get_window_draw_list()
                
                # Dibujar "pelotita" (círculo) en lugar de cuadrado, unificado con átomos
                draw_list.add_circle_filled(imgui.ImVec2(p.x + 10, p.y + 10), 4.5, imgui.get_color_u32((col_v4[0], col_v4[1], col_v4[2], 1.0)))
                
                imgui.indent(20)
                if imgui.selectable(f"{display_name}##{formula}", is_selected)[0]:
                    state.selected_quimidex_mol = formula
                imgui.unindent(20)
            imgui.end_table()
    else:
        imgui.text_disabled("Sin fórmulas estables.")
        
    imgui.spacing()
    imgui.separator()
    imgui.text_colored((1.0, 0.4, 0.4, 1.0), f"⚠ UNK: {unknown_count}")
    imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"🗑 JUNK: {transitory_count}")
    imgui.end_child()
    
    imgui.same_line()
    
    # --- COLUMNA DERECHA: INFOGRAFÍA ---
    imgui.begin_child("mol_info_child", (0, 0), True)
    selected_formula = getattr(state, 'selected_quimidex_mol', None)
    
    if selected_formula and selected_formula in collection:
        data = collection[selected_formula]
        name = data.get('name', 'Desconocida')
        
        imgui.text_colored((0.1, 0.8, 1.0, 1.0), "🧬 ANÁLISIS ESTRUCTURAL")
        imgui.separator()
        
        # Si es un agregado, mostrar información especial de conteo
        if selected_formula == "AGGREGATE_AMORPHOUS":
            imgui.text_wrapped("Se han detectado múltiples configuraciones de esta brea orgánica.")
            imgui.text_colored((0.8, 0.5, 0.2, 1.0), f"Cantidad detectada: {data.get('count', 1)}")
            imgui.spacing()
            
        draw_molecule_infographic(selected_formula, name, data)
        
        imgui.spacing()
        imgui.separator()
        if imgui.button("Reset Inventario", (imgui.get_content_region_avail().x, 0)):
             imgui.open_popup("Confirmar Reset")
    else:
        imgui.spacing()
        imgui.spacing()
        imgui.text_disabled("<- Selecciona una molécula\n   para ver su estructura.")
        
    # El popup de confirmación debe estar fuera del condicional del seleccionado pero dentro del child o panel
    if imgui.begin_popup_modal("Confirmar Reset", None, imgui.WindowFlags_.always_auto_resize)[0]:
        imgui.text("¿Estás seguro? Se perderán todos tus descubrimientos.")
        if imgui.button("SÍ, Borrar todo", (120, 0)):
            inventory.discovered_molecules = {}
            inventory.save()
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("Cancelar", (120, 0)):
            imgui.close_current_popup()
        imgui.end_popup()
        
    imgui.end_child()


def _draw_atoms_origin_tab(state):
    """Pestaña con visualización integrada de clasificación e infografía."""
    import src.config as cfg
    
    # --- UI DIVIDIDA (SPLIT VIEW) ---
    imgui.begin_child("atoms_list_child", (240, 0), True)
    imgui.text_colored((0.9, 0.7, 0.3, 1.0), "ELEMENTOS")
    imgui.separator()
    
    flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.scroll_y
    if imgui.begin_table("atomic_list_table", 1, flags):
        for name, info in cfg.ATOMS.items():
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            
            col = np.array(info['color']) / 255.0
            is_selected = getattr(state, 'selected_quimidex_atom', None) == name
            
            # Dibujar un pequeño "circulo" de color antes del nombre
            p = imgui.get_cursor_screen_pos()
            draw_list = imgui.get_window_draw_list()
            draw_list.add_circle_filled((p.x + 10, p.y + 10), 4, imgui.get_color_u32((col[0], col[1], col[2], 1.0)))
            
            imgui.indent(20)
            if imgui.selectable(name, is_selected)[0]:
                state.selected_quimidex_atom = name
            imgui.unindent(20)
            
        imgui.end_table()
    imgui.end_child()
    
    imgui.same_line()
    
    # --- COLUMNA DERECHA: INFOGRAFÍA ---
    imgui.begin_child("atom_info_child", (0, 0), True)
    selected_name = getattr(state, 'selected_quimidex_atom', None)
    
    if selected_name and selected_name in cfg.ATOMS:
        info = cfg.ATOMS[selected_name]
        imgui.text_colored((0.2, 1.0, 0.5, 1.0), "📊 DETALLE ATÓMICO")
        imgui.separator()
        
        # Dibujar el widget modular con el nombre completo
        full_name = info.get('name', selected_name)
        draw_atom_infographic(full_name, info)
    else:
        # Mensaje por defecto cuando no hay nada seleccionado
        imgui.spacing()
        imgui.spacing()
        imgui.text_disabled("<- Selecciona un elemento\n   para ver su infografía.")
        
    imgui.end_child()
