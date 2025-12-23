import taichi as ti
import numpy as np
import moderngl
import glfw
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.systems.taichi_fields import pos, colors, n_visible, visible_indices, is_active
from src.renderer.particle_renderer import ParticleRenderer
from src.renderer.opengl_kernels import (
    compact_render_data, render_pos, render_col,
    MAX_BOND_VERTICES
)
import src.config.system_constants as const

# --- CONFIG ---
NUM_PARTICLES = 7000
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 600

def init_data():
    """Inicializa partículas aleatorias en Taichi."""
    print(f"[BENCH] Inicializando {NUM_PARTICLES} partículas...")
    
    # Random positions and colors (Padded to MAX_PARTICLES)
    pos_np = np.zeros((const.MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:NUM_PARTICLES] = np.random.rand(NUM_PARTICLES, 2) * const.WORLD_SIZE
    
    col_np = np.zeros((const.MAX_PARTICLES, 3), dtype=np.float32)
    col_np[:NUM_PARTICLES] = np.random.rand(NUM_PARTICLES, 3)
    
    pos.from_numpy(pos_np)
    colors.from_numpy(col_np)
    
    # Is Active
    act_np = np.zeros(const.MAX_PARTICLES, dtype=np.int32)
    act_np[:NUM_PARTICLES] = 1
    is_active.from_numpy(act_np)
    
    # Fake Visibility (All visible for stress test)
    n_visible[None] = NUM_PARTICLES
    
    indices = np.zeros(const.MAX_PARTICLES, dtype=np.int32)
    indices[:NUM_PARTICLES] = np.arange(NUM_PARTICLES, dtype=np.int32)
    visible_indices.from_numpy(indices)

def main():
    # 1. Taichi Init (Already done by import src.systems.taichi_fields)
    # ti.init(arch=ti.vulkan) -> REMOVED to avoid Double Init Error
    
    
    # 2. GLFW Init
    if not glfw.init():
        print("Error: GLFW init failed")
        return

    glfw.window_hint(glfw.RESIZABLE, False)
    # FORCE VSYNC OFF
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    
    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, "Benchmark GPU - 7000 Particles", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glfw.swap_interval(0) # Disable VSync logic
    
    # 3. ModernGL Init
    ctx = moderngl.create_context()
    renderer = ParticleRenderer(ctx, const.MAX_PARTICLES, MAX_BOND_VERTICES)
    
    init_data()
    
    # Camera fake params
    cx, cy = const.WORLD_SIZE / 2, const.WORLD_SIZE / 2
    vis_w_half = const.WORLD_SIZE / 2
    vis_h_half = (vis_w_half / WINDOW_WIDTH) * WINDOW_HEIGHT
    camera_params = (cx, cy, vis_w_half, vis_h_half)
    
    print("[BENCH] Iniciando Loop de Renderizado (Sin Física)...")
    
    frames = 0
    last_time = time.time()
    start_bench = last_time
    
    while not glfw.window_should_close(window):
        t_start = time.perf_counter()
        
        # A. Compaction (GPU)
        compact_render_data()
        ti.sync() # Wait for Taichi
        
        # B. Data Transfer (GPU -> RAM)
        # En benchmark real, descargamos TODO lo visible (7000)
        pos_data = render_pos.to_numpy()[:NUM_PARTICLES]
        col_data = render_col.to_numpy()[:NUM_PARTICLES]
        
        # C. Render (ModernGL)
        ctx.clear(0.05, 0.05, 0.05)
        # Dummy bonds/debug
        renderer.render(pos_data, col_data, None, None, None, WINDOW_WIDTH, WINDOW_HEIGHT, camera_params)
        
        glfw.swap_buffers(window)
        glfw.poll_events()
        
        # FPS Counter
        frames += 1
        now = time.time()
        if now - last_time >= 1.0:
            print(f"FPS: {frames}")
            frames = 0
            last_time = now
            
        # Optional: Exit after 10 seconds
        if now - start_bench > 10.0:
            break
            
    glfw.terminate()

if __name__ == "__main__":
    main()
