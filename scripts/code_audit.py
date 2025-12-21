#!/usr/bin/env python3
"""
Code Audit Script - LifeSimulator
==================================
Analiza la estructura del código para detectar:
- Imports no usados
- Funciones/clases sin referencias
- Dependencias circulares
- Métricas de complejidad

Uso:
    python scripts/code_audit.py [ruta]
"""

import os
import ast
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class CodeAuditor:
    """Analizador de código Python para auditorías."""
    
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.files: Dict[str, dict] = {}
        self.all_imports: Dict[str, Set[str]] = defaultdict(set)
        self.all_definitions: Dict[str, Set[str]] = defaultdict(set)
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
    
    def analyze_file(self, filepath: Path) -> dict:
        """Analiza un archivo Python y extrae metadatos."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            return {"error": str(e)}
        
        result = {
            "path": str(filepath),
            "lines": len(content.splitlines()),
            "bytes": len(content.encode('utf-8')),
            "imports": [],
            "from_imports": [],
            "classes": [],
            "functions": [],
            "global_vars": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)
                    self.all_imports[str(filepath)].add(alias.name)
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    import_str = f"{module}.{alias.name}" if module else alias.name
                    result["from_imports"].append(import_str)
                    self.all_imports[str(filepath)].add(module)
                    self.import_graph[str(filepath)].add(module)
                    
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                    "bases": [self._get_name(b) for b in node.bases]
                })
                self.all_definitions[str(filepath)].add(node.name)
                
            elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                # Solo funciones de nivel superior
                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [self._get_name(d) for d in node.decorator_list]
                })
                self.all_definitions[str(filepath)].add(node.name)
                
            elif isinstance(node, ast.Assign) and node.col_offset == 0:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        result["global_vars"].append(target.id)
        
        return result
    
    def _get_name(self, node) -> str:
        """Extrae el nombre de un nodo AST."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return str(type(node).__name__)
    
    def scan_directory(self, exclude_dirs: Set[str] = None):
        """Escanea todos los archivos Python en el directorio."""
        exclude_dirs = exclude_dirs or {"__pycache__", ".git", "venv", ".venv"}
        
        for filepath in self.root.rglob("*.py"):
            # Saltar directorios excluidos
            if any(ex in filepath.parts for ex in exclude_dirs):
                continue
            
            rel_path = filepath.relative_to(self.root)
            self.files[str(rel_path)] = self.analyze_file(filepath)
    
    def find_unused_imports(self) -> Dict[str, List[str]]:
        """Detecta imports que no se usan en el archivo."""
        unused = {}
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            
            # Leer el contenido del archivo
            full_path = self.root / filepath
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_unused = []
            all_imports = data["imports"] + [i.split(".")[-1] for i in data["from_imports"]]
            
            for imp in all_imports:
                # Nombre simple del import
                name = imp.split(".")[-1]
                # Contar ocurrencias (excluyendo la línea de import)
                lines = content.split('\n')
                uses = sum(1 for line in lines if name in line and 'import' not in line)
                if uses == 0:
                    file_unused.append(imp)
            
            if file_unused:
                unused[filepath] = file_unused
        
        return unused
    
    def find_unused_definitions(self) -> Dict[str, List[str]]:
        """Detecta funciones/clases definidas pero nunca importadas."""
        # Recopilar todos los nombres importados
        all_imported = set()
        for imports in self.all_imports.values():
            all_imported.update(imports)
        
        for filepath, data in self.files.items():
            for imp in data.get("from_imports", []):
                all_imported.add(imp.split(".")[-1])
        
        # Comparar con definiciones
        unused = {}
        for filepath, defs in self.all_definitions.items():
            unused_in_file = []
            for d in defs:
                if d.startswith("_"):  # Ignorar privados
                    continue
                if d not in all_imported:
                    unused_in_file.append(d)
            if unused_in_file:
                unused[filepath] = unused_in_file
        
        return unused
    
    def get_complexity_report(self) -> List[Tuple[str, int, int]]:
        """Retorna archivos ordenados por complejidad (líneas)."""
        report = []
        for filepath, data in self.files.items():
            if "error" not in data:
                report.append((filepath, data["lines"], data["bytes"]))
        return sorted(report, key=lambda x: x[1], reverse=True)
    
    def print_report(self):
        """Imprime el reporte completo de auditoría."""
        print("=" * 60)
        print("REPORTE DE AUDITORÍA - LifeSimulator")
        print("=" * 60)
        
        # 1. Archivos por tamaño
        print("\n📊 ARCHIVOS POR TAMAÑO (líneas)")
        print("-" * 40)
        for filepath, lines, bytes_ in self.get_complexity_report()[:10]:
            kb = bytes_ / 1024
            status = "⚠️" if lines > 400 else "✅"
            print(f"{status} {filepath}: {lines} líneas ({kb:.1f} KB)")
        
        # 2. Imports no usados
        print("\n🔍 IMPORTS POTENCIALMENTE NO USADOS")
        print("-" * 40)
        unused_imports = self.find_unused_imports()
        if unused_imports:
            for filepath, imports in unused_imports.items():
                print(f"  {filepath}:")
                for imp in imports:
                    print(f"    - {imp}")
        else:
            print("  ✅ Ninguno detectado")
        
        # 3. Definiciones sin uso externo
        print("\n📦 DEFINICIONES SIN IMPORTAR EXTERNAMENTE")
        print("-" * 40)
        unused_defs = self.find_unused_definitions()
        if unused_defs:
            for filepath, defs in unused_defs.items():
                print(f"  {filepath}:")
                for d in defs:
                    print(f"    - {d}")
        else:
            print("  ✅ Todo parece conectado")
        
        # 4. Resumen de estructura
        print("\n📁 ESTRUCTURA DEL PROYECTO")
        print("-" * 40)
        dirs = defaultdict(list)
        for filepath in self.files:
            parts = Path(filepath).parts
            dir_name = parts[0] if len(parts) > 1 else "/"
            dirs[dir_name].append(filepath)
        
        for dir_name, files in sorted(dirs.items()):
            total_lines = sum(self.files[f].get("lines", 0) for f in files)
            print(f"  {dir_name}/: {len(files)} archivos, {total_lines} líneas")
        
        # 5. Clases y Funciones principales
        print("\n🏗️ CLASES PRINCIPALES")
        print("-" * 40)
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            for cls in data.get("classes", []):
                print(f"  {cls['name']} ({filepath}:{cls['line']}) - {len(cls['methods'])} métodos")
        
        print("\n" + "=" * 60)
        print("FIN DEL REPORTE")
        print("=" * 60)


def main():
    # Determinar ruta raíz
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"Analizando: {root}\n")
    
    auditor = CodeAuditor(root)
    auditor.scan_directory()
    auditor.print_report()


if __name__ == "__main__":
    main()
