import ast
import os
import sys
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

# Data structures
func_defs = defaultdict(list)
class_defs = defaultdict(list)
file_definitions = defaultdict(list)
stub_funcs = []
call_graph = defaultdict(lambda: defaultdict(set))
imports = []

for file in files:
    try:
        source = file.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(source)
    except Exception as e:
        print(f"SYNTAX ERROR in {file}: {e}")
        continue
    package = get_module_path(file)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            func_defs[name].append((file, node.lineno, node, package))
            file_definitions[file].append((name, node.lineno, 'function'))
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
                stub_funcs.append({'file': str(file), 'line': node.lineno, 'name': name, 'type': 'function'})
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    call_graph[name][str(file)].add(child.func.id)
        elif isinstance(node, ast.ClassDef):
            name = node.name
            class_defs[name].append((file, node.lineno, node, package))
            file_definitions[file].append((name, node.lineno, 'class'))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mname = item.name
                    qname = f"{name}.{mname}"
                    file_definitions[file].append((qname, item.lineno, 'method'))
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
                        stub_funcs.append({'file': str(file), 'line': item.lineno, 'name': qname, 'type': 'method'})
                    for child in ast.walk(item):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                            call_graph[qname][str(file)].add(child.func.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    file_definitions[file].append((target.id, node.lineno, 'assign'))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                file_definitions[file].append((node.target.id, node.lineno, 'assign'))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'file': str(file),
                    'line': node.lineno,
                    'module': alias.name,
                    'names': [alias.asname or alias.name],
                    'level': 0,
                    'package': package,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = [alias.name for alias in node.names]
            imports.append({
                'file': str(file),
                'line': node.lineno,
                'module': module,
                'names': names,
                'level': node.level,
                'package': package,
            })

# Duplicate exports (same file, same name defined more than once at module level)
dup_exports = []
for file, defs in file_definitions.items():
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

# Duplicate module-level functions across files
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

dup_funcs = []
for name, items in func_defs.items():
    if len(items) > 1:
        # filter out common boilerplate names
        if name.startswith('_') or name in ('main', 'cli', 'run', 'app', 'create_app', 'get_db', 'init_app', 'before_request', 'after_request', 'index', 'health', 'ready', 'alive'):
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
        dup_funcs.append({
            'name': name,
            'count': len(items),
            'locations': [{'file': str(f), 'line': line, 'package': pkg} for f, line, node, pkg in items],
            'identical_pairs': identical,
        })

dup_classes = []
for name, items in class_defs.items():
    if len(items) > 1:
        dup_classes.append({
            'name': name,
            'count': len(items),
            'locations': [{'file': str(f), 'line': line, 'package': pkg} for f, line, node, pkg in items],
        })

# Import errors (internal modules not found)
import_errors = []
for imp in imports:
    level = imp['level']
    module = imp['module']
    pkg = imp['package']
    mod_parts = module.split('.') if module else []
    abs_mod = resolve_relative(mod_parts, level, pkg)
    abs_mod_str = '.'.join(abs_mod)
    is_internal = False
    if level > 0:
        is_internal = True
    else:
        top = abs_mod_str.split('.')[0] if abs_mod_str else ''
        is_internal = top == 'backend' or abs_mod_str in existing_modules
    if is_internal:
        path = mod_to_path(abs_mod_str)
        if path is None:
            import_errors.append({
                'file': imp['file'],
                'line': imp['line'],
                'import': abs_mod_str,
                'names': imp['names'],
                'error': 'Module not found',
            })

# Circular dependencies via imports
file_to_module = {str(f): get_module_path(f) for f in files}
module_to_file = {v:k for k,v in file_to_module.items()}
import_edges = defaultdict(set)
for imp in imports:
    level = imp['level']
    module = imp['module']
    pkg = imp['package']
    mod_parts = module.split('.') if module else []
    abs_mod = resolve_relative(mod_parts, level, pkg)
    abs_mod_str = '.'.join(abs_mod)
    is_internal = False
    if level > 0:
        is_internal = True
    else:
        top = abs_mod_str.split('.')[0] if abs_mod_str else ''
        is_internal = top == 'backend' or abs_mod_str in existing_modules
    if is_internal:
        path = mod_to_path(abs_mod_str)
        if path:
            src = imp['file']
            dst = str(path)
            if src != dst:
                import_edges[src].add(dst)

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

unique_cycles = []
seen_sets = set()
for c in cycles:
    s = tuple(sorted(set(c)))
    if s not in seen_sets:
        seen_sets.add(s)
        unique_cycles.append(c)

# Mutual recursion / redundant calls in same file
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

# Print report
print("="*100)
print("BACKEND AUDIT REPORT")
print("="*100)

print("\n## 1. DUPLICATE FUNCTION DEFINITIONS ACROSS FILES")
if not dup_funcs:
    print("No duplicate module-level functions found.")
for item in dup_funcs:
    sev = "CRITICAL" if item['identical_pairs'] else "WARNING"
    print(f"\n[{sev}] Function '{item['name']}' defined in {item['count']} files")
    if item['identical_pairs']:
        print("  Identical body detected in pairs:")
        for a_file, a_line, b_file, b_line in item['identical_pairs']:
            print(f"    - {a_file}:{a_line}  <->  {b_file}:{b_line}")
    print("  Locations:")
    for loc in item['locations']:
        print(f"    - {loc['file']}:{loc['line']}  (package {loc['package']})")

print("\n## 2. DUPLICATE CLASS DEFINITIONS ACROSS FILES")
if not dup_classes:
    print("No duplicate class definitions found.")
for item in dup_classes:
    print(f"\n[WARNING] Class '{item['name']}' defined in {item['count']} files")
    for loc in item['locations']:
        print(f"    - {loc['file']}:{loc['line']}  (package {loc['package']})")

print("\n## 3. STUB / EMPTY IMPLEMENTATIONS")
if not stub_funcs:
    print("No stubs found.")
for stub in sorted(stub_funcs, key=lambda x: (x['file'], x['line'])):
    sev = "INFO" if stub['type'] == 'method' else "WARNING"
    print(f"[{sev}] {stub['type']} '{stub['name']}' is stub/empty at {stub['file']}:{stub['line']}")

print("\n## 4. IMPORT ERRORS (INTERNAL MODULES NOT FOUND)")
if not import_errors:
    print("No internal import errors found.")
for err in import_errors:
    print(f"[CRITICAL] {err['file']}:{err['line']} imports missing module '{err['import']}' (names: {err['names']})")

print("\n## 5. CIRCULAR DEPENDENCIES")
if not unique_cycles:
    print("No circular import cycles detected.")
for cyc in unique_cycles:
    print(f"[CRITICAL] Circular import detected:")
    for i in range(len(cyc)-1):
        print(f"    {cyc[i]} ->")
    print(f"    {cyc[-1]}")

print("\n## 6. REDUNDANT / MUTUAL FUNCTION CALLS (SAME FILE)")
if not redundant_calls:
    print("No mutual recursion in same file found.")
for red in redundant_calls:
    print(f"[WARNING] {red['file']}: '{red['func_a']}' <-> '{red['func_b']}' call each other")

print("\n## 7. DUPLICATE EXPORTS IN SAME FILE")
if not dup_exports:
    print("No duplicate exports in same file found.")
for dup in dup_exports:
    print(f"[CRITICAL] {dup['file']}: name '{dup['name']}' exported twice (lines {dup['lines'][0]} and {dup['lines'][1]}, types {dup['types']})")

print("\n" + "="*100)
