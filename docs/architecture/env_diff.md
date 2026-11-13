# Virtual Environment (`.venv`) Modifications

This document records the exact changes that were manually made to the Python virtual environment (`.venv`) in order to successfully compile the `run_compass.exe` binary. 

**WARNING:** If you ever delete and recreate your `.venv`, or if you upgrade/reinstall `panel` or `statsmodels`, you **MUST** manually re-apply these exact changes, otherwise Nuitka compilation will fail or the compiled application will crash on startup!

---

## 1. Package Additions

### `pip install vtk`
*   **Reference:** [Error 7 in COMPILATION.md](../compilation/compilation.md#error-7-nuitka-crash-on-vtk-version-check-implicit-imports)
*   **Reason:** Nuitka's internal anti-bloat engine statically evaluates `vtk` version checks inside third-party scientific libraries during compilation. Without `vtk` installed, the evaluation resolves to `NoneType >= tuple`, which violently crashes the entire Nuitka C-compiler AST parsing phase. 
*   **Action:** Installed `vtk` into the `.venv` so a valid version string (e.g. `9.6.2`) is present for Nuitka to parse.

---

## 2. Code Modifications (Monkey-Patches)

### `panel\io\document.py`
*   **Reference:** [Error 6 in COMPILATION.md](../compilation/compilation.md#error-6-nuitka-compiler-crash-on-python-312-list-comprehensions)
*   **File Path:** `c:\Users\vboxuser\Desktop\compass\.venv\Lib\site-packages\panel\io\document.py`
*   **Reason:** Nuitka has a known compilation bug when processing Python 3.12+ list comprehensions that are nested inside `try...finally` blocks. This crashes the C-compiler completely.
*   **Action:** Refactored the list comprehensions inside the `_get_static_callbacks` method into standard `for` loops.

**Diff:**
```diff
@@ -95,12 +95,16 @@
         elif event.setter == 'client':
             return
         try:
-            return [
-                cb(event) for cb in callbacks
-            ]
+            results = []
+            for cb in callbacks:
+                results.append(cb(event))
+            return results
         finally:
-            return [
-                cb(event) for cb in _callbacks
-            ]
+            results_final = []
+            for cb in _callbacks:
+                results_final.append(cb(event))
+            return results_final
```

---

### `statsmodels\tools\docstring.py`
*   **Reference:** [Error 11 in COMPILATION.md](../compilation/compilation.md#error-11-statsmodels-docstring-parsing-crash)
*   **File Path:** `c:\Users\vboxuser\Desktop\compass\.venv\Lib\site-packages\statsmodels\tools\docstring.py`
*   **Reason:** When `statsmodels` is loaded inside a Nuitka compiled executable, many docstrings are stripped or optimized away. `statsmodels.tools.docstring.remove_parameters` attempts to parse missing docstrings and explicitly raises a `ValueError` if parameters are not found, crashing the application at boot.
*   **Action:** Handled the missing docstrings by patching the strict error raise to silently `pass`.

**Diff:**
```diff
@@ -589,7 +589,8 @@
     for p in parameters:
         if p not in extract:
             msg = f"One or more parameters were not found: {p}"
-            raise ValueError(msg)
+            # Patched for Nuitka docstring stripping
+            pass
         for line in extract[p]:
             _insert(line)
```
