"""
Chemistry Kernels - Re-exports para compatibilidad.
====================================================
DEPRECATED: Importar directamente desde src.systems.chemistry

Este archivo mantiene compatibilidad hacia atrás con imports existentes.
Los kernels ahora están organizados en:
- chemistry/bonding.py: Formación de enlaces
- chemistry/bond_forces.py: Fuerzas de resorte
- chemistry/vsepr.py: Geometría molecular
- chemistry/dihedral.py: Fuerzas torsionales
- chemistry/depth_z.py: Profundidad 2.5D
"""

# Re-exports desde el paquete chemistry
from src.systems.chemistry import (
    # Bonding
    check_bonding_func_single,
    check_bonding_gpu,
    reset_molecule_ids,
    propagate_molecule_ids_step,
    update_partial_charges,
    
    # Bond Forces
    apply_bond_forces_i,
    apply_bond_forces_func,
    apply_bond_forces_gpu,
    
    # VSEPR
    get_ideal_angle_rad,
    apply_vsepr_geometry_i,
    apply_vsepr_geometry_func,
    apply_vsepr_geometry_gpu,
    
    # Dihedral
    apply_dihedral_forces_i,
    apply_dihedral_forces_gpu,
    
    # Depth Z
    compute_depth_z_i,
    compute_depth_z_func,
    compute_depth_z_gpu,
)

__all__ = [
    'check_bonding_func_single',
    'check_bonding_gpu',
    'reset_molecule_ids',
    'propagate_molecule_ids_step',
    'update_partial_charges',
    'apply_bond_forces_i',
    'apply_bond_forces_func',
    'apply_bond_forces_gpu',
    'get_ideal_angle_rad',
    'apply_vsepr_geometry_i',
    'apply_vsepr_geometry_func',
    'apply_vsepr_geometry_gpu',
    'apply_dihedral_forces_i',
    'apply_dihedral_forces_gpu',
    'compute_depth_z_i',
    'compute_depth_z_func',
    'compute_depth_z_gpu',
]
