import numpy as np

class Camera:
    def __init__(self, world_size, window_width, window_height):
        """
        Sistema de Cámara centralizado.
        
        Args:
            world_size (float): Tamaño del mundo cuadrado (ej. 5000).
            window_width (int): Ancho de la ventana de SO (ej. 800).
            window_height (int): Alto de la ventana de SO (ej. 500).
        """
        self.world_size = world_size
        self.window_width = window_width
        self.window_height = window_height
        # Configuración de Viewport
        self.aspect_ratio = window_width / window_height
        self.sim_ratio = self.aspect_ratio # Reemplaza el 1.25 hardcoded
        
        # Estado de la cámara (Centro en coordenadas de Mundo)
        self.x = world_size / 2.0
        self.y = world_size / 2.0
        self.zoom = 4.15
        
        # Límites estrictos según preferencia del usuario
        self.min_zoom = 4.15
        self.max_zoom = 30.0
        
        # Configuración de Viewport (UI ocupa el 25% derecho)
        # La simulación se renderiza en [0.0, 0.75] de la pantalla
        # Configuración de Viewport (UI ocupa el 25% derecho)
        # La simulación se renderiza en [0.0, 0.75] de la pantalla
        # PERO, el usuario puede ver detrás del panel (abajo).
        # Además, el centro visual está en 0.375.
        # Distancia al borde derecho (1.0) es 1.0 - 0.375 = 0.625.
        # Distancia al borde izquierdo (0.0) es 0.375.
        # Para cubrir todo simétricamente, necesitamos radio 0.625 -> Ancho 1.25
        
    def update_aspect(self, width, height):
        """Actualiza el aspect ratio y aplica límites."""
        if height == 0: return
        self.window_width = width
        self.window_height = height
        self.aspect_ratio = width / height
        self.sim_ratio = self.aspect_ratio
        
        # Aplicar límites al zoom actual
        self.zoom = max(self.min_zoom, min(self.zoom, self.max_zoom))
        self.clamp_position()

    def update_zoom(self, factor):
        """Aplica un factor multiplicativo al zoom (clamped)."""
        self.zoom *= factor
        self.zoom = max(self.min_zoom, min(self.zoom, self.max_zoom))
        self.clamp_position()

    def set_zoom(self, value):
        """Establece un valor absoluto de zoom."""
        self.zoom = max(self.min_zoom, min(value, self.max_zoom))
        self.clamp_position()

    def move(self, dx, dy):
        """Mueve la cámara en unidades de Mundo."""
        self.x += dx
        self.y += dy
        self.clamp_position()
        
    def center(self):
        """Resetea posición y zoom."""
        self.x = self.world_size / 2.0
        self.y = self.world_size / 2.0
        self.zoom = self.min_zoom

    def get_visible_area(self):
        """
        Retorna (width, height) del área visible en Unidades de Mundo.
        Basado en que el alto de la pantalla es 1.0 normalized = 1.0 * WORLD_SIZE / zoom?
        
        En el kernel 'normalize_positions_with_zoom':
        rel_y = (pos - cy) * z
        norm_y = 1.0 - (rel_y / WORLD_SIZE + 0.5)
        
        Para cubrir 0..1 en norm_y:
        Delta_norm = 1.0
        Delta_rel / WORLD_SIZE = 1.0  => Delta_rel = WORLD_SIZE
        Delta_world * z = WORLD_SIZE => Delta_world = WORLD_SIZE / z
        
        Por lo tanto:
        Visible Height = WORLD_SIZE / zoom
        Visible Width (Screen) = Visible Height * AspectRatio
        Pero... el sim_ratio afecta.
        
        La pantalla sim es 0..0.75 en normalized X.
        Entonces visible width es 0.75 * WORLD_SIZE / zoom.
        """
        vis_h = self.world_size / self.zoom
        vis_w = (self.world_size * self.sim_ratio) / self.zoom
        return vis_w, vis_h

    def clamp_position(self):
        """Evita que la cámara se salga de los bordes del mundo."""
        vis_w, vis_h = self.get_visible_area()
        
        min_x, max_x = vis_w / 2, self.world_size - vis_w / 2
        min_y, max_y = vis_h / 2, self.world_size - vis_h / 2
        
        # Si el zoom es muy lejano (veo más que el mundo), centro la cámara
        if min_x > max_x: self.x = self.world_size / 2
        else: self.x = max(min_x, min(self.x, max_x))
            
        if min_y > max_y: self.y = self.world_size / 2
        else: self.y = max(min_y, min(self.y, max_y))

    def get_culling_bounds(self, margin=0.0):
        """
        Retorna [min_x, min_y, max_x, max_y] con margen.
        Usado para decidir qué partículas simular.
        """
        vis_w, vis_h = self.get_visible_area()
        
        min_x = (self.x - vis_w / 2) - margin
        max_x = (self.x + vis_w / 2) + margin
        min_y = (self.y - vis_h / 2) - margin
        max_y = (self.y + vis_h / 2) + margin
        
        return [min_x, min_y, max_x, max_y]

    def get_render_params(self):
        """Retorna parámetros para enviar a GPU (zoom, cx, cy)."""
        return self.zoom, self.x, self.y
        
    def get_screen_bounds(self):
        """
        Retorna los límites del mundo que están EXACTAMENTE en los bordes de la pantalla
        [min_x, min_y, max_x, max_y].
        Usa el offset 0.375 para la izquierda y 0.625 para la derecha.
        """
        # Ancho a la izquierda del centro (0.375 de la pantalla)
        w_left = (0.375 / self.zoom) * self.world_size
        # Ancho a la derecha del centro (0.625 de la pantalla)
        w_right = (0.625 / self.zoom) * self.world_size
        # Alto arriba/abajo del centro (0.5 de la pantalla cada uno)
        h_half = (0.5 / self.zoom) * self.world_size
        
        return [
            self.x - w_left,
            self.y - h_half,
            self.x + w_right,
            self.y + h_half
        ]

    def get_dist_to_borders(self):
        """
        Retorna distancias a los bordes del mundo desde los bordes de la PANTALLA [L, R, T, B].
        """
        sb = self.get_screen_bounds()
        
        d_left = sb[0]
        d_right = self.world_size - sb[2]
        d_top = self.world_size - sb[3]
        d_bottom = sb[1]
        
        return d_left, d_right, d_top, d_bottom

    def get_culling_margins(self, margin_px):
        """
        Retorna la distancia entre el borde de la pantalla (Azul) 
        y el borde de simulación (Verde) en unidades de mundo.
        """
        sb = self.get_screen_bounds()
        cb = self.get_culling_bounds(margin_px)
        
        # Margen = Sim_Bound - Screen_Bound (en valor absoluto de lejanía)
        m_left = sb[0] - cb[0]
        m_right = cb[2] - sb[2]
        m_top = cb[3] - sb[3]
        m_bottom = sb[1] - cb[1]
        
        return m_left, m_right, m_top, m_bottom

    def screen_to_world(self, screen_x, screen_y, window_w, window_h):
        """
        Convierte coordenadas de pantalla (0..W, 0..H) a coordenadas de Mundo.
        NOTA: Sincronizado con ParticleRenderer que invierte Y.
        """
        vis_w, vis_h = self.get_visible_area()
        world_x = self.x + (screen_x / window_w - 0.5) * vis_w
        # Invertimos el signo de Y para coincidir con el renderer
        world_y = self.y + (screen_y / window_h - 0.5) * vis_h
        return world_x, world_y
