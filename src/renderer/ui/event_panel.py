"""
Panel de Eventos - QuimicPYTHON
================================
Muestra la timeline y eventos recientes de la simulación.
"""
import pygame
from src.core.context import get_context

class EventPanel:
    """Panel que muestra tiempo de simulación y eventos recientes."""
    
    def __init__(self, x, y, width=250, height=300):
        self.rect = pygame.Rect(x, y, width, height)
        self.font_title = pygame.font.SysFont("Consolas", 14, bold=True)
        self.font_time = pygame.font.SysFont("Consolas", 24, bold=True)
        self.font_event = pygame.font.SysFont("Consolas", 11)
        self.font_small = pygame.font.SysFont("Consolas", 10)
        self.visible = True
    
    def toggle(self):
        """Alterna visibilidad del panel."""
        self.visible = not self.visible
    
    def draw(self, screen):
        if not self.visible:
            return
            
        ctx = get_context()
        
        # Fondo semi-transparente
        overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        overlay.fill((20, 20, 25, 200))
        screen.blit(overlay, (self.rect.x, self.rect.y))
        
        # Borde
        pygame.draw.rect(screen, (60, 60, 80), self.rect, 2, border_radius=8)
        
        # Título
        title = self.font_title.render("⏱ TIMELINE", True, (150, 200, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))
        
        # Tiempo de simulación (grande)
        time_str = ctx.get_sim_time()
        frame_str = f"Frame: {ctx.get_sim_frame():,}"
        speed_str = f"×{ctx.timeline.speed}"
        
        time_surf = self.font_time.render(time_str, True, (100, 255, 150))
        screen.blit(time_surf, (self.rect.x + 10, self.rect.y + 30))
        
        # Velocidad
        speed_color = (255, 200, 100) if ctx.timeline.speed > 1 else (150, 150, 150)
        speed_surf = self.font_title.render(speed_str, True, speed_color)
        screen.blit(speed_surf, (self.rect.x + 130, self.rect.y + 35))
        
        # Frame count (pequeño)
        frame_surf = self.font_small.render(frame_str, True, (100, 100, 100))
        screen.blit(frame_surf, (self.rect.x + 10, self.rect.y + 60))
        
        # Controles de velocidad
        controls = "[+/-] Velocidad | [P] Pausa"
        ctrl_surf = self.font_small.render(controls, True, (80, 80, 100))
        screen.blit(ctrl_surf, (self.rect.x + 10, self.rect.y + 75))
        
        # Separador
        pygame.draw.line(screen, (50, 50, 60), 
                        (self.rect.x + 10, self.rect.y + 95),
                        (self.rect.x + self.rect.width - 10, self.rect.y + 95), 1)
        
        # Título de eventos
        events_title = self.font_title.render("📜 EVENTOS RECIENTES", True, (200, 180, 100))
        screen.blit(events_title, (self.rect.x + 10, self.rect.y + 102))
        
        # Eventos recientes
        events = ctx.get_recent_events(8)
        y_offset = 125
        
        if not events:
            no_events = self.font_event.render("(Sin eventos aún)", True, (80, 80, 80))
            screen.blit(no_events, (self.rect.x + 10, self.rect.y + y_offset))
        else:
            for event in reversed(events):  # Más recientes arriba
                # Formatear evento
                time_prefix = f"[{event.timestamp:>6}]"
                desc = event.description[:30] + "..." if len(event.description) > 30 else event.description
                
                # Color según tipo
                type_colors = {
                    'water_formed': (100, 200, 255),
                    'organic_chain': (100, 255, 100),
                    'complex_structure': (255, 200, 100),
                    'molecule_formed': (200, 200, 200),
                    'milestone': (255, 255, 100),
                }
                color = type_colors.get(event.event_type.value, (150, 150, 150))
                
                # Dibujar
                time_surf = self.font_small.render(time_prefix, True, (80, 80, 80))
                desc_surf = self.font_event.render(desc, True, color)
                
                screen.blit(time_surf, (self.rect.x + 10, self.rect.y + y_offset))
                screen.blit(desc_surf, (self.rect.x + 60, self.rect.y + y_offset))
                
                y_offset += 18
                if y_offset > self.rect.height - 20:
                    break
        
        # Estado de pausa
        if ctx.timeline.paused:
            pause_surf = self.font_time.render("⏸ PAUSA", True, (255, 100, 100))
            screen.blit(pause_surf, (self.rect.x + 50, self.rect.y + self.rect.height - 40))
