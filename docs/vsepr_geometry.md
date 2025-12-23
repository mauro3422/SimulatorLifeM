# VSEPR Molecular Geometry System

## Overview

The VSEPR (Valence Shell Electron Pair Repulsion) system maintains realistic molecular geometry by applying angular forces to bonded atoms.

## Theory

VSEPR predicts bond angles based on the number of electron regions:

| Num Bonds | Geometry | Ideal Angle | Example |
|-----------|----------|-------------|---------|
| 2 | Linear | 180° | CO₂ |
| 3 | Trigonal Planar | 120° | BF₃ |
| 4 | Tetrahedral | 109.5° | CH₄ |
| 5 | Trigonal Bipyramidal | 90°/120° | PCl₅ |
| 6 | Octahedral | 90° | SF₆ |

## Implementation

### Files

- `src/systems/chemistry_constants.py` - VSEPR angle tables, hybridization data
- `src/systems/chemistry_kernels.py` - `apply_vsepr_geometry_i()` GPU kernel
- `src/systems/simulation_gpu.py` - Orchestrator integration

### GPU Kernel

```python
@ti.func
def apply_vsepr_geometry_i(i: ti.i32):
    # 1. Culling check (only process visible atoms)
    # 2. For each atom with 2+ bonds
    # 3. Calculate angle between each pair of bonds
    # 4. Apply restoring force toward ideal angle
```

### Performance

- Uses culling bounds (`sim_bounds`) - only processes visible atoms
- Fused into `kernel_resolve_constraints()` with collision and bond forces
- O(N) complexity with O(k²) per atom where k = number of bonds (max 8)

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| ANGULAR_SPRING_K | 0.5 | Angular spring stiffness |
| ANGULAR_DAMPING | 0.3 | Angular damping |
| ANGULAR_FORCE_FACTOR | 0.15 | Force application factor |
| ANGLE_TOLERANCE | 5° | Minimum angle error to apply force |

## Usage

The VSEPR system is automatically integrated into the simulation loop:

```
kernel_resolve_constraints():
├── resolve_constraints_grid_i()  # Collisions
├── apply_bond_forces_i()         # Spring forces  
└── apply_vsepr_geometry_i()      # Angular forces (VSEPR)
```

## Verification

Run `scripts/physics_verify.py` to validate the physics system.
