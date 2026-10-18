# Compass Application - Security Context

This document extracts critical security-related information about the main Windows host application (Compass) and its integration with KeySec and compass_api.

## 1. Ultimate Protection Suite (Nuitka Commercial & Themida)
The main application (Compass) operates under a zero-trust model and is fortified using a commercial-grade protection stack:
* **Nuitka Commercial:** Translates the entire Python ecosystem into native C/C++ code, completely eliminating Python bytecode (.pyc).
* **Nuitka VM:** Virtualizes the execution flow and encrypts critical constants.
* **Themida:** Wraps the final executable, providing extreme Anti-Dump, Anti-Debug, and Anti-VM capabilities, alongside code virtualization.

**CRITICAL NOTE ON DEPLOYMENT:** Because of this commercial protection stack, standard Python packaging concerns (such as the typical Nuitka --onefile %TEMP% folder extraction vulnerabilities) **DO NOT APPLY**. The execution is heavily virtualized and protected from disk-based extraction monitoring.

## 2. Global Error Handling & Telemetry
* **CompassLogger:** The application features a global singleton logger that monkey-patches sys.excepthook and Tornado's log_exception. 
  - **Security Consequence:** Any crash, including those caused by security mechanisms (e.g., dongle disconnection, tampered memory), will generate a FATAL_CRASH_REPORT.txt containing full stack traces and context. Care must be taken to ensure Nuitka VM obfuscates this output enough so it doesn't leak plaintext logic to an attacker.

## 3. Session Management
* **Web Server Nature:** Compass acts as a local web server (Tornado). Multiple users can connect to it via browser sessions.
* **Session Storage:** Sessions are managed dynamically (e.g., data/session/session_store.json). Currently, it maps tokens (like MY_SUPER_SECRET_TOKEN_E2E) to user emails and created_at timestamps. 
  - **Security Consequence:** Because it acts as a server, enforcing the "User Limit" requires tracking active sessions on the backend and delegating that enforcement to the KeySec hardware dongle.

## 4. Dependencies
* Relies on complex dynamic libraries (Pandas, Numba, Scipy) which are embedded and obfuscated. The usage of Numba (JIT compilation) means some mathematical functions are compiled to machine code at runtime, which must be carefully aligned with Themida's memory protection rules to prevent false-positive crashes (e.g., DEP/NX violations).
