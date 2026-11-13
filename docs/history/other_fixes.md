# Other Fixes and Bug Squashing

## Overview
Several highly critical state management and parsing bugs were addressed during this session. These bugs previously caused hard crashes across different dashboard modes (especially after cleaning session data).

## What We Changed
1. **The `app_conf` Detachment Bug (`LoadDashboard._reset_app_conf`)**
   - **The Problem:** When a session was cleared and a fresh file uploaded, `load_dashboard.py` attempted to reset configurations by reading the generic `current_config.yml`. It did this by reassigning `self.app_conf = SafeFileManager().read_yaml(...)`. Because `self.app_conf` was just a reference to `self.app.conf` inside `CompassEngine`, reassigning it severed the link between the dashboard and the engine. As a result, subsequent dashboard initializations (like `DissoDashboard`) pulled the stale, empty `_app.conf` dictionary from memory and crashed with `KeyError: 'formulation'`.
   - **The Solution:** Modified `_reset_app_conf` to use an in-place `.update()` pattern rather than variable reassignment:
     ```python
     new_conf = SafeFileManager().read_yaml(file_name)
     self.app_conf.clear()
     self.app_conf.update(new_conf)
     ```
   - This ensures the UI memory stays perfectly synchronized with the global engine state.

2. **IndexOutOfBounds Error in `disso_fitting_1f`**
   - **The Problem:** Depending on the matrix size or data parsing, dissolution fitting arrays sometimes caused an `IndexError: list index out of range` when generating trace markers or plots.
   - **The Solution:** Implemented robust bounds checking utilizing `min(len(arr) - 1, idx)` and modulo arithmetic to safely cap indices without crashing the layout generator.

3. **Missing `e` Event Parameter (`clean_data`)**
   - **The Problem:** A callback function (`clean_data`) bound to a Panel widget missed the required positional event parameter, throwing an error when the widget was clicked.
   - **The Solution:** Added the single `event` parameter to the callback definition.

## Agent Instructions for Future Work
- Always remember that Panel applications pass references to global configuration dictionaries (`app_conf`). If you reassign the variable instead of updating it in-place, you will break the state pipeline.
- Test edge cases where user sessions are aggressively purged. Dashboard modules lack thorough `KeyError` safety checks (e.g. they blindly request `self.app_conf['formulation']` during `__init__`). Consider adding `dict.get()` with default fallbacks if further KeyError issues arise.
