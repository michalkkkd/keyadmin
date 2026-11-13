# Logging Information & User Sessions

## Overview
Proper isolation of user data and diligent logging are fundamental to the Compass Engine's stability, particularly because it runs on a multi-user network server and is compiled as a Nuitka executable. 

## What We Did & Confirmed
1. **User Session Isolation (`compass_engine.py`)**
   - **Session ID Propagation:** The authenticated user's identity is passed into `CompassEngine.__init__(self, _app, user_id=...)` as a constructor argument. The session is selected in `_get_session_ID()`, which reads the URL query args `ID` and `mode` via `pn.state.session_args.get('ID')` / `get('mode')` — there is **no** `?user_id=` URL parameter.
   - **Directory Creation:** For every unique `user_id`, a dedicated session folder is generated (e.g., `data/session/admin@example.com/`). This completely isolates concurrent users from overwriting each other's configuration states or uploaded CSVs.
   - **Config Hydration:** We ensured that the fallback chain safely defaults to the `default/current_config.yml` template (`self._input_path + 'default/current_config.yml'`, exposed under the conf key `path_generic`) only if the user's specific directory lacks a configuration file. Note: the folder is `default/`, not `generic/`.

2. **Session Cleanup Protocol**
   - **Data Purging:** We implemented the "Clean session data" button to proactively flush the user's active directory. When clicked, it deletes `data/session/{ID}/` using `shutil.rmtree` and forces a page reload via `pn.state.location.reload = True`.
   - **Re-initialization Fix:** As noted in [`other_fixes.md`](../history/other_fixes.md), we patched the `_reset_app_conf` sequence to ensure that when a session is wiped and a new template is copied over, the in-memory dictionary `self.app_conf` is updated in-place rather than detached.

3. **Logging & Exception Tracing (`app/core/logger.py`)**
   - **Tornado Exception Swallowing:** Because Panel relies on Tornado's async event loop, exceptions thrown inside button clicks (callbacks) are often swallowed or difficult to trace. 
   - **CompassLogger Integration:** We utilized `CompassLogger().log_exception(e)` across our heavy `run_callback` functions (e.g., inside `@with_spinner`) to ensure that any mathematical or data-parsing failures during background threads are captured cleanly.
   - **Traceback Preservation:** The robust logging allowed us to trace the precise source of `KeyError` and `TypeError` events across the UI threads, confirming the necessity of a globally accessible logging hook that bypasses standard `sys.excepthook` limitations in Nuitka.

## Agent Instructions for Future Work
- **Never rely on global variables for user state.** Always read and write to `self.app_conf['path']` utilizing the `SafeFileManager` to guarantee that one user's uploads do not bleed into another's.
- When creating new UI callbacks (buttons, file uploads, sliders), wrap the execution logic in a `try/except` block that routes to `CompassLogger().log_exception(e)`. Without this, runtime errors on the server will fail silently, leaving the user with a frozen loading spinner and no error logs to debug.

---

## Appendix: Global Singletons (moved from root agent doc)

### SafeFileManager (`app/core/file_manager.py`)
Single source of truth for all paths and I/O. Every `open()`, `pd.read_csv`, `df.to_csv`, `yaml.load` in the frontend goes through this singleton.
1. Locked/missing file: logs an error and returns `None` instead of crashing the UI.
2. Creates missing parent directories before saving.
3. Uses `sys.argv[0]` so data is saved next to the `.exe`, not in `%TEMP%`.
Also contains `SessionManager` for per-session folders (`data/session/{ID}/`).

### CompassLogger (`app/core/logger.py`)
Global singleton; errors are never silent. Writes JSON logs to `data/logs/log.json`.
*   Traces use plain log strings, not `inspect.stack()` (performance).
*   **Global exception hook:** registered at the top of `run_compass.py`, overrides `sys.excepthook` to capture fatal boot crashes.
*   **FATAL_CRASH_REPORT:** on abrupt exe death, writes `data/logs/FATAL_CRASH_REPORT.txt` (stack trace, `sys.argv`, execution context).
*   **Tornado monkey-patch:** Panel callbacks run on Tornado's async loop where exceptions are swallowed; `register_global_hook()` patches `tornado.web.RequestHandler.log_exception` to route UI crashes into CompassLogger.
