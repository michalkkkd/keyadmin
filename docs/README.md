# Dokumentacja KeySec / KeyFirmware / Compass

Wiedza o bezpieczeństwie dongla (Seeed XIAO MG24 / EFR32MG24) i aplikacji hosta Compass.

> **Zasada DRY:** każdy temat jest opisany szczegółowo w **jednym** pliku (kanonie). Ten indeks tylko wskazuje, gdzie. Nie powielaj tu faktów — dodaj link. Overview (w tym ten plik) nigdy nie streszcza kanonu, tylko do niego kieruje.

## security/ — mechanizmy bezpieczeństwa

| Dokument | Zakres (kanon) |
|---|---|
| [hardware-security.md](security/hardware-security.md) | Krzem EFR32MG24 / Secure Vault High: status każdej funkcji sprzętowej. |
| [cryptography-and-keys.md](security/cryptography-and-keys.md) | Wszystkie klucze, handshake ECDHE, szyfrowanie kanału, cykl życia kluczy przy provisioningu. |
| [anti-tamper](security/antitamper.md) | Detekcja sabotażu, progi, log tamper (User Data), autodestrukcja, warstwa OTP/SE. |
| [secure_debug_lock.md](security/secure_debug_lock.md) | Blokada SWD, challenge-response, Command Key, tryby. |
| [provisioning.md](security/provisioning.md) | Narzędzia build/flash (`flashbat/`) i pipeline `provision_dongle.py`. |
| [time-license.md](security/time-license.md) | Zegar licencji, ochrona przed cofaniem daty. |
| [users-limit.md](security/users-limit.md) | Limit aktywnych użytkowników + sprzętowa rotacja tokenów VRX (anti-bypass). |
| [app-hardening.md](security/app-hardening.md) | Utwardzanie binarki hosta: Nuitka + Themida, flagi włączone/wyłączone, checklista produkcyjna. |
| [authentication.md](security/authentication.md) | Logowanie Compass (lokalny e-mail+hasło), jedno konto na komputer, tożsamość dla dongla. |
| [diagnostics.md](security/diagnostics.md) | Strumień DIAG (`Compass.exe --diag`), format i co trafia do klienta. |

## architecture/ — architektura

| Dokument | Zakres |
|---|---|
| [software.md](architecture/software.md) | Główne pliki, podział TrustZone, podział repozytoriów (prod/factory, keycomm/keyadmin), tabela komend TinyFrame. |
| [hardware-environment.md](architecture/hardware-environment.md) | Płytka, mostek SAMD11, komponenty SDK, bateria RTC, odkrycia i pułapki firmware. |
| [requirements.md](architecture/requirements.md) | Wymagania projektowe. |
| [compass-app.md](architecture/compass-app.md) | Architektura aplikacji Compass (PC): framework Panel/Bokeh/Tornado, entry point, zależności. |
| [logging_and_sessions.md](architecture/logging_and_sessions.md) | `SafeFileManager`, `CompassLogger`, sesje, hook Tornado. |
| [env_diff.md](architecture/env_diff.md) | Ręczne modyfikacje `.venv` wymagane do kompilacji (fingerprint środowiska). |
| [e2e.md](architecture/e2e.md) | Testy end-to-end (Playwright + pytest). |
| [Compass DMX Sitemap.drawio.xml](architecture/Compass%20DMX%20Sitemap.drawio.xml) | Mapa aplikacji (diagram, materiał referencyjny). |

## compilation/ — budowanie aplikacji (Compass)

| Dokument | Zakres |
|---|---|
| [compilation.md](compilation/compilation.md) | Build Nuitka + Themida, pułapki `__file__`/DIST_DIR/include-package, lista błędów kompilacji. |
| [compilation_models_clang.md](compilation/compilation_models_clang.md) | Statyczna kompilacja modeli Numba `@cfunc` przez Clang/LLVM dla `numbalsoda`. |
| [cpp_models_performance.md](compilation/cpp_models_performance.md) | Modele ODE w C++: wydajność, reguła bit-identyczności, benchmark/compare. |
| [nuitka_help.md](compilation/nuitka_help.md) | Pełny help CLI Nuitki (materiał referencyjny). |

> **Uwaga:** komendy build/flash w tych plikach są kanoniczne — nie zmieniać.

## firmware/ — funkcje firmware

| Dokument | Zakres |
|---|---|
| [power-and-sleep.md](firmware/power-and-sleep.md) | Zarządzanie energią, uśpienie na baterii, Wake-on-RX. |
| [uart-tuning.md](firmware/uart-tuning.md) | Strojenie buforów UART (przeciw overrun/zawieszeniom). |

## Pozostałe

| Dokument | Zakres |
|---|---|
| [audit/](audit/) | Audyt dokumentacji: [`docs-audyt-prompt.md`](audit/docs-audyt-prompt.md) (prompt), [`docs-audyt-wynik.md`](audit/docs-audyt-wynik.md) (wynik), [`security-prompt.md`](audit/security-prompt.md). |
| [prompts/python-to-c.md](prompts/python-to-c.md) | Prompt pomocniczy: migracja Python → C. |
| [history/](history/) | Log historyczny: [`Refactorings.md`](history/Refactorings.md) (rejestr refaktoringów), [`ux_ui_changes.md`](history/ux_ui_changes.md), [`other_fixes.md`](history/other_fixes.md), [`numbalsoda.md`](history/numbalsoda.md). |
| [todo.md](todo.md) | Otwarte zadania. |
