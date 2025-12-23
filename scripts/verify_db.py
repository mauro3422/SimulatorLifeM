from src.config.molecules import load_molecule_database, get_all_known_molecules

def test_load():
    success = load_molecule_database("es")
    if success:
        db = get_all_known_molecules()
        print(f"Total moléculas cargadas: {len(db)}")
        for formula in db:
            print(f"- {formula}")
    else:
        print("Error al cargar la base de datos.")

if __name__ == "__main__":
    test_load()
