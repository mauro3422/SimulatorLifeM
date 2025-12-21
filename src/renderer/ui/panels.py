import pygame
import numpy as np
import src.config as cfg
from .widgets import Slider, Button

class ControlPanel:
    def __init__(self, x, y, config):
        self.rect = pygame.Rect(x, y, 200, config.HEIGHT)
        self.config = config
        
        # Tooltips simplificados
        tooltips = {
            "TIME": "TIEMPO: Acelera la simulación (1=lento, 10=rápido).",
            "TEMP": "CAOS: Energía térmica de las partículas.",
            "GRAV": "GRAVEDAD: Empuja todo hacia el suelo."
        }
        
        # Sliders principales (simplificados)
        self.sliders = {
            "TIME_SCALE": Slider(x + 20, y + 40, 160, 10, "Velocidad", 1, 200, config.TIME_SCALE, tooltips["TIME"]),
            "TEMPERATURE": Slider(x + 20, y + 95, 160, 10, "Caos", 0.0, 0.2, config.TEMPERATURE, tooltips["TEMP"]),
            "GRAVITY": Slider(x + 20, y + 150, 160, 10, "Gravedad", 0.0, 0.3, config.GRAVITY, tooltips["GRAV"])
        }
        
        self.btn_graph = Button(x + 20, y + 210, 160, 30, "Gráfico Energía", (100, 50, 50))
        self.btn_default = Button(x + 20, y + 250, 160, 30, "Valores Default", (50, 100, 50))
        self.btn_debug = Button(x + 20, y + 290, 160, 30, "Modo Debug", (100, 100, 20))
        self.show_graph = False
        
        # Historial de Energía
        self.history_ek = []
        self.history_ep = []
        self.max_history = 100
        
        self.font_title = pygame.font.SysFont("Arial", 18, bold=True)

    def handle_event(self, event):
        for key, slider in self.sliders.items():
            if slider.handle_event(event):
                setattr(self.config, key, slider.val)
        
        if self.btn_graph.handle_event(event):
            self.show_graph = not self.show_graph
            
        if self.btn_default.handle_event(event):
            self.config.reset_to_defaults()
            # Sincronizar sliders visualmente
            for key, slider in self.sliders.items():
                slider.val = getattr(self.config, key)
                slider.update_button_pos()
                
        if self.btn_debug.handle_event(event):
            self.config.SHOW_DEBUG = not self.config.SHOW_DEBUG

    def draw(self, screen, universe=None):
        # Fondo
        pygame.draw.rect(screen, (25, 25, 25), self.rect)
        pygame.draw.line(screen, (60, 60, 60), (self.rect.x, 0), (self.rect.x, 2000), 2)
        
        title = self.font_title.render("CONTROLES", True, (200, 200, 200))
        screen.blit(title, (self.rect.x + 20, 10))
        
        for slider in self.sliders.values():
            slider.draw(screen)
            
        self.btn_graph.draw(screen)
        self.btn_default.draw(screen)
        self.btn_debug.draw(screen)
        
        if self.show_graph and universe:
            self._update_energy_logic(universe)
            self._draw_energy_panel(screen)

    def _update_energy_logic(self, universe):
        # 1. Energía Cinética (Ek = Sum(0.5 * m * v^2))
        velocidades_sq = np.sum(universe.vel**2, axis=1)
        masas = cfg.MASAS[universe.tipos]
        ek = np.sum(0.5 * masas * velocidades_sq)
        
        # 2. Energía Potencial (Ep = Sum(0.5 * k * delta_x^2)) de los enlaces
        ep = 0
        if np.any(universe.enlaces):
            diff = universe.pos[:, np.newaxis, :] - universe.pos[np.newaxis, :, :]
            dist = np.linalg.norm(diff, axis=2)
            delta_x = dist - self.config.DIST_EQUILIBRIO
            # Usar la máscara de enlaces (triu para no duplicar)
            mask = np.triu(universe.enlaces)
            ep = np.sum(0.5 * self.config.SPRING_K * (delta_x[mask]**2))
            
        self.history_ek.append(ek)
        self.history_ep.append(ep)
        if len(self.history_ek) > self.max_history:
            self.history_ek.pop(0)
            self.history_ep.pop(0)

    def _draw_energy_panel(self, screen):
        panel_rect = pygame.Rect(self.rect.x - 250, self.rect.y + 300, 240, 150)
        pygame.draw.rect(screen, (15, 15, 15), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 50, 50), panel_rect, 2, border_radius=10)
        
        f = pygame.font.SysFont("Arial", 12)
        screen.blit(f.render("Energía Total (Termodinámica)", True, (200, 200, 200)), (panel_rect.x + 10, panel_rect.y + 5))
        
        if len(self.history_ek) < 2: return

        # Escalar gráfico
        max_val = max(max(self.history_ek), max(self.history_ep), 1)
        h_factor = 100 / max_val
        w_factor = 220 / self.max_history
        
        # Dibujar líneas
        for i in range(len(self.history_ek) - 1):
            x1 = panel_rect.x + 10 + i * w_factor
            x2 = panel_rect.x + 10 + (i + 1) * w_factor
            
            # Cinética (Rojo)
            y1_k = panel_rect.bottom - 10 - self.history_ek[i] * h_factor
            y2_k = panel_rect.bottom - 10 - self.history_ek[i+1] * h_factor
            pygame.draw.line(screen, (255, 50, 50), (x1, y1_k), (x2, y2_k), 2)
            
            # Potencial (Azul)
            y1_p = panel_rect.bottom - 10 - self.history_ep[i] * h_factor
            y2_p = panel_rect.bottom - 10 - self.history_ep[i+1] * h_factor
            pygame.draw.line(screen, (50, 100, 255), (x1, y1_p), (x2, y2_p), 2)

        # Leyenda
        screen.blit(f.render("Ek (Calor)", True, (255, 50, 50)), (panel_rect.x + 10, panel_rect.bottom - 25))
        screen.blit(f.render("Ep (Enlaces)", True, (50, 100, 255)), (panel_rect.x + 100, panel_rect.bottom - 25))

class InfoCard:
    """Muestra información científica de un átomo seleccionado."""
    def __init__(self):
        self.font_name = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_data = pygame.font.SysFont("Arial", 13)

    def draw(self, screen, atom_type):
        if atom_type is None: return
        
        data = cfg.ATOMS[atom_type]
        # Posición relativa al fondo de la pantalla
        h = cfg.sim_config.HEIGHT
        rect = pygame.Rect(10, h - 130, 280, 120)
        
        # Fondo con borde de color del elemento
        pygame.draw.rect(screen, (20, 20, 25), rect, border_radius=12)
        pygame.draw.rect(screen, data["color"], rect, 2, border_radius=12)
        
        # Título
        name_surf = self.font_name.render(f"{atom_type}: {self._get_full_name(atom_type)}", True, (255, 255, 255))
        screen.blit(name_surf, (rect.x + 12, rect.y + 8))
        
        # Subtítulo (Masa y Valencia)
        sub_text = f"Masa: {data['mass']}u | Valencias: {data['valence']}"
        sub_surf = self.font_data.render(sub_text, True, (180, 180, 180))
        screen.blit(sub_surf, (rect.x + 12, rect.y + 35))
        
        # Descripción con Wrap real
        self._draw_wrapped_text(screen, data['description'], rect.x + 12, rect.y + 55, 255)

    def _draw_wrapped_text(self, screen, text, x, y, max_width):
        words = text.split(' ')
        space_width, _ = self.font_data.size(' ')
        curr_x, curr_y = x, y
        
        for word in words:
            word_surf = self.font_data.render(word, True, (150, 150, 150))
            word_w, word_h = word_surf.get_size()
            
            if curr_x + word_w > x + max_width:
                curr_x = x
                curr_y += word_h + 2
                
            screen.blit(word_surf, (curr_x, curr_y))
            curr_x += word_w + space_width

    def _get_full_name(self, symbol):
        names = {"H": "Hidrógeno", "O": "Oxígeno", "C": "Carbono", "N": "Nitrógeno"}
        return names.get(symbol, "Desconocido")
