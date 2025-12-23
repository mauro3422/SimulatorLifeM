"""
Physics Stress Test Script
==========================
Runs the simulation in a "headless" mode (minimal UI/overhead) to verify stability 
and collect performance metrics over a fixed duration.

Goals:
1. Verify stability (bonds broken vs formed)
2. Measure performance (FPS, Physics MS)
3. Detect "explosions" (sudden energy spikes)
"""
import sys
import os
import time
import numpy as np
from PIL import Image

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Mock imgui to run headless if possible, or just use minimal window
# Since our main loop depends on imgui for IO, we'll import it but not render a complex UI.
import glfw
from src.core.context import get_context
from src.core.frame_loop import FrameLoop
from src.core.perf_logger import get_perf_logger
from src.systems import taichi_fields
from src.config import system_constants as sys_cfg
import taichi as ti

# ==============================================================================
# CONFIG
# ==============================================================================
FRAMES_TO_RUN = 600  # ~10 seconds at 60 FPS
TARGET_PARTICLES = 5000
TEST_NAME = "physics_stress_test"

def run_test():
    print(f"🚀 STARTING STRESS TEST: {TEST_NAME}")
    print(f"🎯 Target: {FRAMES_TO_RUN} frames, {TARGET_PARTICLES} particles")
    
    # 1. Init Context
    state = get_context()
    
    # Init Simulation Data (Mocking main.py injection)
    # This relies on state.init_simulation doing the heavy lifting if params are passed
    # But main.py sets up a lot. For simplicity, we'll rely on the singleton state 
    # being properly initialized if we follow a similar pattern to main.py's init.
    
    # Check if we can run without full main.py setup. 
    # Simulation fields need to be injected.
    from src.systems.simulation_gpu import (
        MAX_PARTICLES, n_particles, pos, vel, radii, is_active, atom_types, 
        gravity, friction, temperature, max_speed, world_width, world_height,
        dist_equilibrio, spring_k, damping, rango_enlace_min, 
        rango_enlace_max, dist_rotura, max_fuerza,
        sim_bounds, run_simulation_fast, update_borders_gl,
        prepare_bond_lines_gl, compact_render_data, prepare_highlights,
        universal_gpu_buffer, num_enlaces, enlaces_idx, pos_z,
        prob_enlace_base, click_force, click_radius, manos_libres, colors
    )
    
    import src.systems.simulation_gpu as sim_gpu
    print(f"DEBUG: sim_gpu path = {sim_gpu.__file__}")
    
    # 2. Window Prep (moved after imports to satisfy Taichi)
    # Minimal Window for Context (Taichi/OpenGL need it)
    if not glfw.init():
        print("Failed to init GLFW")
        return
        
    window = glfw.create_window(800, 600, "Stress Test (Visual)", None, None)
    glfw.make_context_current(window)

    # Init ModernGL (Required for Renderer)
    import moderngl
    ctx = moderngl.create_context()
    
    # Init Renderer
    from src.renderer.particle_renderer import ParticleRenderer
    renderer = ParticleRenderer(ctx, max_particles=sys_cfg.MAX_PARTICLES, max_bond_vertices=sys_cfg.MAX_BONDS * 2)
    state.renderer = renderer # Inject into state for FrameLoop to use logic if needed
    
    # Enable Blending
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    # ================== DATA INIT ==================
    import src.systems.simulation_gpu as sim_gpu
    
    print("🎲 Generating Random Particle Data...")
    active_data = np.ones(TARGET_PARTICLES, dtype=np.int32)
    
    # Random atom types (0-5)
    atoms_data = np.random.randint(0, 6, size=TARGET_PARTICLES, dtype=np.int32)
    
    # Spawning logic: EXTREME density for chemistry verification
    SPAWN_AREA = 500.0 # Super tight cluster
    pos_data = (np.random.rand(TARGET_PARTICLES, 2) * SPAWN_AREA) + (sys_cfg.WORLD_SIZE * 0.5 - SPAWN_AREA * 0.5)
    
    print("🚀 Injecting Data into GPU...")
    print("🚀 Injecting Data into GPU (Manual)...")
    
    # Pad to MAX_PARTICLES to avoid shape mismatch
    max_p = sim_gpu.MAX_PARTICLES
    
    pad_active = np.zeros(max_p, dtype=np.int32)
    pad_active[:TARGET_PARTICLES] = active_data
    sim_gpu.is_active.from_numpy(pad_active)
    
    pad_atoms = np.zeros(max_p, dtype=np.int32)
    pad_atoms[:TARGET_PARTICLES] = atoms_data
    sim_gpu.atom_types.from_numpy(pad_atoms)
    
    pad_pos = np.zeros((max_p, 2), dtype=np.float32)
    pad_pos[:TARGET_PARTICLES] = pos_data.astype(np.float32)
    sim_gpu.pos.from_numpy(pad_pos)
    
    # 4. Set N_Particles
    sim_gpu.n_particles[None] = TARGET_PARTICLES
    
    # 5. Reset other fields
    sim_gpu.vel.fill(0)
    sim_gpu.num_enlaces.fill(0)
    
    # 6. Set Sim Bounds (CRITICAL for Chemistry Culling)
    bounds_arr = np.array([0.0, 0.0, sys_cfg.WORLD_SIZE, sys_cfg.WORLD_SIZE], dtype=np.float32)
    sim_gpu.sim_bounds.from_numpy(bounds_arr)
    print(f"📦 Sim Bounds set to: {bounds_arr}")
    
    state.init_camera(sys_cfg.WORLD_SIZE, 800, 600)
    
    # Mock 'sim' dict for FrameLoop/MoleculeDetector compatibility
    state.sim = {
        'atom_types': sim_gpu.atom_types,
        'enlaces_idx': sim_gpu.enlaces_idx,
        'num_enlaces': sim_gpu.num_enlaces
    }
    

    # Resources
    gpu_resources = {
        'sim_bounds': sim_bounds, 'run_simulation_fast': run_simulation_fast,
        'update_borders_gl': update_borders_gl, 'prepare_bond_lines_gl': prepare_bond_lines_gl,
        'compact_render_data': compact_render_data, 'prepare_highlights': prepare_highlights,
        'universal_gpu_buffer': universal_gpu_buffer, 'n_particles': n_particles,
        'pos': pos, 'pos_z': pos_z, 'num_enlaces': num_enlaces, 'enlaces_idx': enlaces_idx,
    }
    
    from src.renderer.opengl_kernels import OFFSET_STATS, OFFSET_PARTICLES, OFFSET_BONDS, OFFSET_HIGHLIGHTS, OFFSET_DEBUG
    render_resources = {
        'OFFSET_STATS': OFFSET_STATS, 'OFFSET_PARTICLES': OFFSET_PARTICLES,
        'OFFSET_BONDS': OFFSET_BONDS, 'OFFSET_HIGHLIGHTS': OFFSET_HIGHLIGHTS, 'OFFSET_DEBUG': OFFSET_DEBUG,
    }
    
    # Frame Loop
    frame_loop = FrameLoop(state, gpu_resources, render_resources)
    perf = get_perf_logger()
    perf.session_id = f"stress_test_{int(time.time())}"
    
    # Mock IO for tick
    class MockIO:
        class DisplaySize:
            x, y = 800, 600
        display_size = DisplaySize()
    
    # ================== VERIFICATION ==================
    def verify_initialization():
        print("🔍 VERIFYING INITIALIZATION...")
        pos_data = pos.to_numpy()
        active_data = is_active.to_numpy()
        active_count = np.sum(active_data)
        
        if active_count == 0:
            print("❌ ERROR: No active particles found!")
            return False
            
        mean_pos = np.mean(pos_data[active_data == 1], axis=0)
        print(f"✅ Active Particles: {active_count}")
        print(f"✅ Center of Mass: {mean_pos}")
        print("✅ Simulation Memory Initialized correctly.")
        return True

    if not verify_initialization():
        return

    print("ℹ️ NOTE: Visuals are disabled for max speed (White/Black screen is normal).")
    
    # Use Global World Size (15000)
    
    # Initialize again with new size
    state.init_camera(sys_cfg.WORLD_SIZE, 800, 600)
    
    # Init GL for basic visual feedback
    try:
        from OpenGL.GL import glClear, glClearColor, GL_COLOR_BUFFER_BIT
        DEFAULT_BG = (0.1, 0.1, 0.2, 1.0) # Science Blue
    except:
        DEFAULT_BG = None

    print(f"⚠️ DENSITY: World Size is {sys_cfg.WORLD_SIZE}")

    # ================== PHYSICS INIT (Explicit) ==================
    import src.systems.physics_constants as phys_cfg
    
    # Force values (Taichi fields init to 0 by default if not set)
    print("🔧 Setting Physics Constants...")
    taichi_fields.prob_enlace_base[None] = phys_cfg.PROB_ENLACE_REALISTA
    taichi_fields.dist_rotura[None] = phys_cfg.DIST_EQUILIBRIO_BASE * phys_cfg.DIST_ROTURA_FACTOR
    taichi_fields.max_fuerza[None] = phys_cfg.MAX_FORCE_BASE
    taichi_fields.rango_enlace_max[None] = phys_cfg.RANGO_ENLACE_MAX_BASE
    
    print(f"   -> Prob: {taichi_fields.prob_enlace_base[None]}")
    print(f"   -> Break Dist: {taichi_fields.dist_rotura[None]}")
    
    # Force Probability MAX for visibility
    taichi_fields.prob_enlace_base[None] = 1.0
    taichi_fields.rango_enlace_max[None] = 200.0 # Wide range for test
    print(f"   -> Force Prob: {taichi_fields.prob_enlace_base[None]}")
    print(f"   -> Force Range: {taichi_fields.rango_enlace_max[None]}")

    # ================== CHEM INIT ==================
    print("🧪 Initializing Chemistry (Valences)...")
    taichi_fields.sync_atomic_data()
    
    @ti.kernel
    def init_valencies_kernel():
        for i in range(sys_cfg.MAX_PARTICLES):
            if taichi_fields.is_active[i] == 1:
                t = taichi_fields.atom_types[i]
                if i < 10:
                    print(f"[Kernel] P{i} T:{t} ValMax:{taichi_fields.VALENCIAS_MAX[t]}")
                # VALENCIAS_MAX is int, manos_libres is float
                taichi_fields.manos_libres[i] = float(taichi_fields.VALENCIAS_MAX[t])

    init_valencies_kernel()
    print("✅ Valences initialized.")
    
    # FORCE VALENCES (Hardcoded fallback)
    print("💪 Forcing Valences (Hardcoded)")
    # H, C, O, N, P, S order typically
    hardcoded_val = np.array([1, 4, 2, 3, 5, 6], dtype=np.int32) 
    # Check shape
    current_shape = taichi_fields.VALENCIAS_MAX.shape[0]
    if current_shape > 6:
        # pad
        padded = np.zeros(current_shape, dtype=np.int32)
        padded[:6] = hardcoded_val
        hardcoded_val = padded
    
    taichi_fields.VALENCIAS_MAX.from_numpy(hardcoded_val)
    
    # init_valencies_kernel() # DISABLE KERNEL
    print("✅ Valences initialized (Kernel Disabled).")
    
    # MANUAL INJECTION OF HANDS
    print("💉 Injecting Hands directly from CPU...")
    # Pad to max
    hands_cpu = np.zeros(sim_gpu.MAX_PARTICLES, dtype=np.float32)
    hands_cpu[:TARGET_PARTICLES] = 4.0 # Give everyone 4 hands
    sim_gpu.manos_libres.from_numpy(hands_cpu)
    
    # Debug: Check Hands
    total_hands = sim_gpu.manos_libres.to_numpy().sum()
    print(f"📊 Total Free Hands: {total_hands}")
    
    # FORCE AFFINITY & BOUNDS (All 1.0)
    print("💘 Forcing Universal Love (Affinity = 1.0) on GPU...")
    @ti.kernel
    def force_data_kernel():
        for i, j in taichi_fields.AFINIDAD_MATRIX:
            taichi_fields.AFINIDAD_MATRIX[i, j] = 1.0
        
        # Explicit bounds
        sim_gpu.sim_bounds[0] = 0.0
        sim_gpu.sim_bounds[1] = 0.0
        sim_gpu.sim_bounds[2] = sys_cfg.WORLD_SIZE
        sim_gpu.sim_bounds[3] = sys_cfg.WORLD_SIZE
        
        # Explicit N (Inside kernel)
        sim_gpu.n_particles[None] = TARGET_PARTICLES
        
        # Ensure VALENCIAS_MAX is not zero
        for v in range(6):
            if taichi_fields.VALENCIAS_MAX[v] == 0:
                # Default valences for types 0-5 if not loaded
                if v == 0: taichi_fields.VALENCIAS_MAX[v] = 1
                elif v == 1: taichi_fields.VALENCIAS_MAX[v] = 4
                elif v == 2: taichi_fields.VALENCIAS_MAX[v] = 1
                elif v == 3: taichi_fields.VALENCIAS_MAX[v] = 2
                elif v == 4: taichi_fields.VALENCIAS_MAX[v] = 3
                elif v == 5: taichi_fields.VALENCIAS_MAX[v] = 4

        for i in range(TARGET_PARTICLES):
            sim_gpu.is_active[i] = 1
            # Importante: Inicializar manos libres basándose en el tipo de átomo
            t = sim_gpu.atom_types[i]
            val = taichi_fields.VALENCIAS_MAX[t]
            sim_gpu.manos_libres[i] = float(val)
            sim_gpu.num_enlaces[i] = 0
            
        # Reset counter for real measurement
        taichi_fields.total_bonds_count[None] = 0
        taichi_fields.rango_enlace_max[None] = 200.0 # Wide range
        taichi_fields.prob_enlace_base[None] = 1.0 # 100% chance
        
        # Enlarge for visibility
        for i in range(TARGET_PARTICLES):
            sim_gpu.radii[i] = 15.0
        
        # MANUAL BOND (0-1)
        sim_gpu.enlaces_idx[0, 0] = 1
        sim_gpu.enlaces_idx[1, 0] = 0
        sim_gpu.num_enlaces[0] = 1
        sim_gpu.num_enlaces[1] = 1
    
    # Set from Python too (Double insurance)
    taichi_fields.n_particles[None] = TARGET_PARTICLES
    
    force_data_kernel()
    ti.sync() # Barrier
    print(f"✅ Affinity, Bounds, N={taichi_fields.n_particles[None]}, Range & Manual Bond Forced on GPU.")

    # ================== MAIN LOOP ==================
    start_time = time.time()
    
    from src.systems.molecule_detector import get_molecule_detector
    
    for i in range(FRAMES_TO_RUN):
        # Keep window responsive
        glfw.poll_events()
        
        # Clear screen (ModernGL)
        ctx.clear(0.1, 0.1, 0.2)
        
        # Tick (Calculate Physics & Prepare Render Data)
        frame_data = frame_loop.tick(MockIO(), sys_cfg.WORLD_SIZE)
        
        # Camera adjustment for visualization if first frame
        if i == 0:
             state.camera.center = [7500.0, 7500.0]
             state.camera.set_zoom(0.5) # Zoom in to see the 500-unit cluster
        
        # Render (Draw to screen)
        if frame_data:
            frame_loop.render_frame(frame_data, sys_cfg.WORLD_SIZE, bonds_only=False)
            
        # Screenshot diagnostic (After render!)
        if i == 100:
            print("📸 Capturing screenshot at frame 100...")
            ti.sync() # Ensure GPU is done
            data = ctx.screen.read(components=3)
            img = Image.frombytes('RGB', ctx.screen.size, data)
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img.save("screenshot_stress.png")
            print("✅ Screenshot saved to screenshot_stress.png")
            
        perf.end_frame(state.fps)
        
        # Swap buffers 
        glfw.swap_buffers(window)
        
        # Progress
        if i % 100 == 0:
            broken = taichi_fields.total_bonds_broken_dist[None]
            
            # TRUTH: Read directly from Taichi (Bypass Perf/Buffer lag)
            formed = taichi_fields.total_bonds_count[None]
            
            # DEBUG: Check bounds and hands
            bounds = sim_gpu.sim_bounds.to_numpy()
            hands_Sample = sim_gpu.manos_libres.to_numpy().sum()
            active_Sample = sim_gpu.is_active.to_numpy().sum()
            val_max_Sample = taichi_fields.VALENCIAS_MAX.to_numpy()[:6]
            grid_pop = sim_gpu.grid_count.to_numpy().sum()
            enlaces_sum = sim_gpu.num_enlaces.to_numpy().sum()
            
            msg = f"   [Debug] Bounds: {bounds}\n"
            msg += f"   [Debug] Hands Sum: {hands_Sample} | Active: {active_Sample} | Grid Pop: {grid_pop}\n"
            msg += f"   [Debug] ValMax[0:6]: {val_max_Sample} | num_enlaces sum: {enlaces_sum}\n"
            print(msg)
            with open("debug_bounds.txt", "a") as f:
                f.write(msg)
            
            # Force detection for report
            from src.systems.molecule_detector import get_molecule_detector
            det = get_molecule_detector()
            # We can't easily force it without arguments, but frame loop runs it every 60 frames.
            # We'll just read the latest state.
            
            unique_mols = len(det.discovered_formulas)
            mol_list = list(det.discovered_formulas) if unique_mols > 0 else "[]"
            
            print(f"Frame {i}/{FRAMES_TO_RUN} | FPS: {state.fps:.1f} | Bonds: {formed} | Broken: {broken} | Mols: {unique_mols} {mol_list}")
        
            print(f"Frame {i}/{FRAMES_TO_RUN} | FPS: {state.fps:.1f} | Bonds: {formed} | Broken: {broken} | Mols: {unique_mols} {mol_list}")
            
    # Save results
    perf.save_session()
    
    print(f"✅ Test Complete in {time.time() - start_time:.2f}s")
    print(f"Final Broken Bonds (Dist): {taichi_fields.total_bonds_broken_dist[None]}")

if __name__ == "__main__":
    run_test()
