import pygame
import numpy as np
import src.config as cfg

def limpiar_pantalla(screen):
    screen.fill(cfg.sim_config.BG_COLOR)

def dibujar_universo(screen, universe, colision_mask=None):
    """Dibuja todo el estado del universo."""
    # 0. Dibujar Cuadrícula si está activada
    if cfg.sim_config.SHOW_GRID:
        dibujar_cuadricula(screen)

    # 1. Dibujar Enlaces
    pares = np.argwhere(np.triu(universe.enlaces))
    for i, j in pares:
        p1 = (int(universe.pos[i, 0]), int(universe.pos[i, 1]))
        p2 = (int(universe.pos[j, 0]), int(universe.pos[j, 1]))
        pygame.draw.line(screen, (80, 80, 180), p1, p2, 2)

    # 2. Dibujar Partículas (Ordenadas por tamaño: Grandes al fondo)
    indices_ordenados = np.argsort(universe.radios_asignados)[::-1]
    
    for i in indices_ordenados:
        x, y = int(universe.pos[i, 0]), int(universe.pos[i, 1])
        r = int(universe.radios_asignados[i])
        
        # Color base o rojo si hay colisión (Debug)
        color = tuple(universe.colores_asignados[i])
        if cfg.sim_config.SHOW_DEBUG and colision_mask is not None:
            if np.any(colision_mask[i]):
                pygame.draw.circle(screen, (255, 0, 0), (x, y), r + 2, 2) # Outline rojo

        pygame.draw.circle(screen, color, (x, y), r)
        
        # Opcional: Centros blancos para visibilidad (lo que el usuario notó)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 2)
    
    # 3. Dibujar UI (Estadísticas)
    dibujar_estadisticas(screen, universe)

def dibujar_cuadricula(screen):
    """Dibuja una malla sutil de fondo para referencia espacial."""
    c = cfg.sim_config
    step = 50
    color = (25, 25, 25)
    limit_x = c.WIDTH - 200
    
    for x in range(0, limit_x + 1, step):
        pygame.draw.line(screen, color, (x, 0), (x, c.HEIGHT))
    for y in range(0, c.HEIGHT + 1, step):
        pygame.draw.line(screen, color, (0, y), (limit_x, y))

def dibujar_estadisticas(screen, universe):
    """Muestra información en tiempo real sobre la química del sistema."""
    if not pygame.font.get_init():
        pygame.font.init()
    
    fuente = pygame.font.SysFont("Arial", 18)
    
    enlaces_totales = np.sum(universe.enlaces) // 2
    manos_libres_totales = int(np.sum(universe.manos_libres))
    
    textos = [
        f"Átomos: {len(universe.pos)}",
        f"Enlaces: {enlaces_totales}",
        f"Manos Libres: {manos_libres_totales}",
        "Presiona 'R' para Resetear"
    ]
    
    for i, texto in enumerate(textos):
        surf = fuente.render(texto, True, (200, 200, 200))
        screen.blit(surf, (10, 10 + i * 20))
