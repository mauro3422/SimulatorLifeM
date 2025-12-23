"""
Molecular Analysis Panel - Panel de UI para estadísticas moleculares
=====================================================================
Muestra estadísticas en tiempo real de formación, estabilidad y ángulos.
"""

from imgui_bundle import imgui
from src.systems.molecular_analyzer import get_molecular_analyzer
from src.config.molecules import get_molecule_name


def draw_molecular_analysis_panel(state, visible: bool = True):
    """
    Dibuja el panel de análisis molecular.
    
    Muestra:
    - Moléculas activas
    - Formaciones/destrucciones recientes
    - Top moléculas más estables
    - Análisis de ángulos
    """
    if not visible:
        return
        
    analyzer = get_molecular_analyzer()
    summary = analyzer.get_summary()
    
    # Posicionar en la esquina izquierda, debajo del panel de control
    panel_w = 280
    panel_h = 350
    imgui.set_next_window_pos((10, 350), imgui.Cond_.first_use_ever)
    imgui.set_next_window_size((panel_w, panel_h), imgui.Cond_.first_use_ever)
    imgui.set_next_window_bg_alpha(0.85)
    
    expanded, _ = imgui.begin("🔬 ANÁLISIS MOLECULAR", None, 
                              imgui.WindowFlags_.always_auto_resize)
    
    if expanded:
        # === Estadísticas Generales ===
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "◆ ESTADÍSTICAS GLOBALES")
        imgui.separator()
        
        imgui.text(f"Moléculas Activas: {summary['active_molecules']}")
        imgui.text(f"Fórmulas Únicas: {summary['unique_formulas']}")
        imgui.text_colored((0.3, 1.0, 0.3, 1.0), f"Formaciones: {summary['total_formations']}")
        imgui.text_colored((1.0, 0.5, 0.5, 1.0), f"Destrucciones: {summary['total_destructions']}")
        
        imgui.spacing()
        imgui.spacing()
        
        # === Top Moléculas Más Formadas ===
        imgui.text_colored((1.0, 0.8, 0.2, 1.0), "◆ TOP FORMACIONES (Estables)")
        imgui.separator()
        
        shown_count = 0
        for formula, count in summary['top_formed']:
            name = get_molecule_name(formula)
            if name != "Transitorio":
                imgui.text(f"  {formula} ({name}): {count}")
                shown_count += 1
            if shown_count >= 5: break
        
        if shown_count == 0:
            imgui.text_disabled("  Ninguna estable aún...")
        
        imgui.spacing()
        imgui.spacing()
        
        # === Top Moléculas Más Estables ===
        imgui.text_colored((0.4, 1.0, 0.8, 1.0), "◆ MÁS ESTABLES (Avg Lifetime)")
        imgui.separator()
        
        shown_stable = 0
        for formula, avg_life in summary['top_stable']:
            name = get_molecule_name(formula)
            if avg_life > 0 and name != "Transitorio":
                imgui.text(f"  {formula} ({name}): {avg_life:.1f}f")
                shown_stable += 1
            if shown_stable >= 5: break

        if shown_stable == 0:
            imgui.text_disabled("  Solo moléculas efímeras...")
        
        imgui.spacing()
        imgui.spacing()
        
        # === Auditoría & Junk (Modernizado) ===
        imgui.spacing()
        imgui.separator()
        from src.gameplay.inventory import get_inventory
        inv = get_inventory()
        audit_count = len(inv.get_audit_list())
        junk_count = inv.get_transitory_count()
        
        # Grid de contadores
        if imgui.begin_table("junk_counters", 2):
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text_colored((1.0, 0.4, 0.4, 1.0), f"⚠ DESCONOCIDAS")
            imgui.table_set_column_index(1)
            imgui.text_colored((1.0, 1.0, 1.0, 1.0), f"[{audit_count}]")
            if imgui.is_item_hovered():
                imgui.set_tooltip("Moléculas sin clasificar en el sistema.")
            
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text_disabled("🗑 TRANSITORIAS")
            imgui.table_set_column_index(1)
            imgui.text_disabled(f"[{junk_count}]")
            if imgui.is_item_hovered():
                imgui.set_tooltip("Fragmentos inestables o ruido de fondo.")
            
            imgui.end_table()
            
        if audit_count > 0:
            imgui.text_disabled(" (Revisar logs para descubrimientos)")
    
    imgui.end()


def run_molecular_analysis_tick(state):
    """
    Ejecuta el análisis molecular cada N frames.
    Debe llamarse desde el loop principal.
    """
    # Solo analizar cada 30 frames para no impactar performance
    if not hasattr(state, '_mol_analysis_counter'):
        state._mol_analysis_counter = 0
        
    state._mol_analysis_counter += 1
    
    if state._mol_analysis_counter >= 30:
        state._mol_analysis_counter = 0
        
        # Obtener datos necesarios de la simulación
        if hasattr(state, 'sim') and state.sim:
            try:
                pos_np = state.gpu['pos'].to_numpy()
                pos_z_np = state.sim['pos_z'].to_numpy()
                atom_types_np = state.sim['atom_types'].to_numpy()
                enlaces_idx_np = state.sim['enlaces_idx'].to_numpy()
                num_enlaces_np = state.sim['num_enlaces'].to_numpy()
                molecule_id_np = state.sim['molecule_id'].to_numpy()
                is_active_np = state.sim['is_active'].to_numpy()
                
                analyzer = get_molecular_analyzer()
                analyzer.analyze_frame(
                    pos_np, pos_z_np, atom_types_np, enlaces_idx_np,
                    num_enlaces_np, molecule_id_np, is_active_np
                )
                
                # Después del análisis, verificar misiones del jugador (Evento)
                state.progression.check_mission()
            except Exception as e:
                pass  # Silenciar errores durante inicialización
