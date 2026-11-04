# Compass Authentication, One Device per Account and the Dongle User Limit

Moved here from `compass/_internal/agent/authentication.md` (2026-11-04). The code paths below are in the **compass** repository (`app/...`) unless they say otherwise. Related: [Active Users Limit Mechanism](users_limit_mechanism.md) (how the dongle counts users).

## Authentication & Keycloak Integration

### Overview
The Compass application relies on a Keycloak SSO (Single Sign-On) integration. Historically, the application handled frontend redirects via JavaScript evaluation. This approach proved highly unstable when the application was compiled with Nuitka into a standalone Windows executable (`.exe`).

### What We Changed
1. **Replaced `execute_javascript` with `pn.pane.HTML` Injection:**
   - **The Problem:** Calling `pn.state.execute_javascript()` led to `AttributeError` exceptions inside the Nuitka executable runtime.
   - **The Solution:** We bypassed direct Javascript evaluation by injecting a `pn.pane.HTML` widget containing `<script>` tags that trigger the `window.location.href` redirect to the Keycloak login server. This method is incredibly robust across both standard Python and compiled Nuitka runtimes.

2. **Session ID Passing:**
   - User identity (e.g., email) is extracted following a successful login.
   - We updated the routing architecture to pass this data cleanly via URL parameters (e.g., `?user_id=admin@example.com`).
   - `CompassEngine._get_session_ID()` successfully parses this URL parameter upon redirect to establish isolated, secure session folders named after the authenticated user (e.g., `data/session/admin@example.com/`).

### Agent Instructions for Future Work
- **DO NOT** attempt to use `pn.state.execute_javascript()` for browser-side script execution, especially related to authentication. Always use `pn.pane.HTML` script injections.
- If modifying the SSO flow, ensure that the final return redirect accurately maps the user identifier to `user_id` so that the `CompassEngine` backend correctly creates the user-specific session folder.

## One Account, One Computer at a Time
A company buys a dongle user limit (e.g. 3 concurrent users); sharing one login across several computers must not get around it. The Compass server enforces it; nothing about it is decided or encoded in the browser. `SessionGuard` (`app/auth/session_guard.py`) holds the session side of it; `app/main.py` only calls `SessionGuard.open_session()` and `SessionGuard.logout()`:
- **One token per login:** `AuthUI._handle_successful_login()` (`app/auth/auth_ui.py`) revokes every older token of the email (`SessionStore.revoke_email()`, `app/auth/session_store.py`) and issues a new one. The account works only in the browser that logged in last; a copied cookie dies with the next login. Logout also removes the token on the server (`SessionGuard.logout()`, called by the logout button in `app/main.py`), not just the browser cookie.
- **Signed out elsewhere:** `SessionGuard._watch_login_token()` checks every 3 s whether the session's token still exists; once revoked it sends the browser to the login screen with `?signed_out=1` (`AuthUI.MSG_SIGNED_OUT_ELSEWHERE`).
- **One device per account:** `app/auth/live_sessions.py` (`LIVE_SESSIONS`, in memory) holds the open sessions as email + device, where device = client IP (`AuthManager.get_session_client_ip()`, Tornado `remote_ip`) + browser (`get_session_device()`). A session of the same email from another device is refused while the first one is open with a valid token (`AuthUI.MSG_ACCOUNT_IN_USE_FMT`, login screen); logging in there takes the account over. Tabs of one browser are one device. `SessionGuard._claim_live_session()` registers the session and releases it in `on_session_destroyed`.
- Limits: several people behind one IP with copied cookies (terminal server) look like one device; an IP change of the same computer is refused until the old session is destroyed (~30 s) or the user logs in again. A second server cannot share the dongle: the COM port opens for one process only.

## Device Identity for the Dongle User Limit
The dongle limits concurrent users by a hash (CRC-32) of what keycomm gets in `set_user_email()`. That value is the email plus the browser, not the email alone:
- **The browser data stays on the server.** The login form contains `BrowserProbe` (`app/auth/browser_probe.py`, an invisible Panel `JSComponent`): the browser reports `"<screen.width>x<screen.height>|<navigator.platform>|<navigator.userAgent>"` and Panel syncs it to the server like a widget value. `_handle_successful_login()` stores it with the new token in `session_store.json` (`SessionStore.add_session(token, email, device)`); without a report it stores the request's `User-Agent`. The browser holds only `compass_auth`; no device cookie, no encoding in JavaScript.
- `AuthManager.clean_device()` keeps printable characters only and at most `DEVICE_MAX_LEN` (400): the value comes from the browser and keycomm logs it (`LOG_FMT_CHECK_LICENSE`), so no forged log lines.
- `AuthManager.get_session_device()` reads the device of the session's token (`SessionStore.get_device()`), or the request's `User-Agent` for a token stored without one. `AuthManager.get_session_license_identity()` returns `"<email>|<device>"`.
- **The email comes from the session's login token** (`get_session_login_email()`), never from the test overrides of `get_session_user_email()` (`COMPASS_E2E_ACTIVE`, `PYTEST_CURRENT_TEST`, `COMPASS_E2E_USER_EMAIL`, `INTEGRITY_USER_EMAIL`). A customer can set those environment variables; they would give every session one email, and the dongle would count all users as one. Without a logged-in browser session the overrides still apply in development (integrity runs); the compiled build returns "" there, so `XCall` refuses.
- Only the dongle-facing calls use the identity: `XCall.__init__` (`app/level_x/xcall.py`) and the two `set_user_email()` calls in `XRouter.get_compass_api()` (`app/level_x/xrouter.py`). Session folders, logs and the header still use the plain email from `get_session_user_email()`.
- The browser reports its own data, so it can lie about it. That only changes the device part of the identity; the one-device rule and the token checks above do not depend on it.

## Tests (2026-11-04, Playwright against `COMPASS_TESTING=1 run_compass.py`, https://localhost:1111)
Browser contexts with different user agents and screens act as computers; the PC's LAN address is the second IP. User `test@example.com`, password = email (E2E fixture).
- The second login signs the first browser out (notice shown), one token is left, a second tab of the same browser works.
- A copy of the cookies on another IP is refused while the account is open (`open on another computer (127.0.0.1)`); logging in there takes the account over.
- After logout the token is gone from the server and a copied cookie gives the plain login screen.
- The token in `session_store.json` carries the reported device (`2560x1440|Win32|<UA>`), the browser has only `compass_auth`, the login page has no device encoding.
- With `COMPASS_E2E_ACTIVE=1` and identical browser data, two logged-in users still get different dongle hashes.
