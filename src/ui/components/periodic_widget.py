
import imgui_bundle
from imgui_bundle import imgui
import numpy as np
import re
import time

def draw_periodic_box(draw_list, p_min, size, symbol, mass, color, name="", alpha=1.0):
    """
    Dibuja una caja estilo Tabla Periódica en las coordenadas especificadas.
    """
    p_max = (p_min[0] + size, p_min[1] + size)
    col_v4 = imgui.ImVec4(float(color[0]), float(color[1]), float(color[2]), float(alpha))
    col_bg = imgui.ImVec4(float(color[0]*0.3), float(color[1]*0.3), float(color[2]*0.3), 0.4)
    
    # Dibujar fondo y borde
    draw_list.add_rect_filled(p_min, p_max, imgui.get_color_u32(col_bg), 5.0)
    draw_list.add_rect(p_min, p_max, imgui.get_color_u32(col_v4), 5.0, 0, 2.0)
    
    # Símbolo (Posición estilo Tabla Periódica: Superior Izquierda)
    # Ajustado para que no esté 'tan al medio'
    offset_x = size * 0.15 
    text_pos = (p_min[0] + offset_x, p_min[1] + size * 0.1)
    
    imgui.push_font(imgui.get_io().fonts.fonts[0], 0.0)
    draw_list.add_text(text_pos, imgui.get_color_u32(col_v4), symbol)
    imgui.pop_font()
    
    # Masa (Subido para que no toque el borde inferior y se vea cortado)
    mass_text = f"{mass:.1f}"
    mass_pos = (p_min[0] + 8, p_min[1] + size - 25) # Subido de -18 a -25
    draw_list.add_text(mass_pos, imgui.get_color_u32((0.9, 0.9, 0.9, 0.9)), mass_text)
    
    # Nombre REMOVIDO para limpieza absoluta

def draw_property_grid(properties: dict):
    """
    Dibuja una tabla de propiedades estandarizada.
    """
    if imgui.begin_table("properties_table", 2, imgui.TableFlags_.borders_inner_v):
        for label, value in properties.items():
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text_disabled(f"{label}:")
            imgui.table_set_column_index(1)
            imgui.text(str(value))
        imgui.end_table()

def draw_atom_infographic(name, info, current_bonds=None, max_valence=None, show_origin=True):
    """
    Dibuja la infografía completa de un átomo (el 'elemento' periódico + detalles).
    """
    col = np.array(info['color']) / 255.0
    symbol = info.get('symbol', name[0].upper())
    
    imgui.begin_group()
    
    # Dibujar la caja del elemento
    draw_list = imgui.get_window_draw_list()
    p_min = imgui.get_cursor_screen_pos()
    size = 80 # Aumentado de 70 para que no se vea chico
    draw_periodic_box(draw_list, (p_min.x, p_min.y), size, symbol, info['mass'], col, name=name)
    
    # Espaciador invisible para avanzar el cursor de imgui
    imgui.dummy((size, size))
    imgui.end_group()
    
    # Mapeo de emergencia para Z si falta en el JSON
    z_map = {"H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
             "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18}
    atomic_number = info.get('atomic_number', z_map.get(symbol, '??'))

    imgui.same_line(offset_from_start_x=size + 25.0)
    imgui.begin_group()
    
    # Nombre en GRANDE y Blanco
    imgui.push_font(imgui.get_io().fonts.fonts[0], 0.0) # Podríamos usar una fuente más grande aquí si existiera
    imgui.text_colored((1, 1, 1, 1), f"{name.upper()}")
    imgui.pop_font()
    
    # Subtítulo con Símbolo y Z
    imgui.text_disabled(f"[{symbol}] Numero Atómico: {atomic_number}")
    
    # Estado de valencia si se proporciona
    if current_bonds is not None and max_valence is not None:
        if current_bonds >= max_valence:
            imgui.text_colored((0.4, 1.0, 0.4, 1.0), "● SATURADO")
        else:
            imgui.text_colored((1.0, 1.0, 0.4, 1.0), f"○ ENLACES: {current_bonds}/{max_valence}")
    imgui.end_group()
    
    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    
    # Propiedades obligatorias (extraídas del JSON del sistema)
    props = {
        "Electronegatividad": f"{info['electronegativity']:.2f}",
        "Radio VdW": f"{info.get('radius', 1.0)*100:.0f} pm",
        "Masa Atómica": f"{info['mass']:.2f} u",
        "Valencia Máx.": f"{info['valence']}"
    }
    draw_property_grid(props)
    
    imgui.spacing()
    imgui.text_colored((col[0], col[1], col[2], 0.8), "DESCRIPCIÓN")
    imgui.text_wrapped(info['description'])
    
    # Origen Estelar (Opcional)
    origin = info.get('origin')
    if origin and show_origin:
        imgui.spacing()
        imgui.text_colored((0.9, 0.7, 0.3, 1.0), f"✨ ORIGEN: {origin.get('source', '?')}")
        imgui.text_disabled(f"Proceso: {origin.get('process', '?')}")
        imgui.text_disabled(f"Abundancia: {origin.get('abundance', '?')}")

def draw_molecule_box(draw_list, p_min, size, formula, name, color=(0.1, 0.8, 1.0), alpha=1.0):
    """
    Dibuja una caja visual para una molécula (estilo similar a los átomos).
    """
    p_max = (p_min[0] + size, p_min[1] + size)
    col_v4 = imgui.ImVec4(float(color[0]), float(color[1]), float(color[2]), float(alpha))
    col_bg = imgui.ImVec4(float(color[0]*0.2), float(color[1]*0.2), float(color[2]*0.2), 0.6)
    
    # Dibujar fondo hexagonal (simulado) o caja redondeada
    draw_list.add_rect_filled(p_min, p_max, imgui.get_color_u32(col_bg), 10.0)
    draw_list.add_rect(p_min, p_max, imgui.get_color_u32(col_v4), 10.0, 0, 2.0)
    
    # Fórmula (Con recorte estricto para que NUNCA se salga de la caja)
    # Definir area de recorte (la propia caja)
    imgui.push_clip_rect(p_min, p_max, True)
    
    text_pos = (p_min[0] + 8, p_min[1] + size*0.4)
    imgui.push_font(imgui.get_io().fonts.fonts[0], 0.0)
    draw_list.add_text(text_pos, imgui.get_color_u32(col_v4), formula)
    imgui.pop_font()
    
    imgui.pop_clip_rect()
    
    # Nombre REMOVIDO de la caja porque ya sale a la derecha y se corta abajo

def get_family_color(formula, default_color=(0.1, 0.6, 1.0, 1.0)):
    """
    Retorna un color estándar basado en la familia química de la fórmula.
    """
    if not formula: return default_color
    
    # Prioridad: Silicatos > Azufradas > Fosforadas > Nitrogenadas > Orgánicas
    if 'Si' in formula: return (0.4, 0.5, 0.7, 1.0) # Gris Azulado (Silicatos)
    if 'S' in formula:  return (0.9, 0.9, 0.1, 1.0) # Amarillo (Azufradas)
    if 'P' in formula:  return (1.0, 0.5, 0.1, 1.0) # Naranja (Fosforadas)
    if 'N' in formula:  return (0.2, 0.4, 1.0, 1.0) # Azul (Nitrogenadas)
    if 'C' in formula:  return (0.1, 0.8, 1.0, 1.0) # Cyan (Orgánicas)
    
    return default_color

def draw_molecule_infographic(formula, name, data):
    """
    Dibuja una infografía enciclopédica detallada de una molécula en el Quimidex.
    """
    from imgui_bundle import imgui
    from src.config.molecules import get_molecule_entry
    
    # Obtener entrada rica de la base de datos centralizada
    entry = get_molecule_entry(formula)
    
    imgui.begin_group()
    draw_list = imgui.get_window_draw_list()
    p_min = imgui.get_cursor_screen_pos()
    size = 80 # Unificado con átomos
    
    # Extraer metadatos con seguridad
    if entry:
        e_id = entry["identity"]
        name = e_id["names"].get("es", name)
        category = e_id["category"]
        f_color = e_id.get("family_color", [200, 200, 200])
        lore = entry.get("lore", {})
        gameplay = entry.get("gameplay", {})
    else:
        # Fallback para moléculas no registradas aún
        category = data.get('category', 'Estable')
        f_color = [int(c*255) for c in get_family_color(formula)[:3]]
        # Si no tiene descripción en data, usamos un fallback narrativo
        desc = data.get('description') or data.get('lore', {}).get('origin_story', 'Sin descripción científica disponible en los registros actuales.')
        lore = {"origin_story": desc}
        gameplay = {}

    color_vec = [c/255.0 for c in f_color] + [1.0]
    
    # Caja visual de la molécula
    draw_molecule_box(draw_list, (p_min.x, p_min.y), size, formula, name, f_color)
    imgui.dummy((size, size))
    imgui.end_group()
    
    # Título y Info básica a la derecha
    imgui.same_line(offset_from_start_x=115.0)
    imgui.begin_group()
    
    imgui.push_font(imgui.get_io().fonts.fonts[0], 0.0)
    imgui.text_colored((1, 1, 1, 1), name.upper())
    imgui.pop_font()
    
    imgui.text_disabled(f"Fórmula: {formula} | {category.upper()}")
    imgui.end_group()
    
    imgui.spacing()
    imgui.separator()
    
    # --- SECCIÓN ENCICLOPÉDICA ---
    imgui.spacing()
    
    # 1. Historia y Origen
    imgui.text_colored(imgui.ImVec4(0.7, 0.7, 0.7, 1.0), "HISTORIA Y ORIGEN")
    imgui.push_text_wrap_pos(imgui.get_content_region_avail().x)
    imgui.text(lore.get("origin_story", "No hay datos históricos disponibles."))
    imgui.pop_text_wrap_pos()
    
    # 2. Contexto Biológico (si existe)
    bio = lore.get("biological_presence", "")
    if bio:
        imgui.spacing()
        imgui.text_colored(imgui.ImVec4(0.2, 0.8, 0.2, 1.0), "CONFLUENCIA BIOLÓGICA")
        imgui.push_text_wrap_pos(imgui.get_content_region_avail().x)
        imgui.text(bio)
        imgui.pop_text_wrap_pos()

    # 3. Hitos (si existen)
    milestones = gameplay.get("milestones", [])
    if milestones:
        imgui.spacing()
        imgui.text_colored(imgui.ImVec4(1.0, 0.8, 0.2, 1.0), "HITOS ALCANZADOS")
        for ms in milestones:
            imgui.bullet()
            imgui.text_wrapped(ms)
            
    imgui.spacing()
    imgui.separator()
    
    # Propiedades técnicas extra
    import re
    if '?' in formula:
        atoms_text = "Variante"
    else:
        # Capturar el número después de cada elemento, o asumir 1 si no está (ej: CH4 -> C1H4)
        atoms_count = sum(int(n if n else 1) for n in re.findall(r'[A-Z][a-z]?(\d*)', formula))
        atoms_text = str(atoms_count)
    
    props = {
        "Hallazgos": str(data.get('count', data.get('discovery_count', 1))),
        "Átomos": atoms_text,
        "Puntos": str(gameplay.get("discovery_points", 10)) + " pts"
    }
    draw_property_grid(props)
