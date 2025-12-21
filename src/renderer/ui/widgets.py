import pygame

class Slider:
    def __init__(self, x, y, w, h, label, min_val, max_val, initial_val, tooltip=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.tooltip = tooltip
        
        # Posición del botón del slider
        self.button_rect = pygame.Rect(x, y, 10, h + 4)
        self.update_button_pos()
        
        self.grabbed = False
        self.hovered = False
        self.font = pygame.font.SysFont("Arial", 14)
        self.tooltip_font = pygame.font.SysFont("Arial", 12)

    def update_button_pos(self):
        ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        self.button_rect.centerx = self.rect.x + ratio * self.rect.width

    def update_val_from_mouse(self, mx):
        mx = max(self.rect.x, min(mx, self.rect.x + self.rect.width))
        ratio = (mx - self.rect.x) / self.rect.width
        self.val = self.min_val + ratio * (self.max_val - self.min_val)
        self.update_button_pos()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.button_rect.collidepoint(event.pos):
                self.grabbed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.grabbed = False
        elif event.type == pygame.MOUSEMOTION:
            # Detectar hover para el tooltip
            hitbox = self.rect.inflate(0, 40) # Detectar cerca del texto también
            self.hovered = hitbox.collidepoint(event.pos)
            
            if self.grabbed:
                self.update_val_from_mouse(event.pos[0])
                return True
        return False

    def draw(self, screen):
        # Dibujar barra fondo
        pygame.draw.rect(screen, (40, 40, 40), self.rect, border_radius=5)
        
        # Indicadores de límites (Ticks)
        pygame.draw.line(screen, (80, 80, 80), (self.rect.x, self.rect.y - 3), (self.rect.x, self.rect.bottom + 3), 1)
        pygame.draw.line(screen, (80, 80, 80), (self.rect.right, self.rect.y - 3), (self.rect.right, self.rect.bottom + 3), 1)

        # Dibujar botón
        color_btn = (255, 200, 50) if self.grabbed else (180, 180, 180)
        pygame.draw.rect(screen, color_btn, self.button_rect, border_radius=3)
        
        # Texto Label
        val_str = f"{self.val:.3f}" if self.max_val < 10 else f"{int(self.val)}"
        label_surf = self.font.render(f"{self.label}: {val_str}", True, (220, 220, 220))
        screen.blit(label_surf, (self.rect.x, self.rect.y - 18))
        
        # Dibujar Tooltip si está sobre el slider
        if self.hovered and self.tooltip:
            self._draw_tooltip(screen)

    def _draw_tooltip(self, screen):
        t_surf = self.tooltip_font.render(self.tooltip, True, (255, 255, 150))
        # Ajustar si el tooltip se sale del panel (suponiendo panel de 200px)
        t_rect = t_surf.get_rect(topleft=(self.rect.x, self.rect.y + 18))
        
        if t_rect.right > self.rect.x + 170: # Si se sale del panel a la derecha
            t_rect.right = self.rect.x + 170

        # Fondo pequeño para el tooltip
        bg_rect = t_rect.inflate(12, 8)
        pygame.draw.rect(screen, (20, 20, 20), bg_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 80, 50), bg_rect, 1, border_radius=5)
        screen.blit(t_surf, t_rect)

class Button:
    def __init__(self, x, y, w, h, text, color=(60, 60, 60)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.base_color = color
        self.hover_color = tuple(min(255, c + 30) for c in color)
        self.clicked = False
        self.hovered = False
        self.font = pygame.font.SysFont("Arial", 16)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.hovered:
                self.clicked = True
                return True
        return False

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.base_color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 2, border_radius=8)
        
        surf = self.font.render(self.text, True, (255, 255, 255))
        rect = surf.get_rect(center=self.rect.center)
        screen.blit(surf, rect)
