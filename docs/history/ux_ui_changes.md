# UX and UI Changes

## Overview
Significant visual and interactive improvements were applied to the application layout to make it feel more responsive, modern, and aligned with standard UX paradigms.

## What We Changed
1. **Dynamic Buttons (`button_styles.py`)**
   - **The Problem:** The default buttons provided by Panel felt static and visually unappealing.
   - **The Solution:** We introduced custom CSS classes defining various visual states (rest, hover, active).
   - We integrated these via Panel's raw CSS injection mechanism into `button_styles.py`. 
   - Available classes: `custom-btn-green`, `custom-btn-blue`, `custom-btn-red`, `custom-btn-forward`, `custom-btn-back`, `custom-btn-settings`.

2. **Loading Spinners (`@with_spinner` Decorator)**
   - **The Problem:** Long-running calculations (like `pk_calculations()`) blocked the Tornado thread, freezing the UI. Users had no visual feedback indicating that background calculations were in progress.
   - **The Solution:** We created a highly robust `@with_spinner` decorator inside `app/frontend/utils.py`. 
   - This decorator:
     1. Toggles a loading UI state (using a GIF spinner) via `event.obj.loading = True`.
     2. Yields control briefly (`await asyncio.sleep(0.05)`) to push the UI update to the client.
     3. Offloads the heavy blocking function to a background thread using `await asyncio.to_thread(func, ...)`.
   - The decorator is specifically designed with a flexible `*args, **kwargs` signature so it safely wraps both bound class methods (which take `self`) and unbounded local functions without throwing a `TypeError`.

3. **Layout Alignment**
   - Panel defaults to centering items within `Column` layouts. This looked visually awkward for standard form inputs.
   - **The Solution:** We updated the `bk-panel-models-layout-Column` configurations to use `align='start'`, ensuring left-alignment across forms, tables, and settings blocks.

4. **"Clean Session Data" Action**
   - Added an explicit "Clean session data" button to the sidebar (`_set_side_bar` in `compass_engine.py`).
   - This securely flushes the `data/session/{ID}/` directory, wiping old configurations, and triggering a clean page reload (`pn.state.location.reload = True`).

## Agent Instructions for Future Work
- Use the `@with_spinner` decorator on any button callback that requires more than ~0.5 seconds to compute. It ensures a responsive frontend and protects the Tornado event loop from being blocked by a single user on a multi-user server.
- Stick to the pre-defined CSS classes in `button_styles.py` when spawning new `pn.widgets.Button` elements to maintain UX consistency.
