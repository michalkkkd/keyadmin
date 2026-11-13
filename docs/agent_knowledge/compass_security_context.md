# Aplikacja Compass - kontekst bezpieczeństwa

Ten dokument zbiera kluczowe informacje dotyczące bezpieczeństwa głównej aplikacji hosta dla Windows (Compass) oraz jej integracji z KeySec i compass_api.

## 1. Kompletny pakiet ochrony (Nuitka Commercial i Themida)
Główna aplikacja (Compass) działa w modelu zero-trust i jest wzmocniona komercyjnym zestawem zabezpieczeń:
* **Nuitka Commercial:** Tłumaczy cały ekosystem Pythona na natywny kod C/C++, całkowicie eliminując bytecode Pythona (.pyc).
* **Wirtualizacja Themida (regiony `marker.start()/end()`):** wirtualizuje **wyłącznie oznaczone bloki** kodu hosta (plugin `vm_marker_plugin.py`, rodzina `VM_FISH_WHITE`) — to funkcja Themidy, **nie Nuitki** (build nie używa żadnej „Nuitka VM"). Szyfrowanie stałych Nuitki (`--enable-plugin=data-hiding`) jest **obecnie wyłączone**; aktywne jest tylko `--themida-encrypt-strings` (stringi, dekodowane w RAM).
* **Themida:** Opakowuje finalny plik wykonywalny, zapewniając ochronę Anti-Dump, Anti-Debug (własny silnik Themidy) i wirtualizację kodu. **Anti-VM (`--themida-sandbox-monitors`) jest w buildzie produkcyjnym WYŁĄCZONE** (kolizja z Windows 11 VBS/Hyper-V — zob. `../security/themida_nuitka_hardening.md`).

**UWAGA WDROŻENIOWA:** Chroniony build produkcyjny ([`build-nuitka-comm-themida.ps1`](../../../Compass/build-nuitka-comm-themida.ps1):210) używa **`--mode=standalone`** — **dystrybucja folderowa** (`run_compass.dist` → `C:\Compilation\exe\run_compass.exe`), **NIE** `--onefile`. Dlatego klasyczne pułapki `--onefile` (rozpakowanie >1 GB do `%TEMP%\onefile_XXXXX`) **nie dotyczą** builda produkcyjnego — występują wyłącznie w deweloperskim buildzie `--onefile` (`build.ps1`). Zastrzeżone silniki C++ (`compass_models.dll`, `safe_space_calc.dll`, `Sim_Rapid.dll`) są bundlowane do chronionej VM Themidy (EXTRACT_NEVER), a reszta folderu `.dist` jest opancerzona Themidą.

## 2. Globalna obsługa błędów i telemetria
* **CompassLogger:** Aplikacja ma globalny logger typu singleton, który podmienia (monkey-patching) sys.excepthook oraz log_exception z Tornado. 
  - **Konsekwencja dla bezpieczeństwa:** Każda awaria, także wywołana przez mechanizmy bezpieczeństwa (np. odłączenie dongla, zmodyfikowana pamięć), wygeneruje plik FATAL_CRASH_REPORT.txt z pełnymi stack trace'ami i kontekstem. Trzeba zadbać o to, by ochrona Themidy (wirtualizacja oznaczonych regionów + szyfrowanie stringów) wystarczająco zaciemniała te dane i nie ujawniała atakującemu logiki w postaci jawnego tekstu. Uwaga: szyfrowanie stałych Nuitki (`data-hiding`) jest obecnie wyłączone, więc stałe w zrzucie RAM mogą być widoczne.

## 3. Zarządzanie sesjami
* **Charakter serwera WWW:** Compass działa jako lokalny serwer WWW (Tornado). Wielu użytkowników może się z nim łączyć przez sesje przeglądarki.
* **Przechowywanie sesji:** Sesje są zarządzane dynamicznie (np. data/session/session_store.json). Obecnie plik mapuje tokeny (takie jak MY_SUPER_SECRET_TOKEN_E2E) na adresy e-mail użytkowników i timestampy created_at. 
  - **Konsekwencja dla bezpieczeństwa:** Ponieważ aplikacja działa jako serwer, egzekwowanie „limitu użytkowników” wymaga śledzenia aktywnych sesji po stronie backendu i przekazania tego egzekwowania sprzętowemu donglowi KeySec.

## 4. Zależności
* Aplikacja korzysta ze złożonych bibliotek dynamicznych (Pandas, Numba, Scipy), które są osadzone i zaciemnione. Użycie Numby (kompilacja JIT) oznacza, że część funkcji matematycznych jest kompilowana do kodu maszynowego w trakcie działania programu. Trzeba to starannie zgrać z regułami ochrony pamięci Themidy, aby uniknąć fałszywie pozytywnych awarii (np. naruszeń DEP/NX).
