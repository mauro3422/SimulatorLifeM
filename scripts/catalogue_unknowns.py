
import json
import os
import shutil

# --- DEFINICIONES DE LORE Y CATEGORÍA ---
# Mapeo manual basado en investigación y creatividad para las 25 incógnitas

DATABASE_ROOT = "data/molecules"

NEW_DEFINITIONS = {
    # --- INORGÁNICAS EXÓTICAS ---
    "H2N2O2": {
        "target_file": "inorganic/exotic.json",
        "name": "Ácido Hiponitroso",
        "name_en": "Hyponitrous Acid",
        "category": "precursor_unstable",
        "lore": "Un ácido de nitrógeno inestable y explosivo en estado sólido. Su presencia indica un ciclo del nitrógeno activo pero volátil.",
        "color": [150, 150, 255]
    },
    "H2O4": {
        "target_file": "inorganic/exotic.json",
        "name": "Tetróxido de Hidrógeno",
        "name_en": "Hydrogen Tetroxide",
        "category": "exotic_oxidizer",
        "lore": "Molécula teórica rica en oxígeno. Altamente reactiva y efímera, actúa como un super-oxidante en la sopa primordial.",
        "color": [255, 100, 100]
    },
    "H4S1": {
        "target_file": "inorganic/exotic.json",
        "name": "Sulfurano",
        "name_en": "Sulfurane",
        "category": "exotic_hydride",
        "lore": "Compuesto hipervalente de azufre. Desafía la regla del octeto, existiendo solo bajo presiones moleculares locales extremas.",
        "color": [255, 230, 100]
    },
    
    # --- ORGÁNICAS / PRECURSORES BIOLÓGICOS ---
    "C4H4N3O2": {
        "target_file": "bio/nucleobases.json",
        "name": "Proto-Citosina",
        "name_en": "Proto-Cytosine",
        "category": "nucleobase_precursor",
        "lore": "Una variante primitiva y deshidrogenada de la Citosina. Un 'borrador' evolutivo en el camino hacia el código genético.",
        "color": [100, 255, 150] # Greenish like bases
    },
     "C2H5O1": {
        "target_file": "organic/precursors.json",
        "name": "Radical Etóxido",
        "name_en": "Ethoxide Radical",
        "category": "radical",
        "lore": "La forma radicalaria del etanol. Extremadamente reactivo, busca protones desesperadamente para estabilizarse en alcohol.",
        "color": [200, 200, 200]
    },
    
    # --- SILICIO / HÍBRIDOS (EXÓTICAS) ---
    "C3H8O1Si1": {
        "target_file": "organic/exotic.json", # New file
        "name": "Trimetilsilanol",
        "name_en": "Trimethylsilanol",
        "category": "organosilicon",
        "lore": "Compuesto híbrido carbono-silicio. Sugiere una química paralela donde el silicio intenta imitar al carbono.",
        "color": [180, 180, 190]
    },
    "C2H1P1Si1": {
        "target_file": "organic/exotic.json",
        "name": "Sili-Fosfo-Etino",
        "name_en": "Sili-Phospho-Ethyne",
        "category": "organosilicon_rare",
        "lore": "Extraña unión triple entre C, P y Si. Una curiosidad química posible solo en simulaciones de alta energía.",
        "color": [160, 160, 170]
    },
     "C3H8O2P2Si1": {
        "target_file": "organic/exotic.json",
        "name": "Complejo Si-P Orgánico",
        "name_en": "Organic Si-P Complex",
        "category": "complex_aggregate",
        "lore": "Agregado complejo que incorpora silicio y fósforo en una matriz de carbono. ¿Un intento fallido de vida basada en silicio?",
         "color": [150, 150, 160]
    },

    # --- HETEROCICLOS Y RARAS ---
    "C3N1P1": {
        "target_file": "inorganic/exotic.json",
        "name": "Ciano-Fosfina",
        "name_en": "Cyanophosphine",
        "category": "precursor_toxic",
        "lore": "Precursor reactivo que combina las propiedades tóxicas del cianuro con la reactividad química del fósforo.",
        "color": [200, 100, 200]
    },
    "C2H2N1O2": {
        "target_file": "organic/precursors.json",
        "name": "Nitroeteno (Isómero)",
        "name_en": "Nitroethene Isomer",
        "category": "toxic_organic",
        "lore": "Compuesto nitrogenado insaturado. Útil para síntesis complejas pero inestable por sí mismo.",
        "color": [200, 200, 100]
    },
    
    # --- GENERICS / DEFAULTS FOR THE REST ---
    # Si no está arriba, caerá aquí con un nombre generado
}

def generate_default_lore(formula):
    return {
        "target_file": "organic/exotic.json",
        "name": f"Compuesto Exótico {formula}",
        "name_en": f"Exotic Compound {formula}",
        "category": "exotic_organic",
        "lore": "Estructura molecular inusual surgida del caos primordial. Su función biológica es desconocida.",
        "color": [120, 120, 120]
    }

def catalogue_unknowns():
    source_path = 'data/unknown_molecules.json'
    
    if not os.path.exists(source_path):
        print("No unknown_molecules.json found.")
        return

    with open(source_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    unknowns = data.get('unknown_molecules', [])
    if not unknowns:
        print("No unknowns to catalogue.")
        return

    print(f"Propcessing {len(unknowns)} unknowns...")

    # Group by target file to minimize I/O
    files_to_update = {} # "path": [entry1, entry2]
    
    processed_formulas = []

    for entry in unknowns:
        formula = entry['formula']
        
        # Get definitions
        if formula in NEW_DEFINITIONS:
            defi = NEW_DEFINITIONS[formula]
        else:
            defi = generate_default_lore(formula)
            
        target_path = os.path.join(DATABASE_ROOT, defi['target_file'])
        
        # Build DB entry
        db_entry = {
            formula: {
                "identity": {
                    "names": {
                        "es": defi['name'],
                        "en": defi['name_en']
                    },
                    "formula": formula,
                    "category": defi['category'],
                    "family_color": defi['color']
                },
                "lore": {
                    "origin_story": defi['lore'],
                    "biological_presence": "Trazas",
                    "utility": "Investigación"
                },
                "gameplay": {
                    "milestones": [],
                    "discovery_points": 15, # High points for exotics
                    "difficulty": "hard"
                }
            }
        }
        
        files_to_update.setdefault(target_path, {}).update(db_entry)
        processed_formulas.append(formula)

    # WRITE TO FILES
    for file_path, new_entries in files_to_update.items():
        # Ensure dir exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file_data = {"molecules": {}}
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                 try: 
                    file_data = json.load(f)
                 except: pass
        
        # Update
        file_data.setdefault("molecules", {}).update(new_entries)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=4, ensure_ascii=False)
            
        print(f"Updated {file_path} with {len(new_entries)} new molecules.")

    # CLEAR UNKNOWN FILE
    data['unknown_molecules'] = []
    data['summary']['total_incognitas'] = 0
    
    with open(source_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print("Unknowns file cleared and catalogued successfully!")

if __name__ == "__main__":
    catalogue_unknowns()
