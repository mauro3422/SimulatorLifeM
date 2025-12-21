"""
Configuración centralizada de la Interfaz de Usuario (UI) y Parámetros Visuales.
"""

from imgui_bundle import imgui

class UIConfig:
    # --- PALETA DE COLORES (RGBA) ---
    COLOR_PRIMARY = (1.0, 1.0, 0.9, 1.0)      # Blanco Cálido / Foco
    COLOR_CYAN_NEON = (0.2, 0.9, 1.0, 0.7)    # Cian Eléctrico / Estructura
    COLOR_AQUA_SUBTLE = (0.0, 0.5, 0.7, 0.4)  # Deep Aqua / Fondo
    COLOR_TEXT_HIGHLIGHT = (0.4, 1.0, 0.8, 1.0) # Verde/Cian para log
    COLOR_BOND_FORMED = (0.4, 1.0, 0.6, 1.0)   # Verde Esmeralda
    COLOR_BOND_BROKEN = (1.0, 0.4, 0.4, 1.0)   # Rojo Coral
    COLOR_CATALYSIS = (0.2, 0.8, 1.0, 1.0)     # Azul Eléctrico
    
    # --- DIMENSIONES DE PANELES ---
    PANEL_LEFT_W = 340
    PANEL_STATS_W = 480
    PANEL_STATS_H = 180
    PANEL_INSPECT_W = 360
    PANEL_INSPECT_H = 240
    LOG_H = 420
    
    # --- PARÁMETROS DE DESTACADO (RENDERER) ---
    HIGHLIGHT_RADIUS = 0.028  # Radio en NDC
    HIGHLIGHT_SEGMENTS = 16   # Calidad del círculo
    WIDTH_PRIMARY = 5.0       # Grosor átomo principal
    WIDTH_SECONDARY = 3.0     # Grosor estructura molecular
    
    # --- ESTILOS DE IMGUI ---
    WINDOW_FLAGS_STATIC = (imgui.WindowFlags_.no_move | 
                           imgui.WindowFlags_.no_resize | 
                           imgui.WindowFlags_.no_scrollbar)
    
    WINDOW_FLAGS_LOG = (imgui.WindowFlags_.no_move | 
                        imgui.WindowFlags_.no_resize | 
                        imgui.WindowFlags_.no_scrollbar)

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
