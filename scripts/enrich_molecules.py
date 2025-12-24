#!/usr/bin/env python3
"""
Molecule Lore Enrichment Script
Adds scientific descriptions, origins, milestones and lore to player molecules.
"""

import json
import os
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
PLAYER_MOLECULES = BASE_DIR / "data" / "player_molecules.json"
EMERGENT_PATH = BASE_DIR / "data" / "molecules" / "emergent.json"
OUTPUT_PATH = BASE_DIR / "data" / "molecules" / "enriched_discoveries.json"

# ============================================================================
# SCIENTIFIC KNOWLEDGE DATABASE - REAL MOLECULES
# Based on actual chemistry and astrobiology research
# ============================================================================

KNOWN_MOLECULES = {
    # ==========================================================================
    # FUNDAMENTAL MOLECULES (Cosmically abundant)
    # ==========================================================================
    "H2": {
        "names": {"es": "Hidrógeno Molecular", "en": "Molecular Hydrogen"},
        "lore": {
            "origin_story": "El elemento más abundante del universo, nacido en el Big Bang hace 13.8 mil millones de años.",
            "biological_presence": "Combustible de las estrellas. La fusión H→He ilumina el cosmos.",
            "utility": "Fuente primordial de toda la materia visible del universo."
        },
        "milestones": ["Átomo Primordial", "Combustible Estelar"],
        "difficulty": 1,
        "discovery_points": 10,
        "family_color": [200, 200, 255]
    },
    "O2": {
        "names": {"es": "Oxígeno Molecular", "en": "Molecular Oxygen"},
        "lore": {
            "origin_story": "Producido por fotosíntesis. Causó la Gran Oxidación hace 2.4 mil millones de años.",
            "biological_presence": "Respiración aeróbica. Tóxico para vida anaerobia primitiva.",
            "utility": "Permite metabolismo energético 18x más eficiente que fermentación."
        },
        "milestones": ["Gran Oxidación", "Respiración"],
        "difficulty": 3,
        "discovery_points": 40,
        "family_color": [255, 100, 100]
    },
    "N2": {
        "names": {"es": "Nitrógeno Molecular", "en": "Molecular Nitrogen"},
        "lore": {
            "origin_story": "78% de la atmósfera terrestre. Triple enlace muy estable.",
            "biological_presence": "Inerte. Requiere fijación biológica o rayos para ser asimilado.",
            "utility": "Reservorio de nitrógeno para biosfera."
        },
        "milestones": ["Atmósfera Primordial"],
        "difficulty": 2,
        "discovery_points": 25,
        "family_color": [150, 150, 255]
    },
    
    # ==========================================================================
    # AGUA Y DERIVADOS
    # ==========================================================================
    "H2O1": {
        "names": {"es": "Agua", "en": "Water"},
        "lore": {
            "origin_story": "Traída por cometas y asteroides durante el Bombardeo Tardío.",
            "biological_presence": "Solvente universal. Medio de todas las reacciones bioquímicas.",
            "utility": "Sin agua líquida, no hay vida como la conocemos."
        },
        "milestones": ["Solvente Universal", "Cuna de la Vida"],
        "difficulty": 2,
        "discovery_points": 50,
        "family_color": [100, 150, 255]
    },
    "H2O2": {
        "names": {"es": "Peróxido de Hidrógeno", "en": "Hydrogen Peroxide"},
        "lore": {
            "origin_story": "Formado por radiación UV sobre hielo. Detectado en Marte.",
            "biological_presence": "Usado por células inmunes para matar patógenos.",
            "utility": "Oxidante biológico. Desinfectante natural."
        },
        "milestones": ["Oxidante Primordial", "Escudo Celular"],
        "difficulty": 4,
        "discovery_points": 80,
        "family_color": [255, 220, 220]
    },
    "H3O1": {
        "names": {"es": "Ion Hidronio", "en": "Hydronium Ion"},
        "lore": {
            "origin_story": "Agua protonada. Define la acidez de soluciones.",
            "biological_presence": "Gradiente de protones impulsa síntesis de ATP.",
            "utility": "Motor de la vida: quimioósmosis."
        },
        "milestones": ["Gradiente Protónico"],
        "difficulty": 3,
        "discovery_points": 45,
        "family_color": [100, 200, 255]
    },
    
    # ==========================================================================
    # CARBONO SIMPLE (C1)
    # ==========================================================================
    "C1O1": {
        "names": {"es": "Monóxido de Carbono", "en": "Carbon Monoxide"},
        "lore": {
            "origin_story": "Segunda molécula más abundante en el espacio después de H2.",
            "biological_presence": "Tóxico - bloquea hemoglobina. Pero usado como señal celular.",
            "utility": "Trazador de nubes moleculares en astronomía."
        },
        "milestones": ["Molécula Interestelar", "Gas Venenoso"],
        "difficulty": 2,
        "discovery_points": 30,
        "family_color": [180, 180, 180]
    },
    "C1O2": {
        "names": {"es": "Dióxido de Carbono", "en": "Carbon Dioxide"},
        "lore": {
            "origin_story": "Producto de respiración y volcanes. Atmósfera de Venus y Marte.",
            "biological_presence": "Sustrato de fotosíntesis. Regulador del pH sanguíneo.",
            "utility": "Gas invernadero. Controla clima planetario."
        },
        "milestones": ["Efecto Invernadero", "Fotosíntesis"],
        "difficulty": 3,
        "discovery_points": 35,
        "family_color": [200, 200, 200]
    },
    "C1H4": {
        "names": {"es": "Metano", "en": "Methane"},
        "lore": {
            "origin_story": "Producido por arqueas metanógenas. Abundante en Titán.",
            "biological_presence": "Biofirma potencial. Lagos de metano en Titán.",
            "utility": "Combustible. Potente gas invernadero."
        },
        "milestones": ["Biofirma", "Lagos de Titán"],
        "difficulty": 3,
        "discovery_points": 55,
        "family_color": [150, 200, 150]
    },
    "C1H2O1": {
        "names": {"es": "Formaldehído", "en": "Formaldehyde"},
        "lore": {
            "origin_story": "Detectado en nubes moleculares. Clave en química prebiótica.",
            "biological_presence": "Precursor de azúcares por reacción formosa.",
            "utility": "Primer paso hacia carbohidratos complejos."
        },
        "milestones": ["Molécula Interestelar", "Precursor de Vida"],
        "difficulty": 3,
        "discovery_points": 75,
        "family_color": [255, 200, 150]
    },
    "C1H2O2": {
        "names": {"es": "Ácido Fórmico", "en": "Formic Acid"},
        "lore": {
            "origin_story": "El ácido orgánico más simple. Veneno de hormigas.",
            "biological_presence": "Producto de metabolismo. Defensa química de insectos.",
            "utility": "Conservante natural. Antibacteriano."
        },
        "milestones": ["Ácido Primordial", "Veneno de Hormiga"],
        "difficulty": 4,
        "discovery_points": 85,
        "family_color": [255, 180, 100]
    },
    "C1H3O1": {
        "names": {"es": "Radical Metoxilo", "en": "Methoxy Radical"},
        "lore": {
            "origin_story": "Fragmento reactivo en química atmosférica.",
            "biological_presence": "Intermedio en degradación de metanol.",
            "utility": "Oxidación de compuestos orgánicos."
        },
        "milestones": ["Química Atmosférica"],
        "difficulty": 4,
        "discovery_points": 40,
        "family_color": [255, 200, 180]
    },
    "C1H4O1": {
        "names": {"es": "Metanol", "en": "Methanol"},
        "lore": {
            "origin_story": "Alcohol más simple. Detectado en cometas y nebulosas.",
            "biological_presence": "Tóxico para humanos. Metabolizado a formaldehído.",
            "utility": "Combustible y solvente industrial."
        },
        "milestones": ["Alcohol Cósmico"],
        "difficulty": 4,
        "discovery_points": 65,
        "family_color": [200, 255, 200]
    },
    
    # ==========================================================================
    # CARBONO DOS (C2)
    # ==========================================================================
    "C2H2": {
        "names": {"es": "Acetileno", "en": "Acetylene"},
        "lore": {
            "origin_story": "Triple enlace C≡C. Detectado en atmósfera de Titán.",
            "biological_presence": "Precursor de anillos aromáticos.",
            "utility": "Combustible de soldadura. Síntesis orgánica."
        },
        "milestones": ["Triple Enlace", "Química de Titán"],
        "difficulty": 4,
        "discovery_points": 70,
        "family_color": [200, 180, 150]
    },
    "C2H4": {
        "names": {"es": "Etileno", "en": "Ethylene"},
        "lore": {
            "origin_story": "Primera hormona vegetal descubierta.",
            "biological_presence": "Señal de maduración. Respuesta a estrés en plantas.",
            "utility": "Precursor de polietileno. Madura frutas."
        },
        "milestones": ["Hormona Vegetal", "Maduración"],
        "difficulty": 3,
        "discovery_points": 60,
        "family_color": [150, 255, 150]
    },
    "C2H6": {
        "names": {"es": "Etano", "en": "Ethane"},
        "lore": {
            "origin_story": "Hidrocarburo saturado. Llueve etano en Titán.",
            "biological_presence": "Subproducto de fermentación.",
            "utility": "Combustible. Refrigerante criogénico."
        },
        "milestones": ["Lluvia de Titán"],
        "difficulty": 3,
        "discovery_points": 50,
        "family_color": [180, 220, 180]
    },
    "C2H6O1": {
        "names": {"es": "Etanol", "en": "Ethanol"},
        "lore": {
            "origin_story": "Producto de fermentación. Usado por humanos hace 9000 años.",
            "biological_presence": "Producido por levaduras. Tóxico en exceso.",
            "utility": "Bebidas alcohólicas. Combustible renovable."
        },
        "milestones": ["Fermentación", "Civilización"],
        "difficulty": 5,
        "discovery_points": 90,
        "family_color": [255, 220, 180]
    },
    "C2H4O1": {
        "names": {"es": "Acetaldehído", "en": "Acetaldehyde"},
        "lore": {
            "origin_story": "Intermedio en metabolismo del etanol.",
            "biological_presence": "Causa resaca. Carcinógeno.",
            "utility": "Síntesis de ácido acético."
        },
        "milestones": ["Metabolismo"],
        "difficulty": 4,
        "discovery_points": 55,
        "family_color": [255, 200, 180]
    },
    "C2H4O2": {
        "names": {"es": "Ácido Acético", "en": "Acetic Acid"},
        "lore": {
            "origin_story": "Vinagre. Producido por bacterias acetobacter.",
            "biological_presence": "Acetil-CoA es central en metabolismo.",
            "utility": "Conservante alimentario desde la antigüedad."
        },
        "milestones": ["Fermentación Acética", "Acetil-CoA"],
        "difficulty": 5,
        "discovery_points": 100,
        "family_color": [255, 200, 100]
    },
    "C2H2O1": {
        "names": {"es": "Cetena", "en": "Ketene"},
        "lore": {
            "origin_story": "Intermedio reactivo extremadamente inestable.",
            "biological_presence": "No existe libre en biología.",
            "utility": "Agente de acetilación en laboratorio."
        },
        "milestones": ["Reactivo Fugaz"],
        "difficulty": 6,
        "discovery_points": 90,
        "family_color": [200, 150, 200]
    },
    "C2H2O3": {
        "names": {"es": "Ácido Glioxílico", "en": "Glyoxylic Acid"},
        "lore": {
            "origin_story": "Intermedio del ciclo del glioxilato.",
            "biological_presence": "Permite a plantas metabolizar grasas.",
            "utility": "Síntesis de aminoácidos."
        },
        "milestones": ["Ciclo del Glioxilato"],
        "difficulty": 6,
        "discovery_points": 120,
        "family_color": [180, 220, 180]
    },
    
    # ==========================================================================
    # CARBONO TRES (C3) - PIRUVATOS Y GLICERALDEHÍDOS
    # ==========================================================================
    "C3H4": {
        "names": {"es": "Propino", "en": "Propyne"},
        "lore": {
            "origin_story": "Detectado en atmósfera de Titán por Cassini.",
            "biological_presence": "Precursor de anillos aromáticos.",
            "utility": "Síntesis de compuestos cíclicos."
        },
        "milestones": ["Química de Titán", "Triple Enlace"],
        "difficulty": 5,
        "discovery_points": 85,
        "family_color": [200, 180, 150]
    },
    "C3H4O3": {
        "names": {"es": "Ácido Pirúvico", "en": "Pyruvic Acid"},
        "lore": {
            "origin_story": "Producto final de glucólisis.",
            "biological_presence": "Encrucijada metabólica: fermentación o Krebs.",
            "utility": "Precursor de alanina y lactato."
        },
        "milestones": ["Glucólisis", "Encrucijada Metabólica"],
        "difficulty": 7,
        "discovery_points": 150,
        "family_color": [255, 180, 120]
    },
    "C3H6O3": {
        "names": {"es": "Ácido Láctico", "en": "Lactic Acid"},
        "lore": {
            "origin_story": "Producto de fermentación láctica.",
            "biological_presence": "Producido en músculo durante ejercicio intenso.",
            "utility": "Yogurt, queso. Polímeros biodegradables."
        },
        "milestones": ["Fermentación Láctica", "Ejercicio"],
        "difficulty": 6,
        "discovery_points": 110,
        "family_color": [255, 250, 200]
    },
    "C3H8O3": {
        "names": {"es": "Glicerol", "en": "Glycerol"},
        "lore": {
            "origin_story": "Columna vertebral de triglicéridos y fosfolípidos.",
            "biological_presence": "Componente de membranas celulares.",
            "utility": "Humectante. Anticongelante biológico."
        },
        "milestones": ["Membranas Celulares", "Lípidos"],
        "difficulty": 6,
        "discovery_points": 130,
        "family_color": [200, 255, 200]
    },
    
    # ==========================================================================
    # NITRÓGENO Y AMINAS
    # ==========================================================================
    "N1H3": {
        "names": {"es": "Amoníaco", "en": "Ammonia"},
        "lore": {
            "origin_story": "Abundante en planetas gigantes. Posible solvente alternativo.",
            "biological_presence": "Producto de degradación de aminoácidos. Tóxico.",
            "utility": "Fertilizante. Base en química."
        },
        "milestones": ["Nitrógeno Fijo", "Química de Júpiter"],
        "difficulty": 3,
        "discovery_points": 45,
        "family_color": [150, 200, 255]
    },
    "H1N1O3": {
        "names": {"es": "Ácido Nítrico", "en": "Nitric Acid"},
        "lore": {
            "origin_story": "Formado por rayos en atmósferas primitivas.",
            "biological_presence": "Fuente de nitrógeno reactivo.",
            "utility": "Fertilizante. Fijación de nitrógeno abiótica."
        },
        "milestones": ["Rayo Químico", "Nitrógeno Fijo"],
        "difficulty": 5,
        "discovery_points": 95,
        "family_color": [150, 150, 255]
    },
    "H1C1N1": {
        "names": {"es": "Ácido Cianhídrico", "en": "Hydrogen Cyanide"},
        "lore": {
            "origin_story": "Detectado en cometas. Clave en síntesis prebiótica.",
            "biological_presence": "Tóxico pero precursor de adenina.",
            "utility": "5 HCN → Adenina (base del ADN)."
        },
        "milestones": ["Química Prebiótica", "Cometas"],
        "difficulty": 5,
        "discovery_points": 100,
        "family_color": [200, 150, 255]
    },
    "C1H3N1": {
        "names": {"es": "Metilamina", "en": "Methylamine"},
        "lore": {
            "origin_story": "Amina más simple. Detectada en espacio interestelar.",
            "biological_presence": "Producto de descomposición de proteínas.",
            "utility": "Síntesis de fármacos."
        },
        "milestones": ["Aminas Simples"],
        "difficulty": 4,
        "discovery_points": 65,
        "family_color": [180, 180, 255]
    },
    "C1H5N1": {
        "names": {"es": "Metilamina", "en": "Methylamine"},
        "lore": {
            "origin_story": "La amina orgánica más simple.",
            "biological_presence": "Olor a pescado en descomposición.",
            "utility": "Precursor de aminoácidos."
        },
        "milestones": ["Química del Nitrógeno"],
        "difficulty": 4,
        "discovery_points": 60,
        "family_color": [180, 180, 255]
    },
    
    # ==========================================================================
    # AZUFRE
    # ==========================================================================
    "H2S1": {
        "names": {"es": "Sulfuro de Hidrógeno", "en": "Hydrogen Sulfide"},
        "lore": {
            "origin_story": "Gas volcánico. Olor a huevos podridos.",
            "biological_presence": "Usado por bacterias quimiolitótrofas en ventilas.",
            "utility": "Fotosíntesis alternativa sin oxígeno."
        },
        "milestones": ["Ventilas Hidrotermales", "Quimiosíntesis"],
        "difficulty": 3,
        "discovery_points": 55,
        "family_color": [255, 255, 100]
    },
    "C1H4S1": {
        "names": {"es": "Metanotiol", "en": "Methanethiol"},
        "lore": {
            "origin_story": "Tiol más simple. Olor a col podrida.",
            "biological_presence": "Biofirma potencial. Producido por bacterias.",
            "utility": "Odorante del gas natural."
        },
        "milestones": ["Aliento de Dragón", "Biofirma"],
        "difficulty": 4,
        "discovery_points": 70,
        "family_color": [255, 255, 100]
    },
    "C2H6S1": {
        "names": {"es": "Etanotiol", "en": "Ethanethiol"},
        "lore": {
            "origin_story": "Olor extremadamente fuerte. Se detecta a 1 ppb.",
            "biological_presence": "Señal de actividad microbiana.",
            "utility": "Odorante de seguridad en gas."
        },
        "milestones": ["Azufre Orgánico"],
        "difficulty": 5,
        "discovery_points": 75,
        "family_color": [255, 255, 120]
    },
    "C1H4S2": {
        "names": {"es": "Dimetil Disulfuro", "en": "Dimethyl Disulfide"},
        "lore": {
            "origin_story": "Producido en descomposición.",
            "biological_presence": "Atractante de moscas carroñeras.",
            "utility": "Señal de muerte y descomposición."
        },
        "milestones": ["Ciclo del Azufre"],
        "difficulty": 5,
        "discovery_points": 80,
        "family_color": [255, 230, 100]
    },
    
    # ==========================================================================
    # FÓSFORO - ENERGÍA Y GENÉTICA
    # ==========================================================================
    "H3O4P1": {
        "names": {"es": "Ácido Fosfórico", "en": "Phosphoric Acid"},
        "lore": {
            "origin_story": "Liberado de apatita por meteorización.",
            "biological_presence": "Columna vertebral del ADN. Componente de ATP.",
            "utility": "La molécula más importante para la vida."
        },
        "milestones": ["Energía Universal", "Código Genético"],
        "difficulty": 7,
        "discovery_points": 180,
        "family_color": [255, 150, 100]
    },
    "H3P1O4": {
        "names": {"es": "Ácido Fosfórico", "en": "Phosphoric Acid"},
        "lore": {
            "origin_story": "Forma ortofosfato en solución.",
            "biological_presence": "Pi inorgánico - sustrato de fosforilación.",
            "utility": "Fertilizante. Componente de refrescos."
        },
        "milestones": ["Fosfato Inorgánico"],
        "difficulty": 6,
        "discovery_points": 150,
        "family_color": [255, 150, 100]
    },
    
    # ==========================================================================
    # SILICIO - QUÍMICA ALTERNATIVA
    # ==========================================================================
    "Si1H4": {
        "names": {"es": "Silano", "en": "Silane"},
        "lore": {
            "origin_story": "Análogo de silicio del metano.",
            "biological_presence": "Teóricamente posible vida basada en silicio.",
            "utility": "Industria de semiconductores."
        },
        "milestones": ["Silicio Exótico", "Vida Alternativa"],
        "difficulty": 6,
        "discovery_points": 100,
        "family_color": [200, 200, 200]
    },
    "Si1O2": {
        "names": {"es": "Dióxido de Silicio", "en": "Silicon Dioxide"},
        "lore": {
            "origin_story": "Cuarzo. Componente principal de arena y rocas.",
            "biological_presence": "Diatomeas construyen conchas de sílice.",
            "utility": "Vidrio. Electrónica."
        },
        "milestones": ["Mineral Fundamental"],
        "difficulty": 4,
        "discovery_points": 60,
        "family_color": [220, 220, 220]
    },
    
    # ==========================================================================
    # RADICALES IMPORTANTES
    # ==========================================================================
    "O1H1": {
        "names": {"es": "Radical Hidroxilo", "en": "Hydroxyl Radical"},
        "lore": {
            "origin_story": "El oxidante más reactivo de la naturaleza.",
            "biological_presence": "Daña ADN. Causa envejecimiento.",
            "utility": "Limpia la atmósfera de contaminantes."
        },
        "milestones": ["Radical Libre", "Estrés Oxidativo"],
        "difficulty": 5,
        "discovery_points": 70,
        "family_color": [255, 150, 150]
    },
    "H1O1": {
        "names": {"es": "Radical Hidroxilo", "en": "Hydroxyl Radical"},
        "lore": {
            "origin_story": "Formado por radiólisis del agua.",
            "biological_presence": "Altamente reactivo. Vida media de nanosegundos.",
            "utility": "Detergente atmosférico."
        },
        "milestones": ["Química Radical"],
        "difficulty": 5,
        "discovery_points": 65,
        "family_color": [255, 150, 150]
    },
    "C1H3": {
        "names": {"es": "Radical Metilo", "en": "Methyl Radical"},
        "lore": {
            "origin_story": "Fragmento de metano. Muy reactivo.",
            "biological_presence": "Metilación de ADN regula genes.",
            "utility": "Epigenética."
        },
        "milestones": ["Metilación", "Epigenética"],
        "difficulty": 4,
        "discovery_points": 55,
        "family_color": [180, 255, 180]
    },
    
    # ==========================================================================
    # AMINOÁCIDOS PRECURSORES
    # ==========================================================================
    "C2H5N1O2": {
        "names": {"es": "Glicina", "en": "Glycine"},
        "lore": {
            "origin_story": "El aminoácido más simple. Detectado en cometa 67P.",
            "biological_presence": "Componente de todas las proteínas.",
            "utility": "Primer paso hacia las proteínas."
        },
        "milestones": ["Aminoácido Primordial", "Cometa 67P"],
        "difficulty": 7,
        "discovery_points": 200,
        "family_color": [255, 200, 255]
    },
    "C3H7N1O2": {
        "names": {"es": "Alanina", "en": "Alanine"},
        "lore": {
            "origin_story": "Aminoácido no esencial. Encontrado en meteoritos.",
            "biological_presence": "Segundo aminoácido más común en proteínas.",
            "utility": "Gluconeogénesis. Ciclo alanina-glucosa."
        },
        "milestones": ["Meteoritos", "Quiralidad"],
        "difficulty": 8,
        "discovery_points": 220,
        "family_color": [255, 180, 255]
    },
    
    # ==========================================================================
    # NUCLEOBASES
    # ==========================================================================
    "C5H5N5": {
        "names": {"es": "Adenina", "en": "Adenine"},
        "lore": {
            "origin_story": "Formada de 5 moléculas de HCN. Detectada en meteoritos.",
            "biological_presence": "Base del ADN. Parte del ATP.",
            "utility": "Almacena información genética y energía."
        },
        "milestones": ["Código Genético", "ATP"],
        "difficulty": 9,
        "discovery_points": 300,
        "family_color": [100, 200, 100]
    },
    "C4H5N3O1": {
        "names": {"es": "Citosina", "en": "Cytosine"},
        "lore": {
            "origin_story": "Pirimidina. Sintetizada en experimentos prebióticos.",
            "biological_presence": "Base del ADN. Se aparea con guanina.",
            "utility": "Complementariedad del código genético."
        },
        "milestones": ["Código Genético"],
        "difficulty": 9,
        "discovery_points": 280,
        "family_color": [100, 180, 100]
    },
    
    # ==========================================================================
    # AZÚCARES
    # ==========================================================================
    "C6H12O6": {
        "names": {"es": "Glucosa", "en": "Glucose"},
        "lore": {
            "origin_story": "Formada por fotosíntesis. Combustible universal.",
            "biological_presence": "Fuente primaria de energía celular.",
            "utility": "Glucólisis produce ATP."
        },
        "milestones": ["Fotosíntesis", "Glucólisis"],
        "difficulty": 10,
        "discovery_points": 400,
        "family_color": [255, 255, 200]
    },
    "C5H10O5": {
        "names": {"es": "Ribosa", "en": "Ribose"},
        "lore": {
            "origin_story": "Azúcar del ARN. Síntesis formosa.",
            "biological_presence": "Componente del ARN y ATP.",
            "utility": "Mundo del ARN - origen de la vida."
        },
        "milestones": ["Mundo ARN"],
        "difficulty": 9,
        "discovery_points": 350,
        "family_color": [255, 240, 180]
    },
    "C5H10O4": {
        "names": {"es": "Desoxirribosa", "en": "Deoxyribose"},
        "lore": {
            "origin_story": "Azúcar del ADN. Sin oxígeno en posición 2.",
            "biological_presence": "Más estable que ribosa → ADN como archivo.",
            "utility": "Almacenamiento genético permanente."
        },
        "milestones": ["ADN", "Herencia"],
        "difficulty": 9,
        "discovery_points": 360,
        "family_color": [255, 240, 160]
    },
    
    # ==========================================================================
    # SULFURANO Y COMPUESTOS EXÓTICOS
    # ==========================================================================
    "H4S1": {
        "names": {"es": "Sulfurano", "en": "Sulfurane"},
        "lore": {
            "origin_story": "Compuesto hipervalente de azufre.",
            "biological_presence": "Intermedio en reacciones enzimáticas.",
            "utility": "Química avanzada del azufre."
        },
        "milestones": ["Azufre Hipervalente"],
        "difficulty": 8,
        "discovery_points": 130,
        "family_color": [255, 255, 150]
    },
    "C1O2S1": {
        "names": {"es": "Sulfuro de Carbonilo", "en": "Carbonyl Sulfide"},
        "lore": {
            "origin_story": "Gas volcánico. El compuesto de azufre más abundante en atmósfera.",
            "biological_presence": "Puede catalizar formación de péptidos.",
            "utility": "Catalizador prebiótico de proteínas."
        },
        "milestones": ["Volcanes", "Catálisis Prebiótica"],
        "difficulty": 6,
        "discovery_points": 110,
        "family_color": [255, 230, 100]
    }
}

# Heuristic rules for auto-generating lore
def generate_lore_heuristic(formula, atoms):
    """Generate lore based on molecular composition."""
    C = atoms.get("C", 0)
    H = atoms.get("H", 0)
    N = atoms.get("N", 0)
    O = atoms.get("O", 0)
    P = atoms.get("P", 0)
    S = atoms.get("S", 0)
    Si = atoms.get("Si", 0)
    total = sum(atoms.values())
    
    # Origin story based on composition
    origins = []
    if P > 0 and O >= 2:
        origins.append("Forma parte de la familia de los fosfatos")
    if S > 0 and C > 0:
        origins.append("Compuesto organosulfurado")
    if N > 0 and C > 0:
        origins.append("Contiene nitrógeno orgánico")
    if Si > 0:
        origins.append("Compuesto de silicio, raro en química biológica")
    if C > 0 and O > 0 and H > 0:
        origins.append("Molécula orgánica oxigenada")
    if not origins:
        origins.append("Fragmento molecular transitorio")
    
    origin_story = ". ".join(origins) + "."
    
    # Biological presence
    bio = []
    if P > 0:
        bio.append("Relevante para almacenamiento de energía")
    if N > 0 and C > 0:
        bio.append("Precursor potencial de aminoácidos")
    if S > 0:
        bio.append("Participa en reacciones redox")
    if C >= 3 and N > 0 and O > 0:
        bio.append("Estructura similar a metabolitos")
    if not bio:
        bio.append("Sin rol biológico conocido")
    
    biological_presence = ". ".join(bio) + "."
    
    # Utility
    utility = []
    if P > 0 and O > 0:
        utility.append("Potencial como molécula energética")
    if C >= 2 and N > 0:
        utility.append("Precursor de compuestos nitrogenados")
    if S > 0 and C > 0:
        utility.append("Química del azufre orgánico")
    if total > 10:
        utility.append("Molécula compleja con potencial catalítico")
    if not utility:
        utility.append("Fragmento reactivo transitorio")
    
    return {
        "origin_story": origin_story,
        "biological_presence": biological_presence,
        "utility": ". ".join(utility) + "."
    }

def generate_name_heuristic(formula, atoms):
    """Generate a scientific-sounding name based on composition."""
    C = atoms.get("C", 0)
    H = atoms.get("H", 0)
    N = atoms.get("N", 0)
    O = atoms.get("O", 0)
    P = atoms.get("P", 0)
    S = atoms.get("S", 0)
    Si = atoms.get("Si", 0)
    
    prefixes = {
        1: "Mono", 2: "Di", 3: "Tri", 4: "Tetra",
        5: "Penta", 6: "Hexa", 7: "Hepta", 8: "Octo"
    }
    
    parts = []
    
    # Carbon chain naming
    if C > 0:
        carbon_names = {1: "Met", 2: "Et", 3: "Prop", 4: "But", 5: "Pent", 6: "Hex"}
        parts.append(carbon_names.get(C, f"C{C}"))
    
    # Functional groups
    if P > 0:
        parts.append("fosfo" if P == 1 else f"{prefixes.get(P, str(P))}fosfo")
    if S > 0:
        parts.append("tio" if S == 1 else f"{prefixes.get(S, str(S))}tio")
    if N > 0:
        parts.append("amino" if N == 1 else f"{prefixes.get(N, str(N))}amino")
    if Si > 0:
        parts.append("sila")
    
    # Endings
    if O > 0 and H > 0:
        endings = ["ol", "al", "oico", "ato", "ina"]
        ending = endings[O % len(endings)]
    else:
        ending = "ano"
    
    if parts:
        name = "-".join(parts[:2]) + ending
    else:
        name = f"Compuesto-{formula}"
    
    return name.capitalize()

def generate_milestones(atoms):
    """Generate appropriate milestones based on composition."""
    milestones = []
    C = atoms.get("C", 0)
    N = atoms.get("N", 0)
    O = atoms.get("O", 0)
    P = atoms.get("P", 0)
    S = atoms.get("S", 0)
    Si = atoms.get("Si", 0)
    total = sum(atoms.values())
    
    if P > 0 and O >= 2:
        milestones.append("Química del Fósforo")
    if N > 0 and C > 0:
        milestones.append("Nitrógeno Orgánico")
    if S > 0:
        milestones.append("Química del Azufre")
    if Si > 0:
        milestones.append("Silicio Exótico")
    if total > 15:
        milestones.append("Molécula Compleja")
    if C >= 4 and N > 0 and O > 0:
        milestones.append("Precursor Prebiótico")
    
    if not milestones:
        milestones.append("Descubrimiento Emergente")
    
    return milestones

def calculate_difficulty(atoms):
    """Calculate synthesis difficulty."""
    total = sum(atoms.values())
    unique_elements = len(atoms)
    
    if total < 4:
        return 1
    elif total < 8:
        return 2 + unique_elements
    elif total < 15:
        return 4 + unique_elements
    else:
        return min(10, 6 + unique_elements)

def calculate_discovery_points(atoms, is_significant):
    """Calculate discovery points."""
    base = sum(atoms.values()) * 5
    
    # Bonuses
    if atoms.get("P", 0) > 0:
        base += 30  # Phosphorus is rare
    if atoms.get("N", 0) > 0 and atoms.get("C", 0) > 0:
        base += 20  # Organic nitrogen
    if atoms.get("S", 0) > 0:
        base += 15  # Sulfur chemistry
    if is_significant:
        base *= 1.5
    
    return int(base)

def get_family_color(atoms):
    """Get color based on molecular family."""
    if atoms.get("P", 0) > 0:
        return [255, 150, 100]  # Orange for phosphates
    if atoms.get("S", 0) > 0:
        return [255, 255, 100]  # Yellow for sulfur
    if atoms.get("N", 0) > 0:
        return [150, 150, 255]  # Blue for nitrogen
    if atoms.get("Si", 0) > 0:
        return [200, 200, 200]  # Grey for silicon
    if atoms.get("O", 0) > 0:
        return [255, 200, 200]  # Light red for oxygen
    return [180, 180, 180]  # Default grey

def parse_formula(formula):
    """Parse chemical formula into atom counts."""
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, formula)
    atoms = {}
    for element, count in matches:
        if element:
            atoms[element] = int(count) if count else 1
    return atoms

def enrich_molecule(formula, data):
    """Enrich a single molecule with full lore."""
    atoms = parse_formula(formula)
    
    # Check if we have known data
    if formula in KNOWN_MOLECULES:
        known = KNOWN_MOLECULES[formula]
        return {
            "identity": {
                "formula": formula,
                "names": known["names"],
                "category": "discovered",
                "family_color": known["family_color"]
            },
            "lore": known["lore"],
            "gameplay": {
                "milestones": known["milestones"],
                "discovery_points": known["discovery_points"],
                "difficulty": known["difficulty"],
                "times_synthesized": data.get("count", 1)
            },
            "status": {
                "is_significant": data.get("is_significant", False),
                "first_discovery": data.get("first_discovery", 0)
            }
        }
    
    # Generate for unknown molecules
    is_significant = data.get("is_significant", False)
    current_name = data.get("name", "")
    
    # Determine if we need to generate a name
    if current_name in ["Transitorio", "[Nombre Sugerido]", "Desconocida"] or "Residuo" in current_name:
        name_es = generate_name_heuristic(formula, atoms)
        name_en = name_es  # Simplified
    else:
        name_es = current_name
        name_en = current_name
    
    return {
        "identity": {
            "formula": formula,
            "names": {"es": name_es, "en": name_en},
            "category": "emergent",
            "family_color": get_family_color(atoms)
        },
        "lore": generate_lore_heuristic(formula, atoms),
        "gameplay": {
            "milestones": generate_milestones(atoms),
            "discovery_points": calculate_discovery_points(atoms, is_significant),
            "difficulty": calculate_difficulty(atoms),
            "times_synthesized": data.get("count", 1)
        },
        "status": {
            "is_significant": is_significant,
            "first_discovery": data.get("first_discovery", 0)
        }
    }

def main():
    print("=" * 60)
    print("MOLECULE LORE ENRICHMENT")
    print("=" * 60)
    
    # Load player molecules
    try:
        with open(PLAYER_MOLECULES, "r", encoding="utf-8") as f:
            player_mols = json.load(f)
    except Exception as e:
        print(f"Error loading player molecules: {e}")
        return
    
    print(f"Loaded {len(player_mols)} player molecules")
    
    # Filter out transitorios and trash
    significant_mols = {}
    trash_count = 0
    
    for formula, data in player_mols.items():
        name = data.get("name", "")
        # Skip aggregates and pure transitorios
        if formula.startswith("AGGREGATE"):
            continue
        if name == "Transitorio" and data.get("count", 0) < 5:
            trash_count += 1
            continue
        if "Residuo Inestable" in name:
            trash_count += 1
            continue
            
        significant_mols[formula] = data
    
    print(f"Filtered to {len(significant_mols)} significant molecules")
    print(f"Skipped {trash_count} transient/unstable molecules")
    
    # Enrich each molecule
    enriched = {"molecules": {}}
    known_count = 0
    generated_count = 0
    
    for formula, data in significant_mols.items():
        enriched_mol = enrich_molecule(formula, data)
        enriched["molecules"][formula] = enriched_mol
        
        if formula in KNOWN_MOLECULES:
            known_count += 1
        else:
            generated_count += 1
    
    # Add metadata
    enriched["_meta"] = {
        "total_molecules": len(enriched["molecules"]),
        "known_with_full_lore": known_count,
        "auto_generated": generated_count,
        "source": "player_discoveries"
    }
    
    # Save enriched data
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)
    
    print(f"\nSaved enriched molecules to: {OUTPUT_PATH}")
    print(f"  - Known molecules with full lore: {known_count}")
    print(f"  - Auto-generated lore: {generated_count}")
    
    # Print some examples
    print("\n" + "=" * 60)
    print("SAMPLE ENRICHED MOLECULES:")
    print("=" * 60)
    
    count = 0
    for formula, mol in enriched["molecules"].items():
        if count >= 5:
            break
        print(f"\n[{formula}] {mol['identity']['names']['es']}")
        print(f"  Origin: {mol['lore']['origin_story']}")
        print(f"  Milestones: {', '.join(mol['gameplay']['milestones'])}")
        print(f"  Points: {mol['gameplay']['discovery_points']}")
        count += 1

if __name__ == "__main__":
    main()
