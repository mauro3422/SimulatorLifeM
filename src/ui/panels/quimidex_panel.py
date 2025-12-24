
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
    
    # Empujar estilo oscuro con tinte azul
    imgui.push_style_color(imgui.Col_.window_bg, (0.02, 0.04, 0.08, 1.0))
    imgui.push_style_color(imgui.Col_.title_bg_active, (0.05, 0.15, 0.30, 1.0))
    imgui.push_style_color(imgui.Col_.tab, (0.08, 0.12, 0.20, 1.0))
    imgui.push_style_color(imgui.Col_.tab_hovered, (0.15, 0.30, 0.50, 1.0))
    imgui.push_style_color(imgui.Col_.tab_selected, (0.10, 0.25, 0.45, 1.0))
    
    expanded, is_open = imgui.begin("QUIMIDEX: Enciclopedia Estelar", open_quimidex[0])
    
    open_quimidex[0] = is_open # Actualizar estado del toggle
    
    if expanded:
        if imgui.begin_tab_bar("quimidex_tabs"):
            
            # --- PESTAÑA 1: MOLÉCULAS ---
            if imgui.begin_tab_item("[M] MOLECULAS")[0]:
                _draw_molecules_tab(state)
                imgui.end_tab_item()
                
            # --- PESTAÑA 2: ÁTOMOS (Origen Cósmico) ---
            if imgui.begin_tab_item("[A] ATOMOS")[0]:
                _draw_atoms_origin_tab(state)
                imgui.end_tab_item()
                
            imgui.end_tab_bar()

    imgui.pop_style_color(5)  # Pop all 5 colors
    imgui.end()


def _draw_molecules_tab(state):
    """Pestaña de descubrimientos moleculares en Split-View con Modo Auditoría."""
    inventory = get_inventory()
    collection = inventory.get_collection()
    
    # Init state toggle
    if not hasattr(state, 'quimidex_show_audit'):
        state.quimidex_show_audit = False

    # Filtrado Inteligente
    # 1. Conocidas: Tienen nombre real y NO son categoría 'audit_candidate'
    # 2. Auditables: Categoría 'audit_candidate' o nombre placeholder
    # 3. Transitorias: "Transitorio" (Junk)

    known_collection = {}
    audit_collection = {}
    transitory_count = 0
    
    from src.config.molecules import get_molecule_entry
    
    # Filtrado y preparación (Iteramos sobre copia para evitar RuntimeError por concurrencia)
    for f, d in list(collection.items()):
        name = d.get('name', 'Desconocida')
        category = d.get('category', '').lower()
        if name in ["Transitorio", "Residuo Inestable", "Unstable Residue", "[Nombre Sugerido]", "[Suggested Name]"] or category == 'waste':
            transitory_count += 1
            continue
            
        # Detectar si es candidato de auditoría
        entry = get_molecule_entry(f)
        is_candidate = False
        if entry and entry.get("identity", {}).get("category") == "audit_candidate":
            is_candidate = True
        elif name in ["Desconocida", "[DETECTADA - SIN NOMBRE]", "[DETECTED - UNNAMED]"]:
            is_candidate = True
            
        if is_candidate:
            audit_collection[f] = d
        else:
            known_collection[f] = d
            
    # Selección de qué lista mostrar
    display_collection = audit_collection if state.quimidex_show_audit else known_collection
    
    # --- COLUMNA IZQUIERDA: LISTA ---
    imgui.begin_child("mols_list_child", (240, 0), True)
    
    # Header con Toggle
    if state.quimidex_show_audit:
        imgui.text_colored((1.0, 0.4, 0.4, 1.0), "ANTENA FORENSE")
        if imgui.small_button("<< Volver a Enciclopedia"):
            state.quimidex_show_audit = False
    else:
        imgui.text_colored((0.1, 0.8, 1.0, 1.0), "ENCICLOPEDIA")
        
    imgui.separator()
    
    if len(display_collection) > 0:
        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.scroll_y
        if imgui.begin_table("mols_list_table", 1, flags):
            # Ordenar: Más recientes primero para auditoría, cronológico inverso para enciclopedia
            sorted_items = sorted(display_collection.items(), key=lambda x: x[1]['first_discovery'], reverse=True)
            
            for formula, data in sorted_items:
                imgui.table_next_row()
                imgui.table_set_column_index(0)
                
                is_selected = getattr(state, 'selected_quimidex_mol', None) == formula
                
                # Color dinámico
                if state.quimidex_show_audit:
                    col_v4 = np.array([0.6, 0.6, 0.6]) # Gris para auditoría
                else:
                    raw_col = data.get('color')
                    if raw_col:
                        col_v4 = np.array(raw_col) / 255.0
                    else:
                        col_v4 = get_family_color(formula)
                
                display_name = data.get('name', formula)
                if state.quimidex_show_audit:
                    # En auditoría mostramos la fórmula primero para facilitar identificación visual rapida
                    display_name = f"{formula} {display_name}"
                
                p = imgui.get_cursor_screen_pos()
                draw_list = imgui.get_window_draw_list()
                
                draw_list.add_circle_filled(imgui.ImVec2(p.x + 10, p.y + 10), 4.5, imgui.get_color_u32((col_v4[0], col_v4[1], col_v4[2], 1.0)))
                
                imgui.indent(20)
                if imgui.selectable(f"{display_name}##{formula}", is_selected)[0]:
                    state.selected_quimidex_mol = formula
                imgui.unindent(20)
            imgui.end_table()
    else:
        if state.quimidex_show_audit:
            imgui.text_disabled("No hay anomalías detectadas.")
        else:
            imgui.text_disabled("Sin descubrimientos validados.")
        
    imgui.spacing()
    imgui.separator()
    
    # Footer con Contadores Interactivos
    if not state.quimidex_show_audit:
        if len(audit_collection) > 0:
            if imgui.small_button(f"⚠ AUDITORIA ({len(audit_collection)})"):
                state.quimidex_show_audit = True
            if imgui.is_item_hovered():
                imgui.set_tooltip("Ver lista de moléculas detectadas pero no clasificadas")
        else:
            imgui.text_disabled("✓ Auditoría Limpia")
            
    imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"🗑 JUNK: {transitory_count}")
    imgui.end_child()
    
    imgui.same_line()
    
    # --- COLUMNA DERECHA: INFOGRAFÍA ---
    imgui.begin_child("mol_info_child", (0, 0), True)
    selected_formula = getattr(state, 'selected_quimidex_mol', None)
    
    if selected_formula and selected_formula in collection:
        data = collection[selected_formula]
        name = data.get('name', 'Desconocida')
        
        imgui.text_colored((0.1, 0.8, 1.0, 1.0), "[#] ANALISIS ESTRUCTURAL")
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
        # Dashboard de métricas globales cuando no hay selección
        if len(collection) > 0:
            # Calcular estadísticas en tiempo real (puede optimizarse si es lento)
            most_freq_item = max(collection.items(), key=lambda item: item[1].get('count', 0))
            last_disc_item = max(collection.items(), key=lambda item: item[1].get('first_discovery', 0))
            
            imgui.spacing()
            imgui.text_colored((0.2, 0.9, 0.9, 1.0), "[*] METRICAS DEL SISTEMA")
            imgui.separator()
            imgui.spacing()
            
            imgui.text("Total Registros:")
            imgui.same_line()
            imgui.text_colored((1, 1, 0, 1), str(len(collection)))
            
            imgui.spacing()
            imgui.separator()
            
            # Seccion Ultimo Hallazgo
            imgui.spacing()
            imgui.text_colored((0.6, 0.8, 1.0, 1.0), "[>] Ultimo Detectado:")
            ld_name = last_disc_item[1].get('name', 'Desconocida')
            imgui.text(f"{ld_name}") 
            imgui.text_colored((0.5, 0.5, 0.5, 1.0), f"Fórmula: {last_disc_item[0]}")
            
            # Seccion Más Frecuente
            imgui.spacing()
            imgui.text_colored((0.6, 1.0, 0.6, 1.0), "[+] Mayor Hallazgo:")
            mf_name = most_freq_item[1].get('name', 'Desconocida')
            imgui.text(f"{mf_name}")
            imgui.text_colored((1.0, 0.8, 0.2, 1.0), f"Cantidad: {most_freq_item[1].get('count', 0)}")
            
        else:
            imgui.spacing()
            imgui.spacing()
            imgui.text_disabled("<- Inicia la simulación para\n   descubrir moléculas.")
        
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
        imgui.text_colored((0.2, 1.0, 0.5, 1.0), "[#] DETALLE ATOMICO")
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
