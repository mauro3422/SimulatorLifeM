"""
Sistema de Base de Datos de Moléculas con Metadatos Profundos y i18n.
====================================================================
Gestiona la enciclopedia molecular del simulador, cargando datos enriquecidos 
(historia, contexto biológico, hitos) desde archivos JSON categorizados.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

# Global state
_molecule_db: Dict[str, Any] = {}
_current_language: str = "es"
_db_loaded: bool = False

def _get_db_path() -> Path:
    """Obtiene la ruta al directorio de base de datos."""
    base = Path(__file__).parent.parent.parent
    return base / "data" / "molecules"

def load_molecule_database(language: str = "es") -> bool:
    """
    Carga la base de datos de moléculas desde archivos JSON en data/molecules/.
    Unifica todos los archivos en un registro central rico.
    """
    global _molecule_db, _current_language, _db_loaded
    
    db_dir = _get_db_path()
    _molecule_db = {}
    
    if not db_dir.exists():
        print(f"[MOLECULES] ⚠️ Directorio de base de datos no encontrado: {db_dir}")
        return False
    
    try:
        files_loaded = 0
        for file_path in db_dir.rglob("*.json"):
            if "unknown_molecules" in file_path.name or "player_molecules" in file_path.name:
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    molecules = data.get("molecules", {})
                    
                    # Normalización y enriquecimiento al cargar
                    for formula, raw_data in molecules.items():
                        _molecule_db[formula] = _normalize_molecule_data(formula, raw_data)
                        
                    files_loaded += 1
            except Exception as e:
                print(f"[MOLECULES] ❌ Error cargando {file_path.name}: {e}")

        _current_language = language
        _db_loaded = True
        
        print(f"[MOLECULES] ✅ Enciclopedia modular cargada: {len(_molecule_db)} moléculas desde {files_loaded} archivos.")
        return True
    except Exception as e:
        print(f"[MOLECULES] ❌ Error general cargando base de datos: {e}")
        return False

def _normalize_molecule_data(formula: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asegura que los datos de la molécula cumplan con el esquema enciclopédico.
    Si la molécula viene del formato viejo, la 'promociona' al nuevo.
    """
    # Si ya tiene la estructura nueva, la mantenemos, si no, la adaptamos
    if "identity" in data:
        return data
        
    # Estructura de compatibilidad (formato viejo -> nuevo)
    return {
        "identity": {
            "names": data.get("names", {"es": formula, "en": formula}),
            "formula": formula,
            "category": data.get("category", "unknown"),
            "family_color": data.get("color", [200, 200, 200])
        },
        "lore": {
            "origin_story": data.get("description", ""),
            "biological_presence": "",
            "utility": ""
        },
        "gameplay": {
            "milestones": data.get("milestones", []),
            "discovery_points": data.get("points", 10),
            "difficulty": "medium"
        }
    }

def get_molecule_entry(formula: str) -> Optional[Dict[str, Any]]:
    """Obtiene la entrada enciclopédica completa de una molécula."""
    if not _db_loaded:
        load_molecule_database(_current_language)
    
    entry = _molecule_db.get(formula)
    if entry:
        return entry
        
    # Fallback para Agregados (Glitches convertidos en Lore)
    import re
    atoms_count = sum(int(n if n else 1) for n in re.findall(r'[A-Z][a-z]?(\d*)', formula))
    
    # Filtro de sobre-oxidación (ej. H1O5, C1N1O4P1)
    o_match = re.search(r'O(\d+)', formula)
    o_count = int(o_match.group(1)) if o_match else (1 if 'O' in formula else 0)
    non_h_o_match = re.findall(r'([A-NP-Z][a-z]?)(\d*)', formula)
    backbone_atoms = sum(int(n if n else 1) for _, n in non_h_o_match if _ != 'O')
    
    # Heurística: Si hay más de 3 oxígenos por cada átomo central, es físicamente sospechosa
    if backbone_atoms > 0 and o_count > backbone_atoms * 4:
        return None # Lo tratamos como transitorio/anomalía
        
    if atoms_count > 64:
        return _molecule_db.get("AGGREGATE_AMORPHOUS")
        
    return None

def get_molecule_name(formula: str) -> str:
    """Busca el nombre en el idioma actual."""
    if formula == "AGGREGATE_AMORPHOUS":
        entry = get_molecule_entry(formula)
        names = entry["identity"]["names"]
        return names.get(_current_language, names.get("es", "Agregado"))
        
    entry = get_molecule_entry(formula)
    if not entry:
        # Lógica de fallback para moléculas no registradas
        import re
        atoms_count = sum(int(n if n else 1) for n in re.findall(r'[A-Z][a-z]?(\d*)', formula))
        
        # Detectar sobre-oxidación para el nombre
        o_match = re.search(r'O(\d+)', formula)
        o_count = int(o_match.group(1)) if o_match else (1 if 'O' in formula else 0)
        non_h_o_match = re.findall(r'([A-NP-Z][a-z]?)(\d*)', formula)
        backbone_atoms = sum(int(n if n else 1) for _, n in non_h_o_match if _ != 'O')
        
        if backbone_atoms > 0 and o_count > backbone_atoms * 4:
            return "Transitorio Inestable"
            
        if atoms_count > 64: return "Agregado Orgánico Amorfo"
        return "Desconocida" if atoms_count > 4 else "Transitorio"
        
    names = entry["identity"]["names"]
    return names.get(_current_language, names.get("es", formula))

def get_molecule_color(formula: str) -> List[int]:
    """Obtiene el color de la molécula."""
    entry = get_molecule_entry(formula)
    if entry:
        return entry["identity"].get("family_color", [200, 200, 200])
    return [200, 200, 200]

def get_molecule_info(formula: str) -> Optional[Dict[str, Any]]:
    """
    Función de compatibilidad: Retorna dict con names, category, origin.
    Adapta el nuevo formato rico al formato esperado por el resto del sistema.
    """
    entry = get_molecule_entry(formula)
    if not entry:
        return None
        
    e_id = entry["identity"]
    return {
        "names": e_id["names"],
        "category": e_id["category"],
        "origin": entry.get("lore", {}).get("origin_story", ""),
        "color": e_id.get("family_color", [200, 200, 200]),
        "description": entry.get("lore", {}).get("origin_story", "")
    }

def set_language(language: str):
    global _current_language
    _current_language = language

def get_all_known_molecules() -> Dict[str, Any]:
    if not _db_loaded:
        load_molecule_database(_current_language)
    return _molecule_db

def is_known_molecule(formula: str) -> bool:
    """Verifica si una fórmula está en la base de datos."""
    if not _db_loaded:
        load_molecule_database(_current_language)
    return formula in _molecule_db

def export_unknown_molecules(discovered_formulas: set, output_path: str = None) -> str:
    """
    Exporta moléculas desconocidas y anomalías para revisión forense.
    Separa las descubiertas plausibles de los glitches físicos.
    """
    unknown = []
    anomalies = []
    db = get_all_known_molecules()
    
    import re
    
    for formula in discovered_formulas:
        if formula in db:
            continue
            
        atoms_count = sum(int(n if n else 1) for n in re.findall(r'[A-Z][a-z]?(\d*)', formula))
        
        # Categorización por plausibilidad
        is_glitch = atoms_count > 64
        
        # Heurística de Hidrógenos (Plausibilidad química)
        h_match = re.search(r'H(\d+)', formula)
        h_count = int(h_match.group(1)) if h_match else 0
        is_implausible = h_count > (atoms_count - h_count + 1) * 6
        
        if is_glitch or is_implausible:
            anomalies.append({
                "formula": formula,
                "atoms": atoms_count,
                "reason": "Macro-glitch (>64 at)" if is_glitch else "Inestabilidad (H-Saturation)",
                "critical": is_glitch
            })
        else:
            unknown.append({
                "formula": formula,
                "atoms": atoms_count,
                "suggested_entry": {
                    "names": {"es": "[Nombre Sugerido]", "en": "[Suggested Name]"},
                    "category": "unknown"
                }
            })
    
    if output_path is None:
        base = Path(__file__).parent.parent.parent
        output_path = str(base / "data" / "unknown_molecules.json")
    
    report = {
        "summary": {
            "total_incognitas": len(unknown),
            "total_anomalias": len(anomalies)
        },
        "unknown_molecules": unknown,
        "chemical_anomalies": anomalies
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return output_path

# Backwards compatibility - simple dict access
MOLECULES = {}

def _build_legacy_dict():
    """Construye el dict legacy para compatibilidad con workers y escáner."""
    global MOLECULES, _db_loaded
    if not _db_loaded:
        load_molecule_database(_current_language)
    
    MOLECULES.clear()
    for formula, entry in _molecule_db.items():
        names = entry["identity"]["names"]
        MOLECULES[formula] = names.get(_current_language, names.get("es", formula))

# Auto-carga inicial e integración legacy
load_molecule_database("es")
_build_legacy_dict()
