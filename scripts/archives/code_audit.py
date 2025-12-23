#!/usr/bin/env python3
"""
Code Audit Script v3.0 - LifeSimulator
=======================================
Analiza la estructura del código para detectar:
- Imports no usados
- Funciones/clases sin referencias
- Métricas de complejidad
- Tamaños de archivos y líneas
- Patrones de comentarios (secciones, TODO, FIXME, etc.)

IMPORTANTE: La salida se guarda en 'scripts/audit_report.txt'

Uso:
    python scripts/code_audit.py [ruta]
"""

import os
import ast
import sys
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from datetime import datetime


# ===================================================================
# PATRONES DE COMENTARIOS RECONOCIDOS
# ===================================================================
# Estos patrones se detectan automáticamente en el código

COMMENT_PATTERNS = {
    # Secciones (===)
    "section": r"^#\s*={3,}.*$",
    "section_title": r"^#\s+[A-Z][A-Z\s]+$",
    
    # Prioridades
    "critical": r"#\s*(!{3}|CRITICAL|DANGER|SECURITY)",
    "warning": r"#\s*(!{2}|WARNING|WARN|CAUTION)",
    "important": r"#\s*(!{1}|IMPORTANT|NOTE)",
    
    # Tareas
    "todo": r"#\s*(TODO|FIXME|HACK|XXX|BUG)",
    "optimize": r"#\s*(OPTIMIZE|PERF|SLOW)",
    "refactor": r"#\s*(REFACTOR|CLEANUP|DEAD)",
    
    # Documentación
    "docstring_start": r'^"""',
    "api": r"#\s*(API|PUBLIC|EXPORTED)",
}


class CodeAuditor:
    """Analizador de código Python para auditorías."""
    
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.files: Dict[str, dict] = {}
        self.all_imports: Dict[str, Set[str]] = defaultdict(set)
        self.all_definitions: Dict[str, Set[str]] = defaultdict(set)
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.total_lines = 0
        self.total_bytes = 0
        self.output_lines = []
        self.comment_findings: Dict[str, List[dict]] = defaultdict(list)
    
    def _print(self, text: str = ""):
        """Imprime y guarda en buffer."""
        print(text)
        self.output_lines.append(text)
    
    def analyze_file(self, filepath: Path) -> dict:
        """Analiza un archivo Python y extrae metadatos."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            return {"error": str(e)}
        
        lines = content.splitlines()
        result = {
            "path": str(filepath),
            "lines": len(lines),
            "bytes": len(content.encode('utf-8')),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
            "imports": [],
            "from_imports": [],
            "classes": [],
            "functions": [],
            "global_vars": [],
            "decorators_used": set(),
            "sections": [],
            "todos": [],
            "warnings": []
        }
        
        self.total_lines += result["lines"]
        self.total_bytes += result["bytes"]
        
        # Detectar patrones de comentarios
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Secciones con ===
            if re.match(COMMENT_PATTERNS["section"], stripped):
                result["sections"].append({"line": line_num, "text": stripped})
            
            # TODOs y FIXMEs
            if re.search(COMMENT_PATTERNS["todo"], stripped, re.IGNORECASE):
                result["todos"].append({"line": line_num, "text": stripped})
                self.comment_findings[str(filepath)].append({
                    "type": "TODO",
                    "line": line_num,
                    "text": stripped
                })
            
            # Warnings
            if re.search(COMMENT_PATTERNS["warning"], stripped, re.IGNORECASE):
                result["warnings"].append({"line": line_num, "text": stripped})
                self.comment_findings[str(filepath)].append({
                    "type": "WARNING",
                    "line": line_num,
                    "text": stripped
                })
            
            # Critical
            if re.search(COMMENT_PATTERNS["critical"], stripped, re.IGNORECASE):
                self.comment_findings[str(filepath)].append({
                    "type": "CRITICAL",
                    "line": line_num,
                    "text": stripped
                })
        
        # AST analysis
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)
                    self.all_imports[str(filepath)].add(alias.name)
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    import_str = f"{module}.{alias.name}" if module else alias.name
                    result["from_imports"].append({
                        "module": module,
                        "name": alias.name,
                        "full": import_str
                    })
                    self.all_imports[str(filepath)].add(module)
                    self.import_graph[str(filepath)].add(module)
                    
            elif isinstance(node, ast.ClassDef):
                methods = []
                for n in node.body:
                    if isinstance(n, ast.FunctionDef):
                        methods.append({
                            "name": n.name,
                            "args": len(n.args.args),
                            "line": n.lineno
                        })
                
                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', node.lineno),
                    "methods": methods,
                    "method_count": len(methods),
                    "bases": [self._get_name(b) for b in node.bases],
                    "decorators": [self._get_name(d) for d in node.decorator_list]
                })
                self.all_definitions[str(filepath)].add(node.name)
                
            elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', node.lineno),
                    "args": [arg.arg for arg in node.args.args],
                    "arg_count": len(node.args.args),
                    "decorators": [self._get_name(d) for d in node.decorator_list],
                    "is_kernel": any("kernel" in self._get_name(d).lower() for d in node.decorator_list)
                })
                self.all_definitions[str(filepath)].add(node.name)
                for d in node.decorator_list:
                    result["decorators_used"].add(self._get_name(d))
                
            elif isinstance(node, ast.Assign) and node.col_offset == 0:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        result["global_vars"].append(target.id)
        
        result["code_lines"] = result["lines"] - result["blank_lines"] - result["comment_lines"]
        result["decorators_used"] = list(result["decorators_used"])
        
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
        exclude_dirs = exclude_dirs or {"__pycache__", ".git", "venv", ".venv", ".agent"}
        
        for filepath in self.root.rglob("*.py"):
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
            
            full_path = self.root / filepath
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_unused = []
            
            for imp in data["imports"]:
                name = imp.split(".")[-1]
                lines = content.split('\n')
                uses = sum(1 for line in lines if name in line and 'import' not in line)
                if uses == 0:
                    file_unused.append(imp)
            
            for imp_data in data["from_imports"]:
                name = imp_data["name"]
                lines = content.split('\n')
                uses = sum(1 for line in lines if name in line and 'import' not in line)
                if uses == 0:
                    file_unused.append(imp_data["full"])
            
            if file_unused:
                unused[filepath] = file_unused
        
        return unused
    
    def find_unused_definitions(self) -> Dict[str, List[str]]:
        """Detecta funciones/clases definidas pero nunca importadas."""
        all_imported = set()
        for imports in self.all_imports.values():
            all_imported.update(imports)
        
        for filepath, data in self.files.items():
            for imp in data.get("from_imports", []):
                all_imported.add(imp["name"])
        
        unused = {}
        for filepath, defs in self.all_definitions.items():
            unused_in_file = []
            for d in defs:
                if d.startswith("_"):
                    continue
                if d not in all_imported:
                    unused_in_file.append(d)
            if unused_in_file:
                rel_path = Path(filepath).relative_to(self.root) if self.root in Path(filepath).parents else filepath
                unused[str(rel_path)] = unused_in_file
        
        return unused
    
    def get_complexity_report(self) -> List[Tuple[str, int, int, int]]:
        """Retorna archivos ordenados por líneas de código."""
        report = []
        for filepath, data in self.files.items():
            if "error" not in data:
                report.append((
                    filepath, 
                    data["lines"], 
                    data["code_lines"],
                    data["bytes"]
                ))
        return sorted(report, key=lambda x: x[1], reverse=True)
    
    def get_function_report(self) -> List[Tuple[str, str, int, bool]]:
        """Retorna todas las funciones ordenadas por tamaño."""
        funcs = []
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            for func in data.get("functions", []):
                size = func.get("end_line", func["line"]) - func["line"] + 1
                funcs.append((
                    filepath,
                    func["name"],
                    size,
                    func.get("is_kernel", False)
                ))
        return sorted(funcs, key=lambda x: x[2], reverse=True)
    
    def get_class_report(self) -> List[Tuple[str, str, int, int]]:
        """Retorna todas las clases ordenadas por métodos."""
        classes = []
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            for cls in data.get("classes", []):
                size = cls.get("end_line", cls["line"]) - cls["line"] + 1
                classes.append((
                    filepath,
                    cls["name"],
                    cls["method_count"],
                    size
                ))
        return sorted(classes, key=lambda x: x[2], reverse=True)
    
    def print_report(self):
        """Imprime el reporte completo de auditoría."""
        self._print("=" * 70)
        self._print("REPORTE DE AUDITORÍA - LifeSimulator v3.0")
        self._print(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._print("=" * 70)
        
        # Resumen general
        self._print(f"\n📊 RESUMEN GENERAL")
        self._print("-" * 50)
        self._print(f"  Archivos analizados: {len(self.files)}")
        self._print(f"  Líneas totales: {self.total_lines:,}")
        self._print(f"  Tamaño total: {self.total_bytes / 1024:.1f} KB")
        
        # Archivos por tamaño
        self._print(f"\n📁 ARCHIVOS POR TAMAÑO (Top 15)")
        self._print("-" * 50)
        self._print(f"  {'Archivo':<45} {'Líneas':>8} {'Código':>8} {'KB':>8}")
        self._print(f"  {'-'*45} {'-'*8} {'-'*8} {'-'*8}")
        
        for filepath, lines, code_lines, bytes_ in self.get_complexity_report()[:15]:
            kb = bytes_ / 1024
            status = "⚠️" if lines > 300 else "✅"
            self._print(f"  {status} {filepath:<43} {lines:>6} {code_lines:>8} {kb:>7.1f}")
        
        # Funciones más grandes
        self._print(f"\n🔧 FUNCIONES MÁS GRANDES (Top 10)")
        self._print("-" * 50)
        funcs = self.get_function_report()[:10]
        for filepath, name, size, is_kernel in funcs:
            kernel_tag = " [KERNEL]" if is_kernel else ""
            self._print(f"  {name}{kernel_tag} ({filepath}): {size} líneas")
        
        # Clases
        self._print(f"\n🏗️ CLASES (ordenadas por métodos)")
        self._print("-" * 50)
        for filepath, name, methods, size in self.get_class_report():
            self._print(f"  {name} ({filepath}): {methods} métodos, {size} líneas")
        
        # TODOs y FIXMEs
        self._print(f"\n📝 TODOS/FIXMES ENCONTRADOS")
        self._print("-" * 50)
        total_todos = 0
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            todos = data.get("todos", [])
            if todos:
                self._print(f"  {filepath}:")
                for todo in todos[:3]:
                    self._print(f"    L{todo['line']}: {todo['text'][:60]}...")
                    total_todos += 1
                if len(todos) > 3:
                    self._print(f"    ... y {len(todos) - 3} más")
                    total_todos += len(todos) - 3
        if total_todos == 0:
            self._print("  ✅ Ninguno encontrado")
        else:
            self._print(f"\n  Total: {total_todos} TODOs/FIXMEs")
        
        # Secciones detectadas (===)
        self._print(f"\n📐 SECCIONES DETECTADAS (===)")
        self._print("-" * 50)
        total_sections = 0
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            sections = data.get("sections", [])
            if sections:
                total_sections += len(sections)
        self._print(f"  Total: {total_sections} secciones con '===' detectadas")
        
        # Imports no usados
        self._print(f"\n🔍 IMPORTS POTENCIALMENTE NO USADOS")
        self._print("-" * 50)
        unused_imports = self.find_unused_imports()
        if unused_imports:
            for filepath, imports in unused_imports.items():
                self._print(f"  {filepath}:")
                for imp in imports[:5]:
                    self._print(f"    - {imp}")
                if len(imports) > 5:
                    self._print(f"    ... y {len(imports) - 5} más")
        else:
            self._print("  ✅ Ninguno detectado")
        
        # Definiciones sin uso externo
        self._print(f"\n📦 DEFINICIONES SIN IMPORTAR EXTERNAMENTE")
        self._print("-" * 50)
        unused_defs = self.find_unused_definitions()
        if unused_defs:
            for filepath, defs in unused_defs.items():
                self._print(f"  {filepath}:")
                for d in defs[:5]:
                    self._print(f"    - {d}")
                if len(defs) > 5:
                    self._print(f"    ... y {len(defs) - 5} más")
        else:
            self._print("  ✅ Todo parece conectado")
        
        # Estructura por directorio
        self._print(f"\n📂 ESTRUCTURA POR DIRECTORIO")
        self._print("-" * 50)
        dirs = defaultdict(lambda: {"files": 0, "lines": 0, "bytes": 0})
        for filepath, data in self.files.items():
            if "error" in data:
                continue
            parts = Path(filepath).parts
            dir_name = "/".join(parts[:-1]) if len(parts) > 1 else "/"
            dirs[dir_name]["files"] += 1
            dirs[dir_name]["lines"] += data["lines"]
            dirs[dir_name]["bytes"] += data["bytes"]
        
        self._print(f"  {'Directorio':<30} {'Archivos':>10} {'Líneas':>10} {'KB':>10}")
        self._print(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*10}")
        for dir_name, stats in sorted(dirs.items(), key=lambda x: x[1]["lines"], reverse=True):
            kb = stats["bytes"] / 1024
            self._print(f"  {dir_name:<30} {stats['files']:>10} {stats['lines']:>10} {kb:>9.1f}")
        
        # Kernels Taichi detectados
        self._print(f"\n⚡ KERNELS TAICHI DETECTADOS")
        self._print("-" * 50)
        kernels = [f for f in self.get_function_report() if f[3]]
        if kernels:
            for filepath, name, size, _ in kernels[:15]:
                self._print(f"  @ti.kernel {name} ({filepath}): {size} líneas")
            if len(kernels) > 15:
                self._print(f"  ... y {len(kernels) - 15} más")
        else:
            self._print("  Ninguno detectado")
        
        self._print("\n" + "=" * 70)
        self._print("FIN DEL REPORTE")
        self._print("=" * 70)
    
    def save_report(self, output_path: str):
        """Guarda el reporte en un archivo."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.output_lines))
        print(f"\n💾 Reporte guardado en: {output_path}")


def main():
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"Analizando: {root}\n")
    
    auditor = CodeAuditor(root)
    auditor.scan_directory()
    auditor.print_report()
    
    # Guardar reporte en archivo
    output_path = os.path.join(root, "scripts", "audit_report.txt")
    auditor.save_report(output_path)


if __name__ == "__main__":
    main()
