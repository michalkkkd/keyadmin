# COMPASS E2E Testing with Playwright & Pytest

This document describes how to install, configure, and execute the End-to-End (E2E) test suite for the COMPASS application.

## 1. Installation

The E2E suite uses **Playwright** paired with **pytest**. This allows tests to automatically wait for Panel UI updates and heavy backend calculations (like `numbalsoda` dissolution fitting) without relying on brittle `time.sleep()` calls.

To install the required dependencies into the active virtual environment:

```powershell
# 1. Install the pytest plugin and playwright core
.\.venv\Scripts\python.exe -m pip install pytest pytest-playwright playwright

# 2. Download the Chromium browser engine used for headless testing
.\.venv\Scripts\playwright.exe install chromium
```

## 2. Test Architecture

The E2E tests are located in `_internal/tests_e2e/`, grouped into numbered subfolders (`00_auth/`, `01_session/`, `02_bioequivalence/`, `03_safe_space/`, `04_speed/`). Each scenario is isolated into its own test file for clear reporting.

- `conftest.py`: Contains global fixtures. **It does not boot the server** — the `compass_server` fixture is a no-op (`yield None`, *"Dummy fixture. The user runs the server manually."*), so you must start Compass yourself first (see §3). What conftest actually does: **resets `users.txt`** before tests (re-seeding `admin@example.com` / `test@example.com`), clears `playwright_state.json` for non-auth runs, forces a 1920×1080 viewport, and captures video / backend console errors on failure.
- `test_*.py`: Individual test files asserting specific DOM changes.

## 3. How to Run Tests

The test suite does **not** start the server. First launch Compass yourself in one terminal, then run `pytest` in another.

### Standard Development Mode (Python)
**Step 1 — start the server manually:**
```powershell
# COMPASS_TESTING=1 suppresses the auto-opened browser tab and the heartbeat manager (run_compass.py:130)
$env:COMPASS_TESTING="1"
.\.venv\Scripts\python.exe run_compass.py
```
**Step 2 — run the suite (second terminal):**
```powershell
.\.venv\Scripts\pytest.exe _internal/tests_e2e/
```

### Testing the Compiled Executable (.exe)
To validate the final Nuitka build, launch the compiled `run_compass.exe` with a test target. Its `TestInterceptor` (`app/run/test_interceptor.py`) then sets `TEST_USE_EXE=1` (plus `TEST_EXE_PATH` / `TEST_EXE_CWD`) and spawns `pytest` against that target for you:

```powershell
# Whole suite against the running .exe:
.\run_compass.exe --tests
# Or a single area:
.\run_compass.exe --test=00_auth/
```

### Supported Test Environment Variables
Besides the `--tests` / `--test=` exe mode above (which sets `TEST_USE_EXE` itself), the app / suite honor these:

```powershell
# Mark the boot as a test session:
$env:COMPASS_TESTING="1"
# Override the login email used by tests (default: test@example.com):
$env:COMPASS_E2E_USER_EMAIL="admin@example.com"
# Point data-load tests at a different Excel template:
$env:COMPASS_TEST_EXCEL="C:\path\to\template.xlsx"
```

> There is **no** `TEST_EXTERNAL_SERVER` flag. The test base URL is not hard-coded either — it is read from `data/config/frontend_conf.yaml` (`base_url`) by `helpers._get_base_url()`.

### Useful Pytest Commands:
- **Run a specific scenario**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/00_auth/test_1_unauthorized.py`
- **Run in "Headed" mode (Watch the browser)**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/ --headed`
- **Run with Slow-Motion (Easier to see what's happening)**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/ --headed --slowmo 1000`
- **Debug a failing test**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/ --pdb` (drop into the debugger on failure), or add `--tracing retain-on-failure` to save a Playwright trace for failed tests.

## 4. Writing New Tests

When writing new tests, always use the `page` fixture provided by `pytest-playwright` and the `compass_server` fixture to ensure the backend is running.

```python
from playwright.sync_api import Page, expect
from _internal.tests_e2e.helpers import BASE_URL

def test_example_flow(page: Page):
    # Navigate (BASE_URL comes from data/config/frontend_conf.yaml, not a fixed port)
    page.goto(BASE_URL)
    
    # Interact
    page.fill('input[placeholder="Enter your email"]', 'admin@example.com')
    page.click('button:has-text("Continue")')
    
    # Assert (Playwright automatically waits up to 30s for the element to appear)
    expect(page.locator('text=Welcome Back')).to_be_visible()
```
