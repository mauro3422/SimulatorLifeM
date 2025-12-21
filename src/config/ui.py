"""
Configuración de UI
===================
Colores, dimensiones y estilos para la interfaz de usuario.
"""

from imgui_bundle import imgui


class UIConfig:
    """Constantes de configuración visual para UI."""
    
    # --- PALETA DE COLORES (RGBA) ---
    COLOR_PRIMARY = (1.0, 1.0, 0.9, 1.0)        # Blanco Cálido
    COLOR_CYAN_NEON = (0.2, 0.9, 1.0, 0.7)      # Cian Eléctrico
    COLOR_AQUA_SUBTLE = (0.0, 0.5, 0.7, 0.4)    # Deep Aqua
    COLOR_TEXT_HIGHLIGHT = (0.4, 1.0, 0.8, 1.0) # Verde/Cian
    COLOR_BOND_FORMED = (0.4, 1.0, 0.6, 1.0)    # Verde Esmeralda
    COLOR_BOND_BROKEN = (1.0, 0.4, 0.4, 1.0)    # Rojo Coral
    COLOR_CATALYSIS = (0.2, 0.8, 1.0, 1.0)      # Azul Eléctrico
    COLOR_ORANGE_COORD = (1.0, 0.8, 0.2, 1.0)   # Ámbar
    
    # --- DIMENSIONES DE PANELES ---
    PANEL_LEFT_W = 300
    PANEL_STATS_W = 480
    PANEL_STATS_H = 180
    PANEL_INSPECT_W = 360
    PANEL_INSPECT_H = 240
    LOG_H = 420
    
    # --- TIEMPO Y VELOCIDAD ---
    SPEED_TIERS = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
    BOOST_SPEED = 15.0
    
    # --- PARÁMETROS DE RENDERER ---
    HIGHLIGHT_RADIUS = 0.028
    HIGHLIGHT_SEGMENTS = 16
    WIDTH_PRIMARY = 5.0
    WIDTH_SECONDARY = 3.0
    
    # --- ESTILOS DE IMGUI ---
    WINDOW_FLAGS_STATIC = (
        imgui.WindowFlags_.no_move | 
        imgui.WindowFlags_.no_resize | 
        imgui.WindowFlags_.no_scrollbar
    )
    
    WINDOW_FLAGS_LOG = (
        imgui.WindowFlags_.no_move | 
        imgui.WindowFlags_.no_resize | 
        imgui.WindowFlags_.no_scrollbar
    )

    @staticmethod
    def apply_style():
        """Aplica estilos globales a ImGui."""
        style = imgui.get_style()
        style.window_rounding = 8.0
        style.frame_rounding = 4.0
        style.item_spacing = imgui.ImVec2(8, 10)
        style.set_color_(imgui.Col_.window_bg, (0.05, 0.05, 0.08, 0.95))
        style.set_color_(imgui.Col_.border, (0.2, 0.2, 0.3, 0.5))


class UIWidgets:
    """Widgets reutilizables para la interfaz de usuario."""

    @staticmethod
    def metric_row(label, value, color=None):
        """Dibuja una fila de métrica estandarizada."""
        imgui.table_next_row()
        imgui.table_next_column()
        imgui.text(label)
        imgui.table_next_column()
        if color:
            imgui.text_colored(color, str(value))
        else:
            imgui.text(str(value))

    @staticmethod
    def section_header(text, icon="○"):
        """Dibuja un encabezado de sección con estilo."""
        imgui.spacing()
        imgui.text_colored(UIConfig.COLOR_TEXT_HIGHLIGHT, f"{icon} {text.upper()}")
        imgui.separator()
        imgui.spacing()

    @staticmethod
    def scrollable_log(log_entries, id_str="LogScroll"):
        """Dibuja una región scrollable para logs."""
        imgui.begin_child(id_str, imgui.ImVec2(0, 0), True, imgui.WindowFlags_.always_vertical_scrollbar)
        if not log_entries:
            imgui.text_disabled("No hay eventos recientes...")
        else:
            for entry in log_entries:
                if "ENLACE" in entry:
                    imgui.text_colored(UIConfig.COLOR_BOND_FORMED, f"⚡ {entry[11:]}")
                elif "ROTURA" in entry:
                    imgui.text_colored(UIConfig.COLOR_BOND_BROKEN, f"🔥 {entry[11:]}")
                elif "CATÁLISIS" in entry:
                    imgui.text_colored(UIConfig.COLOR_CATALYSIS, f"🧬 {entry[11:]}")
                else:
                    imgui.text_disabled(f"○ {entry}")
        imgui.end_child()

    @staticmethod
    def camera_hud(camera, win_w, win_h):
        """HUD dinámico de cámara que se auto-ajusta al contenido."""
        # 1. Definir textos y medir
        text_focus = f"ENFOQUE: {camera.zoom:.2f}x"
        text_coords = f"COORDENADAS: [{camera.x:.0f}, {camera.y:.0f}]"
        text_help = "[Mouse Wheel] ZOOM  |  [Rueda Click] MOVER"
        
        size_focus = imgui.calc_text_size(text_focus)
        size_coords = imgui.calc_text_size(text_coords)
        size_help = imgui.calc_text_size(text_help)
        
        # El ancho del banner es el máximo de las líneas + padding
        padding = 40
        banner_w = max(size_focus.x, size_coords.x, size_help.x) + padding
        banner_h = 110
        
        # 2. Posicionar centrado abajo
        imgui.set_next_window_pos((win_w/2 - banner_w/2, win_h - banner_h - 25), imgui.Cond_.always)
        imgui.set_next_window_size((banner_w, banner_h), imgui.Cond_.always)
        imgui.set_next_window_bg_alpha(0.6)
        
        imgui.begin("CAMERA_HUD", None, UIConfig.WINDOW_FLAGS_STATIC | imgui.WindowFlags_.no_title_bar)
        
        # Fila 1: Zoom (Cian)
        imgui.set_cursor_pos_x((banner_w - size_focus.x) / 2)
        imgui.text_colored(UIConfig.COLOR_CYAN_NEON, text_focus)
        
        # Fila 2: Coordenadas (Ámbar)
        imgui.set_cursor_pos_x((banner_w - size_coords.x) / 2)
        imgui.text_colored(UIConfig.COLOR_ORANGE_COORD, text_coords)
        
        imgui.separator()
        
        # Fila 3: Ayuda (Gris)
        imgui.set_cursor_pos_x((banner_w - size_help.x) / 2)
        imgui.text_disabled(text_help)
        
        imgui.end()

    @staticmethod
    def speed_selector(state):
        """Selector de velocidad simplificado (Slider Interactivo)."""
        imgui.text("Escala Temporal (1.0x Óptima):")
        imgui.spacing()
        
        # --- Slider Interactivo Principal ---
        imgui.push_item_width(-1)
        changed, val = imgui.slider_float("##finetune", state.time_scale, 0.0, 15.0, "%.2fx")
        if changed:
            state.time_scale = val
            state.paused = (val == 0.0)
        imgui.pop_item_width()
        
        imgui.new_line()
        
        # Feedback de Boost / Pausa
        if state.boost_active:
            imgui.text_colored((1.0, 0.4, 0.4, 1.0), "ACELERANDO...")
            fraction = (state.time_scale) / UIConfig.BOOST_SPEED
            imgui.push_style_color(imgui.Col_.plot_histogram, (0.2, 0.9, 1.0, 1.0))
            imgui.progress_bar(fraction, imgui.ImVec2(-1, 15), f"{state.time_scale:.1f}x")
            imgui.pop_style_color()
        elif state.paused:
            imgui.text_colored((1.0, 0.4, 0.4, 1.0), "PAUSADO (Doble Tab)")
        elif state.time_scale == 1.0:
            imgui.text_colored((0.4, 1.0, 0.6, 1.0), "Velocidad Óptima (Espacio)")
        else:
            imgui.text_colored((0.4, 0.8, 1.0, 1.0), f"Velocidad Fijada: {state.time_scale:.1f}x")
