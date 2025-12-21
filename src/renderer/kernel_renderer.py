"""
Renderer Custom por Kernel - QuimicPYTHON
=========================================
Dibuja partículas directamente a un buffer de imagen usando kernels GPU.
Mucho más rápido que canvas.circles() de GGUI.
"""
import taichi as ti

# Dimensiones del área de renderizado (sin UI)
RENDER_WIDTH = 600  # Ancho de la zona de simulación
RENDER_HEIGHT = 500  # Alto de la ventana

# Buffer de imagen para renderizado directo
frame_buffer = ti.Vector.field(3, dtype=ti.f32, shape=(RENDER_WIDTH, RENDER_HEIGHT))

@ti.kernel
def clear_frame_buffer():
    """Limpia el frame buffer con color de fondo."""
    for i, j in frame_buffer:
        frame_buffer[i, j] = ti.Vector([0.02, 0.02, 0.05])  # Azul oscuro

@ti.kernel
def draw_circles_to_buffer(
    pos_norm: ti.template(),
    radii_norm: ti.template(),
    colors: ti.template(),
    n_particles: ti.i32
):
    """
    Dibuja círculos al frame buffer usando GPU puro.
    Cada partícula dibuja sus propios pixels en paralelo.
    """
    for p in range(n_particles):
        # Posición normalizada (0-1) a pixels
        px = int(pos_norm[p][0] * RENDER_WIDTH)
        py = int((1.0 - pos_norm[p][1]) * RENDER_HEIGHT)  # Flip Y
        
        # Radio en pixels (mínimo 1 pixel)
        r_pixels = int(ti.max(1.0, radii_norm[p] * RENDER_WIDTH * 2))
        
        if r_pixels <= 0:
            continue
        
        color = colors[p]
        
        # Dibujar círculo relleno
        for dx in range(-r_pixels, r_pixels + 1):
            for dy in range(-r_pixels, r_pixels + 1):
                if dx*dx + dy*dy <= r_pixels*r_pixels:
                    x = px + dx
                    y = py + dy
                    if 0 <= x < RENDER_WIDTH and 0 <= y < RENDER_HEIGHT:
                        frame_buffer[x, y] = color

@ti.kernel
def draw_circles_fast(
    pos_norm: ti.template(),
    radii_norm: ti.template(),
    colors: ti.template(),
    n_visible: ti.i32,
    visible_indices: ti.template()
):
    """
    Versión optimizada: Solo dibuja partículas visibles usando visible_indices.
    """
    for vi in range(n_visible):
        p = visible_indices[vi]
        
        # Posición normalizada (0-1) a pixels
        px = int(pos_norm[p][0] * RENDER_WIDTH)
        py = int((1.0 - pos_norm[p][1]) * RENDER_HEIGHT)
        
        # Radio en pixels - tamaño compacto
        r_pixels = int(ti.max(1.0, radii_norm[p] * RENDER_WIDTH * 1.0))
        
        if r_pixels <= 0:
            continue
            
        color = colors[p]
        
        # Dibujar círculo (algoritmo de Bresenham simplificado)
        for dx in range(-r_pixels, r_pixels + 1):
            for dy in range(-r_pixels, r_pixels + 1):
                dist_sq = dx*dx + dy*dy
                if dist_sq <= r_pixels*r_pixels:
                    x = px + dx
                    y = py + dy
                    if 0 <= x < RENDER_WIDTH and 0 <= y < RENDER_HEIGHT:
                        # Blend suave en el borde
                        if dist_sq > (r_pixels-1)*(r_pixels-1):
                            # Borde - color atenuado
                            frame_buffer[x, y] = color * 0.7
                        else:
                            frame_buffer[x, y] = color

@ti.kernel
def draw_lines_to_buffer(
    bond_vertices: ti.template(),
    n_vertices: ti.i32,
    color: ti.types.vector(3, ti.f32)
):
    """
    Dibuja líneas (enlaces) al frame buffer con grosor.
    """
    for i in range(n_vertices // 2):
        # Cada par de vértices es una línea
        p1 = bond_vertices[i * 2]
        p2 = bond_vertices[i * 2 + 1]
        
        # Convertir a pixels
        x1 = int(p1[0] * RENDER_WIDTH)
        y1 = int((1.0 - p1[1]) * RENDER_HEIGHT)
        x2 = int(p2[0] * RENDER_WIDTH)
        y2 = int((1.0 - p2[1]) * RENDER_HEIGHT)
        
        # Algoritmo de Bresenham para líneas con GROSOR (3 pixels)
        dx = ti.abs(x2 - x1)
        dy = ti.abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        steps = 0
        max_steps = dx + dy + 1
        
        while steps < max_steps:
            # Dibujar pixel central y adyacentes (línea de 3 pixels de grosor)
            for offset in range(-1, 2):  # -1, 0, 1
                # Si la línea es más horizontal, offset en Y
                # Si es más vertical, offset en X
                if dx >= dy:
                    yo = y + offset
                    if 0 <= x < RENDER_WIDTH and 0 <= yo < RENDER_HEIGHT:
                        frame_buffer[x, yo] = color
                else:
                    xo = x + offset
                    if 0 <= xo < RENDER_WIDTH and 0 <= y < RENDER_HEIGHT:
                        frame_buffer[xo, y] = color
            
            if x == x2 and y == y2:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            steps += 1

@ti.kernel
def draw_box_to_buffer(
    x1: ti.f32, y1: ti.f32, x2: ti.f32, y2: ti.f32,
    color: ti.types.vector(3, ti.f32)
):
    """Dibuja un rectángulo (borde) al buffer."""
    px1 = int(x1 * RENDER_WIDTH)
    py1 = int((1.0 - y1) * RENDER_HEIGHT)
    px2 = int(x2 * RENDER_WIDTH)
    py2 = int((1.0 - y2) * RENDER_HEIGHT)
    
    # Asegurar orden correcto
    if px1 > px2:
        px1, px2 = px2, px1
    if py1 > py2:
        py1, py2 = py2, py1
    
    # Líneas horizontales
    for x in range(px1, px2 + 1):
        if 0 <= x < RENDER_WIDTH:
            if 0 <= py1 < RENDER_HEIGHT:
                frame_buffer[x, py1] = color
            if 0 <= py2 < RENDER_HEIGHT:
                frame_buffer[x, py2] = color
    
    # Líneas verticales
    for y in range(py1, py2 + 1):
        if 0 <= y < RENDER_HEIGHT:
            if 0 <= px1 < RENDER_WIDTH:
                frame_buffer[px1, y] = color
            if 0 <= px2 < RENDER_WIDTH:
                frame_buffer[px2, y] = color

def get_frame_buffer():
    """Retorna el frame buffer para usar con gui.set_image()."""
    return frame_buffer
