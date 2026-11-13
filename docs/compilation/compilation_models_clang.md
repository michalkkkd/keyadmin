# Advanced C-Interfacing Pipeline for Compass PK Models

This document outlines the advanced Clang compilation pipeline used to statically compile Numba `@cfunc` models into raw C object files and load them into `numbalsoda` without relying on Numba's JIT compilation at runtime. This severely reduces startup times, caching issues, and Nuitka compatibility problems.

## 1. The Core Problem
The `compass_pk.py` module defines complex differential equations (e.g., `model_V`, `model_PK_19`) that must be evaluated extremely fast by the `lsoda` ODE solver. Typically, Numba uses `@nb.cfunc` to JIT compile these at runtime. However:
*   When packaged with **Nuitka**, Numba's caching mechanism (`__pycache__`) is unreliable, often failing or silently skipping compilation.
*   Numba JIT compilation adds massive overhead to the application startup time.

## 2. The Clang Pipeline Solution
To bypass Numba entirely in the production binary, we created the `generator/` pipeline. This pipeline extracts the LLVM IR from Numba exactly once, compiles it statically using LLVM/Clang, and provides the raw memory pointers to `numbalsoda` using a custom C-Extension bridge.

### The Pipeline Steps (Automated by `build_models.ps1`)
1. **Cache Clearing:** The Numba `__pycache__` is deleted to force Numba to recompile the functions in memory so we can extract their LLVM IR.
2. **IR Extraction (`generate_all.py`):**
    * Dynamically imports `compass_pk`.
    * Locates the core models.
    * Uses `.inspect_llvm()` to dump the raw math instructions.
    * Uses Regex to rename Numba's mangled C-function names (`cfunc._ZN...`) into clean C-identifiers (`model_V_c_wrapper`).
    * Combines all LLVM IR into a single `compass_models.ll` module using `llvmlite.binding`.
3. **Clang Compilation:** Compiles `compass_models.ll` into `compass_models.obj` using the Windows `clang` compiler (MSVC target).
4. **C-API Bridge (`bridge.c` & `numba_stubs.c`):**
    * Numba's LLVM IR secretly depends on the Numba Runtime (NRT) for things like `NRT_Free` and `numba_gil_release`.
    * `numba_stubs.c` implements blank mock functions for these dependencies so the linker doesn't fail.
    * `bridge.c` defines a Python C-Extension that simply returns the memory addresses (as Python integers) of the Clang-compiled functions.
5. **Deployment:** The pipeline compiles the bridge into `compass_models_bridge.pyd` and copies it into `app/frontend/`.

## 3. How it Interacts with `compass_pk.py`
Inside `compass_pk.py`, a master switch `USE_PRECOMPILED_MODELS` exists. 

*   **When True:** The `@nb.cfunc` decorators are replaced with dummy decorators that do absolutely nothing. At the end of the file, the dummy python models are overwritten with objects containing the raw Clang memory pointers:
    ```python
    class ClangCompiledModel:
        def __init__(self, address):
            self.address = address

    model_V = ClangCompiledModel(compass_models_bridge.get_model_V())
    ```
*   Because `numbalsoda.lsoda` natively accepts raw integer pointers (e.g., `model_V.address`), the rest of the application runs perfectly without realizing that Numba is completely missing!

## 4. Rebuilding the Models
If you ever change the math inside the `model_*` functions in `compass_pk.py`:
1. Open PowerShell and navigate to the `generator/` folder.
2. Ensure you have Clang installed (`winget install LLVM.LLVM`).
3. Run `.\build_models.ps1`.
4. The new models are instantly compiled and injected back into the frontend.
