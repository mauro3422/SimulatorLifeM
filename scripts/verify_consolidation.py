
import os
import json
import sys

# Añadir el directorio raíz al path para importar src
sys.path.append(os.getcwd())

from src.gameplay.inventory import MoleculeInventory
from src.config.molecules import load_molecule_database

def verify_consolidation():
    print("--- INICIANDO VERIFICACIÓN DE CONSOLIDACIÓN ---")
    
    # Cargar DB global primero
    load_molecule_database()
    
    # Instanciar inventario (esto disparará el load() con la nueva lógica)
    inventory = MoleculeInventory()
    inventory.load() # Forzar carga para asegurar que se ejecute la lógica
    
    mols = inventory.get_collection()
    
    # Buscar duplicados con el nombre de Agregado
    aggregates = [f for f, d in mols.items() if d.get('name') == "Agregado Orgánico Amorfo"]
    
    print(f"Entradas encontradas con nombre 'Agregado Orgánico Amorfo': {len(aggregates)}")
    for f in aggregates:
        print(f" - Clave: {f}, Conteo: {mols[f].get('count')}")
    
    if len(aggregates) == 1 and aggregates[0] == "AGGREGATE_AMORPHOUS":
        print("✅ ÉXITO: Los agregados han sido consolidados bajo AGGREGATE_AMORPHOUS.")
        print(f"Total de hallazgos acumulados: {mols['AGGREGATE_AMORPHOUS'].get('count')}")
    else:
        print("❌ ERROR: Aún existen duplicados o la clave maestra no existe.")

if __name__ == "__main__":
    verify_consolidation()
