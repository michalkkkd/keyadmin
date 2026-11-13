# Compass Application - Compilation Log and Handoff Document

This document outlines the compilation process, the exact commands used, and all the architectural errors and edge-cases encountered when packaging the `Compass` application into a standalone Windows `.exe` using **Nuitka**.

## 1. The Compilation Strategy

We migrated from PyInstaller to **Nuitka** in `--onefile` mode (using the Zig C-compiler) to properly support the heavy scientific libraries (`numba`, `scipy`, `pandas`, `bokeh`) without extreme bloat or dynamic import failures.

When a Nuitka `--onefile` executable runs, it unpacks its dependencies into a hidden temporary directory (e.g., `%LOCALAPPDATA%\Temp\onefile_XXXXX\run_compass_unpack`).

### Final Nuitka Command

We have encapsulated the final build process into a `build.ps1` script at the root of the project to cleanly isolate output directories and use relative paths instead of hardcoded user directories.

```powershell
$ErrorActionPreference = "Stop"

$OutputDir = "compilation"
$ExeDir = "$OutputDir\exe"

if (Test-Path $ExeDir) {
    Remove-Item -Recurse -Force $ExeDir
}
New-Item -ItemType Directory -Force -Path $ExeDir | Out-Null



.\.venv\Scripts\python.exe -m nuitka --onefile --windows-console-mode=force --lto=no `
  --assume-yes-for-downloads `
  --experimental=debug-report-traceback `
  --output-dir=$OutputDir `
  --nofollow-import-to=numba `
  --nofollow-import-to=llvmlite `
  --nofollow-import-to=plotly.tests `
  --nofollow-import-to=tornado.test `
  --nofollow-import-to=xyzservices.tests `
  --nofollow-import-to=colorama.tests `
  --nofollow-import-to=greenlet.tests `
  --nofollow-import-to=win32ctypes.tests `
  --nofollow-import-to=reportlab.*test* `
  --nofollow-import-to=scipy.*.tests `
  --nofollow-import-to=scipy.*.*.tests `
  --nofollow-import-to=pytest `
  --nofollow-import-to=numpy.tests `
  --nofollow-import-to=pandas.tests `
  --nofollow-import-to=scipy.tests `
  --include-data-dir="app\frontend\__pycache__=app\frontend\__pycache__" `
  --include-package=openpyxl `
  --include-package=pandas `
  --include-package=bokeh `
  --include-package=panel `
  --include-package=plotly `
  --include-package=scipy `
  --include-package-data=plotly `
  --include-package=reportlab `
  --include-package=et_xmlfile `
  --include-package=app.frontend `
  --include-module=yaml `
  --include-package-data=app `
  --include-package-data=_internal.numbalsoda `
  --include-data-files="_internal\numbalsoda\*.dll=_internal\numbalsoda\" `
  --include-data-dir=.\.venv\Lib\site-packages\kaleido=kaleido `
  --include-data-dir=.\static=static `
  --include-data-files=".\data\config\frontend_conf.yaml=data\config\frontend_conf.yaml" `
  --include-data-files=".\data\users\sessions\default\current_config.yml=data\users\sessions\default\current_config.yml" `
  --include-data-dir=.\.venv\Lib\site-packages\panel\dist=panel\dist `
  --include-data-dir=.\.venv\Lib\site-packages\bokeh\server\static=bokeh\server\static `
  --include-data-files=".\.venv\Lib\site-packages\kaleido\executable\bin\kaleido.exe=kaleido\executable\bin\kaleido.exe" `
  --include-data-files=".\.venv\Lib\site-packages\kaleido\executable\bin\swiftshader\*.dll=kaleido\executable\bin\swiftshader\" `
  --include-windows-runtime-dlls=yes `
  run_compass.py

Move-Item -Path "$OutputDir\run_compass.exe" -Destination "$ExeDir\run_compass.exe" -Force
```
*(Note: `--windows-console-mode=force` is used to strictly enforce standard console output behavior, forcing Powershell to block and stream logs).*

---

## 2. Architectural Errors & Fixes Encountered

### Error 1: Panel Serving a Raw String Filepath
**The Issue:** `../run_compass.py` originally called `pn.serve({'/': 'app/main.py'})`. In a compiled `.exe`, `../app/main.py` is compiled into C code and no longer exists as a raw text file on disk, causing the Tornado server to crash.
**The Fix:** We refactored `../app/main.py` to wrap its module-level code inside a `def create_app():` function. We then updated `../run_compass.py` to import it (`from app.main import create_app`) and serve the function object directly: `pn.serve({'/': create_app})`.

### Error 2: Missing Panel/Bokeh Static Resources (JS/CSS)
**The Issue:** When the `.exe` launched, the browser opened but showed a blank page. Panel hardcodes its resource paths to the standard Python `sys.prefix` or `site-packages`, which do not exist in the `.exe`, resulting in 404s for `panel.min.js` and CSS files.
**The Fix:** We dynamically patched `panel.io.resources.DIST_DIR` inside `../run_compass.py` to point to Nuitka's temporary unpack directory:
```python
if hasattr(sys, 'argv') and str(sys.argv[0]).endswith('.exe'):
    import pathlib
    unpack_dir = pathlib.Path(sys.argv[0]).parent / (os.path.splitext(os.path.basename(sys.argv[0]))[0] + "_unpack")
    import panel.io.resources
    panel.io.resources.DIST_DIR = unpack_dir / "panel" / "dist"
```

### Error 3: Environment Detection (`sys.frozen`)
**The Issue:** We initially used `if getattr(sys, 'frozen', False):` to detect if the app was running as an `.exe` to apply the patch above. Nuitka (unlike PyInstaller) does not set `sys.frozen` by default on Windows.
**The Fix:** We swapped the check to `str(sys.argv[0]).endswith('.exe')`.

### Error 4: Absolute Paths in YAML Configs (`FileNotFoundError`)
**The Issue:** When the user moved the `.exe` and the `../data` folder to a new drive (e.g., `Q:` drive) and attempted to load an *old* session (e.g., `?ID=36`), the app threw a `FileNotFoundError` when uploading a new file.
**The Reason:** `current_config.yml` in old sessions hardcodes absolute paths (e.g., `path: C:\Users\...\data/session/36/`). When the app tried to save the uploaded CSV using `data_all_df.to_csv()`, it attempted to write to the missing `C:` drive path instead of the new `Q:` drive location.
**The Fix/Workaround:** Creating a new session successfully generates correct paths. Future work should convert `app_conf['path']` generation to use purely relative paths.

### Error 5: Pandas `read_excel` failure with `BytesIO`
**The Issue:** The UI threw "ERROR: the uploaded data file is incorrect" when uploading a valid `.xlsx` file. Because the Nuitka `.exe` reads the file as a raw byte stream (`BytesIO`) without a `.xlsx` extension, Pandas struggled to dynamically import the `openpyxl` engine.
**The Fix:** We discovered that Nuitka compiled `openpyxl`, but missed its hidden XML parser sub-dependency. Adding `--include-package=et_xmlfile` to the Nuitka build command successfully forced the required dependency into the `.exe`, resolving the issue.

### Error 6: Nuitka Compiler Crash on Python 3.12+ List Comprehensions
**The Issue:** Nuitka has a known, specific compilation bug when processing Python 3.12+ list comprehensions that reside inside `try...finally` blocks. This specific code structure was present deep inside one of Panel's dependencies (`.venv/Lib/site-packages/panel/io/document.py`), causing the entire Nuitka C-compilation process to crash before finishing.
**The Fix (Manual .venv Patch):** We had to manually patch `panel.io.document.py` directly inside the `.venv` by rewriting the offending list comprehensions into standard `for` loops. 
*WARNING:* If you delete and recreate your `.venv` (or upgrade Panel) while still using Python 3.12+, you will need to re-apply this manual patch to `panel/io/document.py`, otherwise Nuitka will fail to compile the `.exe`.

### Error 7: Nuitka Crash on `vtk` Version Check (`implicit-imports`)
**The Issue:** The Nuitka compilation process crashed with `FATAL: implicit-imports: Error, failed to evaluate condition 'version("vtk") >= (9,)'... exception was '>=' not supported between instances of 'NoneType' and 'tuple'`. This occurred because Nuitka's internal anti-bloat/implicit-imports logic tries to evaluate the VTK version, but since VTK wasn't installed, it returned `None`, causing a crash when comparing against a tuple.
**The Fix:** We simply ran `pip install vtk` in the `.venv`. This provided a valid version string (e.g. `9.6.2`) and completely resolved the compiler crash without modifying Nuitka source code.

### Error 8: Nuitka Onefile `numbalsoda` Missing DLL Directory
**The Issue:** Upon successfully building and launching `run_compass.exe`, the application immediately crashed with `FileNotFoundError: [WinError 2] The system cannot find the file specified: 'C:\\...\\Temp\\onefile_XXX\\numbalsoda'`. This happens because `numbalsoda/__init__.py` hardcodes a call to `os.add_dll_directory(os.path.dirname(__file__))`. Nuitka flattens the execution structure inside the onefile payload and doesn't physically create the empty `numbalsoda` package folder, causing the system path lookup to fail.
**The Fix:** We injected a tiny monkey-patch into `run_compass.py` right before importing `numbalsoda` to gracefully ignore missing DLL directories, fixing the crash without needing to rebuild with complicated `--include-data-dir` flags:
```python
# Nuitka one-file compatibility: ignore missing DLL directories
_orig_add_dll = os.add_dll_directory
def safe_add_dll_directory(path):
    try:
        return _orig_add_dll(path)
    except FileNotFoundError:
        pass
os.add_dll_directory = safe_add_dll_directory
```

### Error 9: Corrupted C Cache from Disk Space Exhaustion (`InvalidFormat`)
**The Issue:** The VM ran out of disk space during the AST parsing phase. Nuitka wrote a truncated, 0-byte C file to the `run_compass.build` cache folder (`module.tornado.routing.c`). Upon resizing the disk and restarting Nuitka, the backend Zig compiler immediately crashed with `module.tornado.routing.c:1:1: error: InvalidFormat`.
**The Fix:** To securely flush the corrupted C file, we had to recursively delete both `run_compass.build` and `run_compass.onefile-build`, AND run Nuitka with the `--clean-cache=all` flag to purge the global `ccache` mechanism.

### Error 10: Bare `frontend` Import Not Resolved by Nuitka
**The Issue:** Upon launching the compiled `.exe`, it crashed with `ModuleNotFoundError: No module named 'frontend'`. The codebase uses bare imports like `from frontend.compass_engine import CompassEngine` across 17 files (55 import lines). This works in development because `run_compass.py` dynamically adds `app/` to `sys.path`, but Nuitka resolves imports statically at compile time and only knows the package as `app.frontend`.
**The Fix:** Added `--include-package=app.frontend` to the Nuitka build command, and wrote a Python script to refactor all 17 files across the codebase to properly use `from app.frontend.X import Y`. Nuitka's module registry now correctly resolves the package.

### Error 11: Statsmodels Docstring Parsing Crash (historical)
statsmodels was removed from Compass and from the build on 2026-11-05 (commit b574ac9); this entry only applies to old builds.

**The Issue:** `statsmodels.tools.docstring.remove_parameters` crashes with `ValueError: One or more parameters were not found` when loading the module inside the Nuitka executable due to optimizations/stripping of docstrings.
**The Fix:** Directly patched `c:\Users\vboxuser\Desktop\compass\.venv\Lib\site-packages\statsmodels\tools\docstring.py` line 593 to replace the `raise ValueError` with `pass`. This allows statsmodels to load correctly under Nuitka without crashing.

### Error 12: Numba Caching RuntimeError (`cannot cache function... no locator available`)
**The Issue:** Running the `.exe` triggered a crash in `compass_pk.py` with `RuntimeError: cannot cache function 'model_V': no locator available for file`. This occurs because Numba's `@nb.cfunc(cache=True)` tries to cache the JIT-compiled function by writing a `.nbc`/`.nbi` file next to the source file. However, in Nuitka's temporary unpack environment, the source files are missing or exist only as virtual compiled modules, causing the locator to fail.
**The Fix:** Disabled Numba caching across the entire codebase by changing all instances of `cache=True` to `cache=False` (or removing it entirely) in `app/frontend/compass_pk.py`. The JIT compilation now runs dynamically at startup, which is fast enough and prevents the crash.

### Error 13: Panel Static Assets 404 (`panel/dist` FileNotFoundError)
**The Issue:** The Nuitka `.exe` booted successfully, but Panel's Tornado web server crashed at the very end trying to serve `favicon.ico`. This occurred because Nuitka `onefile` unpacks into a dynamic `%TEMP%\onefile_XYZ` directory, but the original `run_compass.py` monkey-patch hardcoded `DIST_DIR` to look in `sys.argv[0] + "_unpack"`. Furthermore, Nuitka wasn't bundling the `panel/dist` static HTML/JS assets natively.
**The Fix:** 
1. Added `--include-data-dir=c:\Users\vboxuser\Desktop\compass\.venv\Lib\site-packages\panel\dist=panel\dist` to the Nuitka build command.
2. Updated `run_compass.py` to point `DIST_DIR` to the actual dynamic unpack directory using `pathlib.Path(__file__).parent.absolute() / "panel" / "dist"`.

### Error 14: Bokeh Static Assets 404 (`bokeh.min.js` FileNotFoundError)
**The Issue:** After Panel loaded, Bokeh threw 404s trying to serve `bokeh.min.js` and other static assets. Nuitka did not automatically bundle `bokeh/server/static`.
**The Fix:** Added `--include-data-dir=c:\Users\vboxuser\Desktop\compass\.venv\Lib\site-packages\bokeh\server\static=bokeh\server\static` to the Nuitka build command.

### Error 15: Missing Application Config & Static Assets in Nuitka Unpack (`TypeError: NoneType object is not subscriptable`)
**The Issue:** The web server booted, but hitting `localhost:5006` caused a crash in `environment.py` because `SafeFileManager().read_yaml` failed to find `app/frontend_conf.yaml` and returned `None`. This occurred for two reasons:
1. `environment.py` was generating paths using `os.path.dirname(__file__)` which resolved to `%TEMP%\onefile_XYZ`, but Nuitka wasn't bundling `frontend_conf.yaml` or the `static` folder into that directory.
2. `environment.py` was also generating user-facing paths (like `data`, `docs`, `models`, `results`) relative to `%TEMP%\onefile_XYZ`, which would cause user data to be lost when the `.exe` closed!
**The Fix:** 
1. Re-wrote `app/frontend/environment.py` path generators (`data_paths`, `docs_paths`, `models_paths`, `results_paths`) to explicitly use `SafeFileManager().get_base_dir()` so they securely point to the physical directory where the `.exe` lives.
2. Left `static_paths` and `main_paths` pointing to the internal `%TEMP%` unpack folder, and added `--include-package-data=app` and `--include-data-dir=c:\Users\vboxuser\Desktop\compass\static=static` to the Nuitka build command to bundle those static application assets into the `.exe`.

### Error 16: Websocket ProtocolError (`Token is expired`)
**The Issue:** If the Panel app sits idle in the browser (or is refreshed) and the connection is re-established after a certain duration, Bokeh/Tornado throws `ProtocolError: Token is expired. Configure the app with a larger value for --session-token-expiration if necessary`.
**The Fix:** Added `session_token_expiration=31536000` (1 year in seconds) to the `pn.serve()` arguments inside `run_compass.py` to allow the user to leave the app running locally in the background without their session unexpectedly timing out.

### Error 17: Upload Crash (`KeyError: 'path'`)
**The Issue:** Uploading an Excel file crashed the app with `KeyError: 'path'` inside `load_dashboard.py`, which subsequently dumped the entire binary of the Excel file into the console logger. This happened because `compass_engine.py` only injected the dynamically generated `path` into `self._apps.conf` if the session was *new*. If a user logged into an *existing* session (where `current_config.yml` already existed), the `path` key was never injected, leaving the configuration incomplete.
**The Fix:** Modified `compass_engine.py` (`_create_new_sesssion_ID_and_directory`) to *always* assign `path`, `path_generic`, and `ID` to the session's configuration object in memory, even if it skips writing to `current_config.yml` because the file already exists.

### Error 18: Plotly Crash (`FileNotFoundError: Validator JSON file not found`)
**The Issue:** When attempting to load any dashboard that renders a plot (like the Upload or Bioequivalence section), the application crashes with a `FileNotFoundError` complaining about a missing `plotly\validators\_validators.json` in the `%TEMP%` extraction folder. This occurs because `plotly` relies heavily on internal JSON data files for its plotting logic, and Nuitka only bundles `.py` code files by default.
**The Fix:** Added `--include-package-data=plotly` to the Nuitka build command to force the inclusion of all JSON and supporting files located inside the `plotly` module directory.

### Error 19: Plotly Kaleido Crash on "Fit Dissolution" (`ValueError: The kaleido executable is required`)
**The Issue:** When clicking "Fit dissolution" in the Load Dashboard, the application backend threw a `ValueError` because the `kaleido` python library (used by Plotly to generate static images) could not find its bundled `kaleido.cmd` executable. Nuitka only packages python code, leaving the crucial `executable` directory behind.
**The Fix:** Using `--include-data-dir=...kaleido=kaleido` is insufficient because Nuitka deliberately strips executable binaries (`.exe`, `.dll`) out of included data directories. To correctly package the embedded headless Chromium browser, we must add explicit file overrides:
`--include-data-files=c:\...\kaleido\executable\bin\kaleido.exe=kaleido\executable\bin\kaleido.exe`
`--include-data-files=c:\...\kaleido\executable\bin\swiftshader\*.dll=kaleido\executable\bin\swiftshader\`

### Error 20: Panel Thread-Safety Document Lock Loss (Silent Frontend Updates)
**The Issue:** Even after resolving all backend and compilation crashes, clicking the "Fit dissolution" button successfully processed heavy calculations in the background but failed to transition the UI to the next dashboard. The original code wrapped dashboard generation in a background thread via `asyncio.to_thread()` to prevent freezing the UI spinner, but it incorrectly mutated the main layout (`self.for_main[:] = [dashboard]`) from within that external background thread. Modifying Panel/Bokeh documents outside the main Tornado `IOLoop` thread without holding the document lock causes the frontend to silently drop the UI updates.
**The Fix:** Refactored `compass_engine.py` to decouple layout generation from mutation. The background thread now returns the generated dashboard, and the main thread uses `pn.state.curdoc.add_next_tick_callback()` to safely apply the UI transition on the primary Tornado event loop with the document lock held.

---

## 4. The Final Nuitka Compilation Command

This is the ultimate Nuitka command resulting from all the fixes above. It explicitly ignores Numba caching, includes all required dynamic dependencies (`pandas`, `scipy`, `openpyxl`), forces inclusion of Numba C-libraries (`*.dll.a`), manually maps both Bokeh and Panel static Javascript asset directories, bundles the `app` internal configuration data files (`frontend_conf.yaml`), bundles the `static` imagery directory (`.png`/`.ico`), bundles all `plotly` internal JSON data files, and aggressively bundles the entire `kaleido` binary payload.


[/goal]Create a working `.exe` file by executing the following strict workflow:
1. **Compile:** Run `.\build.ps1` to compile the application.
2. **Handle Build Errors:** If Nuitka compilation fails, read the logs, fix the python code or the `build.ps1` configuration, and restart compilation.
3. **Test:** Once built, run the E2E test suite against the compiled executable by executing it via the dev environment:
   ```powershell
   .\.venv\Scripts\pytest.exe _internal/tests_e2e/
   ```
4. **Handle Runtime Errors:** If the E2E tests fail:
   - Review the crash logs.
   - Clean up the Nuitka temp extraction folder to prevent disk exhaustion: `Remove-Item "$env:TEMP\onefile_*" -Recurse -Force -ErrorAction SilentlyContinue`
   - Fix the underlying code or compilation configuration.
   - Completely delete the `compilation` directory to ensure a clean cache.
   - Restart the process from Step 1.
5. **Circuit Breaker:** If you fail 3 times in a row, STOP and ask the user for help. Do not get stuck in an infinite compilation loop.
6. **Resource Exhaustion:** If your AI model usage or resources become exhausted, you must pause and retry after 1 hour. Continue to retry every hour until resources are available again.

```powershell
.\build.ps1
```

---

### Error 21: `EXCEPTION_ILLEGAL_INSTRUCTION` (0xC000001D) Crash on Older Windows CPUs
**The Issue:** The `.exe` built successfully but instantly died with no logs when executed on a Windows 11 machine with an older Intel i7-6700 CPU. The Windows Event Viewer (`Application` -> `Event 1000`) flagged `run_compass.exe` as failing with Exception Code `c000001d`. This occurred because Nuitka defaults to using the `zig` C-compiler backend, and Zig's internal linking engine aggressively optimizes the binary for the host machine's architecture (AMD EPYC AVX-512). It stubbornly ignores standard `$env:CFLAGS` architecture overrides (`-mcpu=x86_64_v2`) during the final linking phase on Windows, causing it to inject unsupported instructions into the executable.
**The Fix:** Because Nuitka disabled `MinGW64` support for Python 3.13+, we were forced to abandon Zig and use **Microsoft Visual Studio Build Tools (MSVC)**. MSVC is the native Windows compiler and inherently produces flawlessly generic, compatible binaries without aggressively injecting host-native CPU vector optimizations. We also maintained the `--lto=no` flag to strictly prevent Link Time Optimization from leaking native instructions. (Note: The `-march=x86_64` flag was originally used to control Zig's output, but it has been removed from `build.ps1` because MSVC does not recognize it and generates `cl : Command line warning D9002 : ignoring unknown option '-march=x86_64'`.)

**How to Install MSVC:**
1. Download **Build Tools for Visual Studio 2022** from the [Visual Studio Downloads page](https://visualstudio.microsoft.com/downloads/).
2. In the installer, select the **Desktop development with C++** workload.
3. Ensure these two components are checked on the right side:
   - **MSVC v143 - VS 2022 C++ x64/x86 build tools**
   - **Windows 11 SDK** (or Windows 10 SDK)
4. Restart your terminal. Nuitka will automatically detect and prioritize MSVC over Zig when `.\build.ps1` is run.

---

## 5. Global Exception Hook & Safe I/O

To aid in debugging the compiled `.exe` without needing a console window, we implemented two massive architectural improvements:

### Global Logging & Exception Catching
We created a global `CompassLogger` (`../app/core/logger.py`). Rather than wrapping every function in a clunky `TryCatch` class, we implemented a true global failsafe:
1. **`sys.excepthook`:** Catching any fatal startup crashes on the main thread (like missing Nuitka dependencies) and instantly dumping a `../logs/FATAL_CRASH_REPORT.txt` containing the traceback, `sys.executable`, and working directory.
2. **Tornado Monkey-Patching:** Because Panel relies on Tornado for its background async loop, unhandled exceptions in UI callbacks (like a button click crashing) are normally swallowed silently. We successfully patched `tornado.web.RequestHandler.log_exception` to route *all* background crashes directly into `CompassLogger`.

### Safe File Manager
We centralized all file reads/writes across the 27 frontend modules into a Singleton `SafeFileManager` (`../app/core/file_manager.py`). 
*   It securely relays operations to Pandas/YAML while utilizing dynamic `.exe` path detection (`os.path.abspath(sys.argv[0])`) to ensure user data is never saved into the temporary `%TEMP%` unpack folder. 
*   It automatically handles missing folder creation and gracefully returns `None` on failures to prevent cascading crashes.

---

## 6. Testing & Validation

### Error 22: Disk Space Exhaustion from Temp Unpack Directories
**The Issue:** Running the E2E test suite in a loop against the generated `run_compass.exe` caused the Tornado server to randomly fail booting with `OSError: [Errno 28] No space left on device` at `tempfile.py:520`. 
**The Reason:** Nuitka `--onefile` payload extracts a large directory (over a gigabyte of data due to SciPy/Plotly dependencies) to `%LOCALAPPDATA%\Temp\onefile_XXXXX` every time it executes. If the `exe` crashes or is force-killed by the test runner before it can cleanly wipe its temp folder, the drive quickly runs out of space.
**The Fix:** Added a manual Powershell purge command (`Remove-Item "$env:TEMP\onefile_*" -Recurse -Force -ErrorAction SilentlyContinue`) between large E2E test iterations to ensure the disk remains healthy.

### Error 23: Playwright Locators Out-of-Sync with Modernized UI
**The Issue:** The E2E tests timed out failing to click `button:has-text("Clean session data")`.
**The Reason:** The UI was updated to make the button an icon-only element (`name=''`, only `icon='trash'`), meaning Playwright could no longer identify it by visible text.
**The Fix:** Added an explicit hook `css_classes=['e2e-clean-session']` into `app/main.py` specifically for E2E testing, and updated the Pytest suite to find `.e2e-clean-session button` instead.

### Error 24: E2E Clean-Directory Sandbox Data Leakage
**The Issue:** When copying `run_compass.exe` into a completely empty `clean_test_dir` and running the E2E test suite against it, the login test randomly failed with `AssertionError`.
**The Reason:** The E2E tests run `reset_users_file()` before every test to clear the user database. However, `conftest.py` hardcoded the reset to the *source* project folder's `data/users.txt`. Meanwhile, the `run_compass.exe` running in `clean_test_dir` was generating its own isolated sandbox `data/users.txt`. The tests were resetting the wrong database, leading to unexpected lockout states.
**The Fix:** Modified `_internal/tests_e2e/conftest.py` to respect a `TEST_EXE_CWD` environment variable, forcing the test suite to reset the `data/users.txt` strictly inside the same directory where the executable is being run.

### Error 25: Nuitka Bloat from Nested Test Suites
**The Issue:** Nuitka's dependency parser was aggressively crawling through the internal test suites of heavily nested scientific libraries (`scipy`, `numpy`, `pandas`), which artificially prolonged compilation time and dragged `pytest` binaries into the final payload.
**The Fix:** Added strict wildcard blocklists to `build.ps1` (`--nofollow-import-to=scipy.*.tests`, `--nofollow-import-to=scipy.*.*.tests`, `--nofollow-import-to=pytest`, etc.) to definitively sever all recursive test scraping.

### Error 26: Playwright UI Timeouts Masking Backend Crashes
**The Issue:** If a complex calculation (like Dissolution Fitting) crashed with a fatal Python exception in the background `.exe`, the UI would simply hang. Playwright would sit for 30 seconds waiting for the next button to appear, eventually failing with a generic `TimeoutError` that completely obscured the real Python traceback.
**The Fix:** Rewrote the `catch_backend_errors` Pytest fixture. It now leverages the dynamic `ROOT_DIR` to locate the active `run-*.log` JSON logfile. By measuring the file's byte-size (`f.seek(start_size)`) at the exact start of a test, the fixture parses only the logs generated during that specific test's lifespan. If any backend `"error"` is detected, Pytest instantly fails the test and dumps the actual Python traceback, bypassing the UI timeout entirely.

---

## 7. Nuitka Commercial + Themida Maximum Security Pipeline (`C:\Compilation`)

For release builds requiring military-grade code protection, anti-tampering, constant encryption, and VM virtualization, the build pipeline utilizes **Nuitka Commercial** integrated with **Themida**.

### Core Architecture & Build Target: `C:\Compilation`
- **Root Directory:** `C:\Compilation`
- **Distribution Directory:** `C:\Compilation\run_compass.dist`
- **Build Work Directory:** `C:\Compilation\run_compass.build`
- **Compiler Cache:** `C:\Compilation\clcache`
- **Final Output Executable & Runtime Directory:** `C:\Compilation\exe\run_compass.exe`

### Key Protections & Optimizations Applied
1. **MSVC x64 Hosted Toolset:** `$env:PreferredToolArchitecture = "x64"` is strictly set to prevent 32-bit compiler heap exhaustion (`fatal error C1060 / C1002 in pass 2`) when compiling massive SciPy C translation units with parallel jobs.
2. **Parallel Jobs:** Configured to `--jobs=8` on multi-core workstations (e.g. 12th Gen Intel Core i7-12700K 12 cores / 20 threads) with 32 GB RAM.
3. **Themida DLL Bundling Policy:**
   - **Force-bundled inside protected VM:** Category 1 proprietary C++ models:
     `--themida-bundled-files=*compass_models.dll`
     `--themida-bundled-files=*safe_space_calc.dll`
     `--themida-bundled-files=*Sim_Rapid.dll`
   - **Unbundled for stability:** Standard open-source runtimes and extensions (`--themida-unbundled-files=*.dll`, `--themida-unbundled-files=*.pyd`).
4. **Data Hiding & Traceback Encryption:** Dynamic GUID salt value for encrypted constant blobs (`--enable-plugin=data-hiding`) and encrypted line numbers (`--obfuscate-line-numbers=encrypted`).
5. **Runtime Compatibility:**
   - Kept annotations enabled (no `--python-flag=no_annotations`) to preserve Python dataclasses required by Tornado and Bokeh.
   - Omitted Nuitka anti-debugger plugin and `--themida-sandbox-monitors` to eliminate crashes with Windows 11 Hyper-V / Virtualization-Based Security (VBS).

### Build Script
Located at: `build-nuitka-comm-themida.ps1`
Run via:
```powershell
powershell.exe -ExecutionPolicy Bypass -File .\build-nuitka-comm-themida.ps1
```


---

## Appendix: Nuitka `--onefile` Traps (moved from root agent doc)

### The `__file__` Variable
A `--onefile` exe extracts itself into a temp folder (e.g. `C:\Users\<user>\AppData\Local\Temp\onefile_XYZ\`). `os.path.dirname(__file__)` points there, so anything saved relative to `__file__` (CSVs, YAML config) is **deleted when the exe closes**. Save data relative to `os.path.dirname(sys.argv[0])`, the physical exe directory.

### Panel Resource 404s
`--onefile` breaks Panel's static resource routing (Bokeh JS). `run_compass.py` patches `panel.io.resources.DIST_DIR` to the `_unpack` directory when running as an exe.

### Missing Sub-Dependencies
Nuitka can't see dynamic imports. Include explicitly: `--include-package=openpyxl` (pandas `read_excel`), `--include-package=scipy`.
