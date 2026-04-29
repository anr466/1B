import ast
import os
from collections import defaultdict
from pathlib import Path

BACKEND = Path('/Users/anr/Desktop/trading_ai_bot-1/backend')
PROJECT = BACKEND.parent
files = sorted(BACKEND.rglob('*.py'))

def get_module_path(file_path):
    rel = file_path.relative_to(PROJECT)
    return str(rel.with_suffix('')).replace(os.sep, '.')

def resolve_relative(module_parts, level, package):
    if level == 0:
        return list(module_parts)
    parts = package.split('.')
    base = parts[:-level] if level <= len(parts) else []
    if module_parts:
        base = base + list(module_parts)
    return base

def collect_module_level_names(body, names):
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                n = alias.asname or alias.name
                names.add(n.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Try):
            collect_module_level_names(node.body, names)
            for handler in node.handlers:
                collect_module_level_names(handler.body, names)
            collect_module_level_names(node.orelse, names)
            collect_module_level_names(node.finalbody, names)
        elif isinstance(node, (ast.If, ast.With, ast.For, ast.While)):
            collect_module_level_names(node.body, names)
            collect_module_level_names(node.orelse, names)
        # ignore nested functions/classes because they are handled by their parent

# Parse all files
parsed = {}
module_exports = defaultdict(set)
file_defs = defaultdict(list)

for file in files:
    try:
        source = file.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(source)
    except Exception as e:
        print(f"SYNTAX ERROR in {file}: {e}")
        continue
    package = get_module_path(file)
    parsed[str(file)] = (tree, package)
    names = set()
    collect_module_level_names(tree.body, names)
    module_exports[package] = names
    # also record file defs for duplicate export detection (same file)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            file_defs[file].append((node.name, node.lineno, 'function'))
        elif isinstance(node, ast.ClassDef):
            file_defs[file].append((node.name, node.lineno, 'class'))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    file_defs[file].append((f"{node.name}.{item.name}", item.lineno, 'method'))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    file_defs[file].append((target.id, node.lineno, 'assign'))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                file_defs[file].append((node.target.id, node.lineno, 'assign'))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                n = alias.asname or alias.name
                file_defs[file].append((n.split('.')[0], node.lineno, 'import'))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                file_defs[file].append((alias.asname or alias.name, node.lineno, 'import'))

# Data structures
func_defs = defaultdict(list)
class_defs = defaultdict(list)
stub_items = []
call_graph = defaultdict(lambda: defaultdict(set))

for file, (tree, package) in parsed.items():
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_defs[node.name].append((file, node.lineno, node, package))
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    call_graph[node.name][str(file)].add(child.func.id)
        elif isinstance(node, ast.ClassDef):
            class_defs[node.name].append((file, node.lineno, node, package))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{node.name}.{item.name}"
                    for child in ast.walk(item):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                            call_graph[qname][str(file)].add(child.func.id)
                    body = item.body
                    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                        body = body[1:]
                    is_stub = False
                    if not body:
                        is_stub = True
                    elif len(body) == 1:
                        stmt = body[0]
                        if isinstance(stmt, ast.Pass):
                            is_stub = True
                        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
                            is_stub = True
                        elif isinstance(stmt, ast.Return) and stmt.value is None:
                            is_stub = True
                        elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Name) and stmt.exc.id == 'NotImplementedError':
                            is_stub = True
                        elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                            is_stub = True
                    if is_stub:
                        # determine if abstract
                        abstract = any(isinstance(d, ast.Name) and d.id == 'abstractmethod' for d in item.decorator_list)
                        abc = any(isinstance(b, ast.Name) and b.id in ('ABC', 'ABCMeta') for b in node.bases)
                        sev = 'INFO' if (abstract or abc or 'Base' in node.name or 'Interface' in node.name) else 'WARNING'
                        stub_items.append({'file': str(file), 'line': item.lineno, 'name': qname, 'type': 'method', 'severity': sev})
            # class-level methods stub done above

# module-level function stubs
for name, items in func_defs.items():
    for file, line, node, package in items:
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        is_stub = False
        if not body:
            is_stub = True
        elif len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                is_stub = True
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
                is_stub = True
            elif isinstance(stmt, ast.Return) and stmt.value is None:
                is_stub = True
            elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Name) and stmt.exc.id == 'NotImplementedError':
                is_stub = True
            elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                is_stub = True
        if is_stub:
            stub_items.append({'file': str(file), 'line': line, 'name': name, 'type': 'function', 'severity': 'WARNING'})

# Duplicate exports in same file
dup_exports = []
for file, defs in file_defs.items():
    seen = {}
    for name, line, typ in defs:
        if name in seen:
            dup_exports.append({
                'file': str(file),
                'name': name,
                'lines': [seen[name][1], line],
                'types': [seen[name][0], typ],
            })
        else:
            seen[name] = (typ, line)

# Duplicate functions across files
dup_funcs_report = []
for name, items in func_defs.items():
    if len(items) > 1:
        if name.startswith('_') or name in ('main','cli','run','app','create_app','get_db','init_app','before_request','after_request','index','health','ready','alive','setup','configure'):
            continue
        bodies = []
        for f, line, node, pkg in items:
            try:
                body_dump = ast.dump(node.body, include_attributes=False)
            except Exception:
                body_dump = ''
            bodies.append((f, line, body_dump, pkg))
        identical = []
        for i in range(len(bodies)):
            for j in range(i+1, len(bodies)):
                if bodies[i][2] and bodies[i][2] == bodies[j][2]:
                    identical.append((str(bodies[i][0]), bodies[i][1], str(bodies[j][0]), bodies[j][1]))
        dup_funcs_report.append({
            'name': name,
            'count': len(items),
            'locations': [{'file': str(f), 'line': line, 'package': pkg} for f, line, node, pkg in items],
            'identical_pairs': identical,
        })

# Duplicate classes across files
dup_classes_report = []
for name, items in class_defs.items():
    if len(items) > 1:
        dup_classes_report.append({
            'name': name,
            'count': len(items),
            'locations': [{'file': str(f), 'line': line, 'package': pkg} for f, line, node, pkg in items],
        })

# Import errors
existing_modules = set()
for file in files:
    mod = get_module_path(file)
    existing_modules.add(mod)
    if file.name == '__init__.py':
        pkg_mod = str(file.relative_to(PROJECT).parent).replace(os.sep, '.')
        existing_modules.add(pkg_mod)

def mod_to_path(mod):
    parts = mod.split('.')
    p = PROJECT.joinpath(*parts)
    if p.with_suffix('.py').exists():
        return p.with_suffix('.py')
    if p.joinpath('__init__.py').exists():
        return p.joinpath('__init__.py')
    return None

import_errors = []
for file, (tree, package) in parsed.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split('.')[0]
                is_internal = top == 'backend' or alias.name in existing_modules
                if is_internal:
                    path = mod_to_path(alias.name)
                    if path is None:
                        import_errors.append({
                            'file': str(file),
                            'line': node.lineno,
                            'import': alias.name,
                            'names': [],
                            'error': 'Module not found',
                        })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            mod_parts = module.split('.') if module else []
            abs_mod = resolve_relative(mod_parts, node.level, package)
            abs_mod_str = '.'.join(abs_mod)
            is_internal = False
            if node.level > 0:
                is_internal = True
            else:
                top = abs_mod_str.split('.')[0] if abs_mod_str else ''
                is_internal = top == 'backend' or abs_mod_str in existing_modules
            if is_internal:
                path = mod_to_path(abs_mod_str)
                if path is None:
                    import_errors.append({
                        'file': str(file),
                        'line': node.lineno,
                        'import': abs_mod_str,
                        'names': [alias.name for alias in node.names],
                        'error': 'Module not found',
                    })
                else:
                    target_mod = get_module_path(path)
                    exported = module_exports.get(target_mod, set())
                    for alias in node.names:
                        name = alias.name
                        if name == '*':
                            continue
                        if name not in exported:
                            sub_path = mod_to_path(f"{target_mod}.{name}")
                            if sub_path is None:
                                import_errors.append({
                                    'file': str(file),
                                    'line': node.lineno,
                                    'import': abs_mod_str,
                                    'name': name,
                                    'error': f"Name '{name}' not found in module",
                                })

# Circular dependencies
file_to_module = {str(f): get_module_path(f) for f in files}
import_edges = defaultdict(set)
for file, (tree, package) in parsed.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split('.')[0]
                is_internal = top == 'backend' or alias.name in existing_modules
                if is_internal:
                    path = mod_to_path(alias.name)
                    if path:
                        import_edges[str(file)].add(str(path))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            mod_parts = module.split('.') if module else []
            abs_mod = resolve_relative(mod_parts, node.level, package)
            abs_mod_str = '.'.join(abs_mod)
            is_internal = False
            if node.level > 0:
                is_internal = True
            else:
                top = abs_mod_str.split('.')[0] if abs_mod_str else ''
                is_internal = top == 'backend' or abs_mod_str in existing_modules
            if is_internal:
                path = mod_to_path(abs_mod_str)
                if path:
                    import_edges[str(file)].add(str(path))

visited = set()
rec_stack = []
rec_set = set()
cycles = []

def dfs(node):
    visited.add(node)
    rec_stack.append(node)
    rec_set.add(node)
    for neighbor in import_edges[node]:
        if neighbor not in visited:
            dfs(neighbor)
        elif neighbor in rec_set:
            idx = rec_stack.index(neighbor)
            cycle = rec_stack[idx:] + [neighbor]
            cycles.append(cycle)
    rec_stack.pop()
    rec_set.remove(node)

for node in list(import_edges.keys()):
    if node not in visited:
        dfs(node)

seen_cycle_sets = set()
unique_cycles = []
for c in cycles:
    s = tuple(sorted(set(c)))
    if s not in seen_cycle_sets:
        seen_cycle_sets.add(s)
        unique_cycles.append(c)

# Mutual recursion in same file (module-level functions only)
redundant_calls = []
file_func_names = defaultdict(set)
for name, items in func_defs.items():
    for f, line, node, pkg in items:
        file_func_names[str(f)].add(name)
for fpath, funcs in file_func_names.items():
    for a in funcs:
        callees = call_graph.get(a, {}).get(fpath, set())
        for b in callees:
            if b in funcs and b != a:
                if a in call_graph.get(b, {}).get(fpath, set()):
                    redundant_calls.append({
                        'file': fpath,
                        'func_a': a,
                        'func_b': b,
                    })

# __all__ duplicates
all_duplicates = []
for file, (tree, package) in parsed.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__all__':
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        seen = set()
                        dup = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                if elt.value in seen:
                                    dup.append(elt.value)
                                seen.add(elt.value)
                        if dup:
                            all_duplicates.append({
                                'file': str(file),
                                'line': node.lineno,
                                'names': dup,
                            })

# REPORT
print("="*120)
print("BACKEND AUDIT REPORT v3")
print("="*120)

print("\n### 1. DUPLICATE MODULE-LEVEL FUNCTION DEFINITIONS ACROSS FILES")
if not dup_funcs_report:
    print("None found.")
for item in dup_funcs_report:
    sev = "CRITICAL" if item['identical_pairs'] else "WARNING"
    print(f"\n[{sev}] Function '{item['name']}' defined in {item['count']} files")
    if item['identical_pairs']:
        print("  Identical AST body in:")
        for a_file, a_line, b_file, b_line in item['identical_pairs']:
            print(f"    - {a_file}:{a_line}  <->  {b_file}:{b_line}")
    print("  Locations:")
    for loc in item['locations']:
        print(f"    - {loc['file']}:{loc['line']}  ({loc['package']})")

print("\n### 2. DUPLICATE CLASS DEFINITIONS ACROSS FILES")
if not dup_classes_report:
    print("None found.")
for item in dup_classes_report:
    print(f"\n[WARNING] Class '{item['name']}' defined in {item['count']} files")
    for loc in item['locations']:
        print(f"    - {loc['file']}:{loc['line']}  ({loc['package']})")

print("\n### 3. STUB / EMPTY IMPLEMENTATIONS")
if not stub_items:
    print("None found.")
for stub in sorted(stub_items, key=lambda x: (x['file'], x['line'])):
    sev = stub['severity']
    print(f"[{sev}] {stub['type']} '{stub['name']}' is stub/empty at {stub['file']}:{stub['line']}")

print("\n### 4. IMPORT ERRORS / MISSING NAMES")
if not import_errors:
    print("None found.")
for err in import_errors:
    if 'name' in err:
        print(f"[CRITICAL] {err['file']}:{err['line']} from '{err['import']}' imports missing name '{err['name']}'")
    else:
        print(f"[CRITICAL] {err['file']}:{err['line']} imports missing module '{err['import']}'")

print("\n### 5. CIRCULAR DEPENDENCIES")
if not unique_cycles:
    print("None detected.")
for cyc in unique_cycles:
    print(f"[CRITICAL] Circular import:")
    for i in range(len(cyc)-1):
        print(f"    {cyc[i]} ->")
    print(f"    {cyc[-1]}")

print("\n### 6. REDUNDANT / MUTUAL FUNCTION CALLS (SAME FILE)")
if not redundant_calls:
    print("None found.")
for red in redundant_calls:
    print(f"[WARNING] {red['file']}: '{red['func_a']}' <-> '{red['func_b']}' call each other")

print("\n### 7. DUPLICATE EXPORTS IN SAME FILE")
if not dup_exports:
    print("None found.")
for dup in dup_exports:
    print(f"[CRITICAL] {dup['file']}: '{dup['name']}' exported twice (lines {dup['lines'][0]} and {dup['lines'][1]}, types {dup['types']})")

print("\n### 8. __all__ DUPLICATE ENTRIES")
if not all_duplicates:
    print("None found.")
for dup in all_duplicates:
    print(f"[WARNING] {dup['file']}:{dup['line']} __all__ has duplicate entries: {dup['names']}")

print("\n" + "="*120)
