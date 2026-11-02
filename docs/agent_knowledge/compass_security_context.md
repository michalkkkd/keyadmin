# Aplikacja Compass - kontekst bezpieczeństwa

Ten dokument zbiera kluczowe informacje dotyczące bezpieczeństwa głównej aplikacji hosta dla Windows (Compass) oraz jej integracji z KeySec i compass_api.

## 1. Kompletny pakiet ochrony (Nuitka Commercial i Themida)
Główna aplikacja (Compass) działa w modelu zero-trust i jest wzmocniona komercyjnym zestawem zabezpieczeń:
* **Nuitka Commercial:** Tłumaczy cały ekosystem Pythona na natywny kod C/C++, całkowicie eliminując bytecode Pythona (.pyc).
* **Nuitka VM:** Wirtualizuje przepływ wykonania i szyfruje krytyczne stałe.
* **Themida:** Opakowuje finalny plik wykonywalny, zapewniając bardzo silną ochronę Anti-Dump, Anti-Debug i Anti-VM, a także wirtualizację kodu.

**KRYTYCZNA UWAGA DOTYCZĄCA WDROŻENIA:** Dzięki temu komercyjnemu zestawowi zabezpieczeń typowe problemy pakowania aplikacji Pythona (np. znane podatności Nuitka --onefile związane z rozpakowywaniem do folderu %TEMP%) **NIE MAJĄ ZASTOSOWANIA**. Wykonanie jest silnie zwirtualizowane i chronione przed monitorowaniem rozpakowywania plików na dysk.

## 2. Globalna obsługa błędów i telemetria
* **CompassLogger:** Aplikacja ma globalny logger typu singleton, który podmienia (monkey-patching) sys.excepthook oraz log_exception z Tornado. 
  - **Konsekwencja dla bezpieczeństwa:** Każda awaria, także wywołana przez mechanizmy bezpieczeństwa (np. odłączenie dongla, zmodyfikowana pamięć), wygeneruje plik FATAL_CRASH_REPORT.txt z pełnymi stack trace'ami i kontekstem. Trzeba zadbać o to, by Nuitka VM wystarczająco zaciemniała te dane i nie ujawniała atakującemu logiki w postaci jawnego tekstu.

## 3. Zarządzanie sesjami
* **Charakter serwera WWW:** Compass działa jako lokalny serwer WWW (Tornado). Wielu użytkowników może się z nim łączyć przez sesje przeglądarki.
* **Przechowywanie sesji:** Sesje są zarządzane dynamicznie (np. data/session/session_store.json). Obecnie plik mapuje tokeny (takie jak MY_SUPER_SECRET_TOKEN_E2E) na adresy e-mail użytkowników i timestampy created_at. 
  - **Konsekwencja dla bezpieczeństwa:** Ponieważ aplikacja działa jako serwer, egzekwowanie „limitu użytkowników” wymaga śledzenia aktywnych sesji po stronie backendu i przekazania tego egzekwowania sprzętowemu donglowi KeySec.

## 4. Zależności
* Aplikacja korzysta ze złożonych bibliotek dynamicznych (Pandas, Numba, Scipy), które są osadzone i zaciemnione. Użycie Numby (kompilacja JIT) oznacza, że część funkcji matematycznych jest kompilowana do kodu maszynowego w trakcie działania programu. Trzeba to starannie zgrać z regułami ochrony pamięci Themidy, aby uniknąć fałszywie pozytywnych awarii (np. naruszeń DEP/NX).
