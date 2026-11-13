# Core Architecture & UI

*   **Framework:** Python + **[HoloViz Panel](https://panel.holoviz.org/)** (Bokeh and Tornado under the hood) for the frontend UI.
*   **Design Pattern:** UI follows a modular `Viewer` base class pattern. Dashboards (`SSD_dashboard`, `pkclv1_dashboard`, etc.) are individual modules in `app/frontend/`.
*   **Entry Point:** `run_compass.py` is the root of the application. It bootstraps the environment, applies monkey-patches, registers global logging hooks, and initializes `pn.serve()`.

## Known Dependencies

### Core Frameworks
*   **HoloViz Panel** (and `bokeh`): frontend. `DIST_DIR` must be mapped to the `_unpack` folder after Nuitka compilation so JS/CSS are served.
*   **tornado**: async web server for Panel. `log_exception` is monkey-patched in `app/logger.py` to route UI background crashes into `log.json`.

### Data & Mathematics
*   **pandas**: central to I/O. `read_excel` dynamically imports `openpyxl` (needs `--include-package=openpyxl` in Nuitka).
*   **numpy** & **scipy**: scipy needs `--include-package=scipy` explicitly.
*   **numbalsoda** & **numba**: JIT compilation and ODE solvers (see `numbalsoda.md`).

### File I/O & Formatting
*   **PyYAML**: parses `current_config.yml` and session data via `SafeFileManager().read_yaml()`.
*   **openpyxl**: Excel read/write in pandas. Must be forced into the Nuitka build.
*   **tabulate**: text tables.
*   **reportlab**: native PDF reports.
