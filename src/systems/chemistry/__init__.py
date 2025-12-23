"""
Chemistry Package - Química Molecular para LifeSimulator
=========================================================
Submódulos:
- bonding: Formación de enlaces y propagación de IDs
- bond_forces: Fuerzas de resorte (Hooke)
- vsepr: Geometría molecular VSEPR
- dihedral: Fuerzas torsionales (zig-zag)
- depth_z: Coordenada Z para visualización 2.5D
"""

# Re-exports públicos
from src.systems.chemistry.bonding import (
    check_bonding_func_single,
    check_bonding_gpu,
    reset_molecule_ids,
    propagate_molecule_ids_step,
    update_partial_charges,
)

from src.systems.chemistry.bond_forces import (
    apply_bond_forces_i,
    apply_bond_forces_func,
    apply_bond_forces_gpu,
)

from src.systems.chemistry.vsepr import (
    get_ideal_angle_rad,
    apply_vsepr_geometry_i,
    apply_vsepr_geometry_func,
    apply_vsepr_geometry_gpu,
)

from src.systems.chemistry.dihedral import (
    apply_dihedral_forces_i,
    apply_dihedral_forces_gpu,
)

from src.systems.chemistry.depth_z import (
    compute_depth_z_i,
    compute_depth_z_func,
    compute_depth_z_gpu,
)

__all__ = [
    # Bonding
    'check_bonding_func_single',
    'check_bonding_gpu',
    'reset_molecule_ids',
    'propagate_molecule_ids_step',
    'update_partial_charges',
    # Bond Forces
    'apply_bond_forces_i',
    'apply_bond_forces_func',
    'apply_bond_forces_gpu',
    # VSEPR
    'get_ideal_angle_rad',
    'apply_vsepr_geometry_i',
    'apply_vsepr_geometry_func',
    'apply_vsepr_geometry_gpu',
    # Dihedral
    'apply_dihedral_forces_i',
    'apply_dihedral_forces_gpu',
    # Depth Z
    'compute_depth_z_i',
    'compute_depth_z_func',
    'compute_depth_z_gpu',
]
