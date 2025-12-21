"""
Datos Atómicos Data-Driven
==========================
Carga datos de átomos desde JSON y preprocesa para uso en GPU.
"""

import os
import json
import numpy as np


def load_atoms_from_json() -> dict:
    """Carga datos de átomos desde archivos JSON en data/atoms/."""
    atoms_path = os.path.join(os.getcwd(), "data", "atoms")
    atom_data = {}
    
    if not os.path.exists(atoms_path):
        os.makedirs(atoms_path)
        return {}
        
    for filename in os.listdir(atoms_path):
        if filename.endswith(".json"):
            filepath = os.path.join(atoms_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                symbol = data.get("symbol", filename.split(".")[0].upper())
                atom_data[symbol] = data
                
    return atom_data


# Cargar tabla periódica
ATOMS = load_atoms_from_json()

# Fallback de seguridad
if not ATOMS:
    ATOMS = {
        "H": {
            "color": (255, 255, 255),
            "radius": 6,
            "mass": 1.0,
            "valence": 1,
            "electronegativity": 2.1,
            "description": "Error al cargar JSON"
        }
    }

# Pre-procesamiento para NumPy (performance)
TIPOS_NOMBRES = list(ATOMS.keys())
COLORES = np.array([a["color"] for a in ATOMS.values()])
RADIOS = np.array([a["radius"] for a in ATOMS.values()])
MASAS = np.array([a["mass"] for a in ATOMS.values()])
VALENCIAS = np.array([a["valence"] for a in ATOMS.values()])
ELECTRONEG_DATA = np.array([a.get("electronegativity", 2.0) for a in ATOMS.values()])
