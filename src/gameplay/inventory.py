"""
Molecule Inventory (Quimidex)
============================
Gestiona la colección de moléculas descubiertas por el jugador.
Persistencia en JSON para guardar el progreso entre sesiones.
"""
import os
import json
import time

class MoleculeInventory:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MoleculeInventory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.save_path = os.path.join(os.getcwd(), "data", "player_molecules.json")
        self.discovered_molecules = {}  # {formula: {name, count, first_discovery_time}}
        self._needs_refresh = False     # Dirty flag for UI
        self.load()
        self._initialized = True
        
    def load(self):
        """Carga el inventario desde disco y sincroniza nombres con la DB global."""
        from src.config.molecules import get_molecule_name, load_molecule_database
        
        # Asegurar que la DB global esté lista antes de sincronizar
        load_molecule_database()

        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Sincronización automática de nombres y Consolidación de Macros
                    updated = False
                    to_consolidate = [] # List of (formula, data) to merge into AGGREGATE_AMORPHOUS

                    for formula, m_data in list(data.items()):
                        current_name = m_data.get("name", "Transitorio")
                        real_name = get_molecule_name(formula)
                        
                        # Consolidación: Si es un agregado y no es la clave maestra, marcar para fusión
                        if real_name == "Agregado Orgánico Amorfo" and formula != "AGGREGATE_AMORPHOUS":
                            to_consolidate.append((formula, m_data))
                            continue

                        # Actualizar si el nombre ha cambiado
                        is_generic = real_name in ["Desconocida", "Transitorio", "Transitorio Inestable"]
                        was_generic = current_name in ["Desconocida", "Transitorio"]
                        
                        if real_name != current_name:
                            if not is_generic or (is_generic and was_generic):
                                m_data["name"] = real_name
                                if not is_generic:
                                    m_data["is_significant"] = False
                                updated = True
                    
                    # Ejecutar consolidación
                    if to_consolidate:
                        if "AGGREGATE_AMORPHOUS" not in data:
                            # Inicializar clave maestra si no existe
                            first_entry = to_consolidate[0][1]
                            data["AGGREGATE_AMORPHOUS"] = {
                                "name": "Agregado Orgánico Amorfo",
                                "count": 0,
                                "first_discovery": first_entry.get("first_discovery", time.time()),
                                "is_significant": False,
                                "unlocked_traits": []
                            }
                        
                        master = data["AGGREGATE_AMORPHOUS"]
                        for f, d in to_consolidate:
                            master["count"] += d.get("count", 1)
                            # Quedarse con el descubrimiento más antiguo
                            if d.get("first_discovery", float('inf')) < master["first_discovery"]:
                                master["first_discovery"] = d["first_discovery"]
                            del data[f] # Eliminar entrada individual
                        
                        updated = True
                        print(f"[INVENTORY] 🧩 Consolidadas {len(to_consolidate)} variantes de Agregado.")

                    self.discovered_molecules = data
                    
                    if updated:
                        print(f"[INVENTORY] 🔄 Inventario sincronizado y optimizado.")
                        self.save()
                    
                    print(f"[INVENTORY] Cargadas {len(self.discovered_molecules)} moléculas.")
            except Exception as e:
                print(f"[ERROR] Error cargando inventario: {e}")
                self.discovered_molecules = {}
    
    def save(self):
        """Guarda el inventario y exporta lista de auditoría."""
        # Asegurar directorio
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(self.discovered_molecules, f, indent=4)
            
            # Exportar lista de auditoría (Desconocidas)
            self.export_audit_list()
        except Exception as e:
            print(f"[ERROR] Error guardando inventario: {e}")

    def export_audit_list(self):
        """Exporta moléculas desconocidas y anomalías usando el sistema centralizado de metadatos."""
        from src.config.molecules import export_unknown_molecules
        
        unknowns = self.get_audit_list()
        if not unknowns:
            return

        # El sistema forense de molecules.py se encarga de clasificar glitches (>64 at)
        # y generar un reporte detallado en data/unknown_molecules.json
        export_unknown_molecules(set(unknowns.keys()))

    def register_discovery(self, formula: str, real_name: str = "Transitorio"):
        """
        Registra una nueva molécula o actualiza el contador.
        Retorna True si es un descubrimiento nuevo.
        """
        is_new = False
        
        # Redirección de macros para consolidación inmediata
        from src.config.molecules import get_molecule_name
        actual_name = get_molecule_name(formula)
        target_key = formula
        
        if actual_name == "Agregado Orgánico Amorfo":
            target_key = "AGGREGATE_AMORPHOUS"

        if target_key not in self.discovered_molecules:
            self.discovered_molecules[target_key] = {
                "name": actual_name,
                "count": 1,
                "first_discovery": time.time(),
                "is_significant": actual_name not in ["Desconocida", "Transitorio"],
                "unlocked_traits": []
            }
            is_new = True
            print(f"[INVENTORY] ✨ ¡Nuevo descubrimiento!: {actual_name} ({formula})")
        else:
            self.discovered_molecules[target_key]["count"] += 1
            # Sincronizar nombre si era genérico y ahora tenemos uno real
            if self.discovered_molecules[target_key]["name"] in ["Desconocida", "Transitorio"] and actual_name not in ["Desconocida", "Transitorio"]:
                self.discovered_molecules[target_key]["name"] = actual_name
                self.discovered_molecules[target_key]["is_significant"] = True

        self._needs_refresh = True
        self.save()
        return is_new

    def check_and_reset_refresh(self) -> bool:
        """Consulta si la UI necesita refrescarse y resetea el flag."""
        if self._needs_refresh:
            self._needs_refresh = False
            return True
        return False

    def get_collection(self):
        """Retorna lista de descubrimientos."""
        return self.discovered_molecules
    
    def get_named_only(self):
        """Retorna solo moléculas con nombre real o significativas (Desconocidas)."""
        return {
            formula: data for formula, data in self.discovered_molecules.items()
            if data.get("name", "Transitorio") != "Transitorio"
        }
    
    def get_audit_list(self):
        """Retorna lista de moléculas marcadas como Desconocida para auditar."""
        return {
            formula: data for formula, data in self.discovered_molecules.items()
            if data.get("name") == "Desconocida"
        }
    
    def get_transitory_count(self):
        """Cuenta moléculas transitorias."""
        return sum(1 for data in self.discovered_molecules.values() 
                   if data.get("name", "Transitorio") == "Transitorio")
    
    def clear_transitory(self):
        """Elimina moléculas transitorias del inventario."""
        before = len(self.discovered_molecules)
        self.discovered_molecules = {
            f: d for f, d in self.discovered_molecules.items()
            if d.get("name", "Transitorio") != "Transitorio"
        }
        removed = before - len(self.discovered_molecules)
        self.save()
        return removed

def get_inventory():
    return MoleculeInventory()
