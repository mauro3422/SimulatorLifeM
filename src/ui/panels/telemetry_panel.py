"""
Telemetry Panel - Panel de debug F3 con información de rendimiento.
"""

from imgui_bundle import imgui
from src.config import UIConfig


def draw_telemetry_panel(state, n_visible_count: int, n_simulated_count: int, win_w: float):
    """
    Dibuja el panel de telemetría (solo visible con F3).
    
    Args:
        state: AppState instance
        n_visible_count: Número de partículas visibles (Render Culling)
        n_simulated_count: Número de partículas simuladas (Physics Culling)
        win_w: Window width
    """
    if not state.show_debug:
        return
    
    panel_w = UIConfig.PANEL_STATS_W
    panel_h = UIConfig.PANEL_STATS_H + 120  # Extra height for molecule stats
    
    # Position at top right corner (above monitor panel)
    y_offset = 20  # Top of screen
    imgui.set_next_window_pos((win_w - panel_w - 20, y_offset), imgui.Cond_.always)
    imgui.set_next_window_size((panel_w, panel_h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.85)  # More opaque for better readability
    
    imgui.begin(
        "TELEMETRÍA (F3)", 
        None, 
        imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_resize
    )
    
    imgui.text_colored((0.2, 0.8, 1.0, 1.0), "MONITOR DE SISTEMA")
    imgui.separator()
    imgui.text(f"FPS: {state.fps:.1f}")
    
    imgui.text(f"Total Alloc: {state.n_particles_val}")
    imgui.text_colored((0.5, 1.0, 0.5, 1.0), f"Physics (Sim): {n_simulated_count}")
    imgui.text_colored((1.0, 1.0, 0.4, 1.0), f"Render (Vis):  {n_visible_count}")
    
    if n_simulated_count < state.n_particles_val:
        # "Culled" confunde al usuario. Mejor "Paused" o "Sleeping"
        diff = state.n_particles_val - n_simulated_count
        imgui.text_disabled(f"Paused (Off-screen): {diff}")
    else:
        imgui.text_disabled("Vista Global (All Active)")
    
    # Molecule Detection Stats
    imgui.separator()
    imgui.text_colored((1.0, 0.8, 0.2, 1.0), "DETECCIÓN MOLECULAR")
    
    from src.systems.molecule_detector import get_molecule_detector
    mol_stats = get_molecule_detector().stats
    
    imgui.text(f"Moléculas Activas: {mol_stats['total_molecules']}")
    imgui.text_colored((0.2, 1.0, 0.5, 1.0), f"Conocidas: {mol_stats['known_molecules']}")
    imgui.text_colored((1.0, 0.5, 1.0, 1.0), f"Descubrimientos: {mol_stats['unique_discoveries']}")
    
    # Show top 3 formulas
    formulas = mol_stats.get('last_scan_formulas', {})
    if formulas:
        sorted_formulas = sorted(formulas.items(), key=lambda x: -x[1])[:3]
        imgui.text_disabled("Top Fórmulas:")
        for formula, count in sorted_formulas:
            from src.config.molecules import get_molecule_name
            name = get_molecule_name(formula)
            if name != "Transitorio":
                imgui.text(f"  {name}: {count}")
            else:
                imgui.text_disabled(f"  {formula}: {count}")
    
    imgui.end()
