import ast

def analyze_code(filename):
    with open(filename, "r", encoding="utf-8") as f:
        code = f.read()
    
    tree = ast.parse(code)
    
    issues = []
    
    # 1. Look for subprocess calls missing creationflags
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, "id", "") == "subprocess" and node.func.attr in ("Popen", "run", "check_output"):
                has_flags = any(k.arg == "creationflags" for k in node.keywords)
                if not has_flags:
                    issues.append(f"Line {node.lineno}: subprocess.{node.func.attr} call might spawn a visible console (missing creationflags=0x08000000)")

    # 2. Look for UI updates not wrapped in self.after inside threads
    # This is harder to do purely with AST because we don't know what runs in a thread.
    # But we can look for threading.Thread
    thread_targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, "id", "") == "threading" and node.func.attr == "Thread":
                for k in node.keywords:
                    if k.arg == "target" and isinstance(k.value, ast.Name):
                        thread_targets.append(k.value.id)

    # 3. Look for bare excepts or except Exception with just 'pass' or print
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
                # check if it's just 'pass' or 'print'
                if len(node.body) == 1:
                    if isinstance(node.body[0], ast.Pass):
                        issues.append(f"Line {node.lineno}: Silent exception caught (pass). This hides potential crashes.")
                    elif isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Call):
                        if getattr(node.body[0].value.func, "id", "") == "print":
                            issues.append(f"Line {node.lineno}: Exception caught and only printed to console. Might be invisible to GUI user.")

    # 4. Check for 'open' without encoding (default encoding might crash on Windows with charmap)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                has_encoding = any(k.arg == "encoding" for k in node.keywords)
                mode = "r"
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for k in node.keywords:
                    if k.arg == "mode" and isinstance(k.value, ast.Constant):
                        mode = k.value.value
                
                if "b" not in mode and not has_encoding:
                    issues.append(f"Line {node.lineno}: open() called without 'encoding' for text file. Can cause UnicodeDecodeError on Windows.")

    for issue in issues:
        print(issue)
        
    if not issues:
        print("No obvious anti-patterns found in this sweep.")

analyze_code("app.py")
