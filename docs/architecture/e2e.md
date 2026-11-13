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

The E2E tests are located in `_internal/tests_e2e/`. 
Each major scenario or workflow is isolated into its own test file to ensure parallel execution safety and clear reporting.

- `conftest.py`: Contains global fixtures. It automatically boots the Tornado server in the background (using `run_compass.py` with the `COMPASS_TESTING=1` environment variable) before tests run, and tears it down afterwards. It also resets the `users.txt` file between tests.
- `test_*.py`: Individual test files asserting specific DOM changes.

## 3. How to Run Tests

### Standard Development Mode (Python)
To run the full suite against the Python source code (which boots `python run_compass.py` in the background):
```powershell
.\.venv\Scripts\pytest.exe _internal/tests_e2e/
```

### Testing the Compiled Executable (.exe)
If you have successfully compiled `run_compass.exe` via Nuitka, you can force the Pytest suite to boot and test the `.exe` directly rather than the raw Python files. This is critical for validating the final build:

```powershell
$env:TEST_USE_EXE="1"
.\.venv\Scripts\pytest.exe _internal/tests_e2e/
```

### Testing an Already Running Instance
If you have already manually launched `run_compass.exe` (or the Python script) in another terminal window, and you do not want Pytest to boot a second background server, use the external server flag:

```powershell
$env:TEST_EXTERNAL_SERVER="1"
.\.venv\Scripts\pytest.exe _internal/tests_e2e/
```

### Useful Pytest Commands:
- **Run a specific scenario**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/auth/test_1_unauthorized.py`
- **Run in "Headed" mode (Watch the browser)**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/ --headed`
- **Run with Slow-Motion (Easier to see what's happening)**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/ --headed --slowmo 1000`
- **Debug a failing test**: `.\.venv\Scripts\pytest.exe _internal/tests_e2e/ --page-on-failure` (opens the browser exactly where it failed)

## 4. Writing New Tests

When writing new tests, always use the `page` fixture provided by `pytest-playwright` and the `compass_server` fixture to ensure the backend is running.

```python
from playwright.sync_api import Page, expect

def test_example_flow(page: Page):
    # Navigate
    page.goto("http://localhost:5006")
    
    # Interact
    page.fill('input[placeholder="Enter your email"]', 'admin@example.com')
    page.click('button:has-text("Continue")')
    
    # Assert (Playwright automatically waits up to 30s for the element to appear)
    expect(page.locator('text=Welcome Back')).to_be_visible()
```
