# Utwardzanie aplikacji Compass (Nuitka Commercial + Themida)

> **Źródło prawdy:** skrypt builda `C:\Compilation\build-nuitka-comm-themida.ps1` (w repo Compass: `build-nuitka-comm-themida.ps1`). Stan zweryfikowany 2026-11-13 wobec skryptu i historii jego backupów.
>
> Ten dokument to **jedyne** miejsce opisujące ochronę binarki hosta: koncepcję warstw, aktualny stan flag (co włączone / co wyłączone do testów i do przywrócenia) oraz checklistę produkcyjną.

## 1. Po co to

Aplikacja hosta dla Windows (Compass) współpracuje z bezpiecznym donglem USB. Gdyby aplikację dało się łatwo zdekompilować (np. standardowy bytecode Pythona), atakujący mógłby odtworzyć klucze kryptograficzne metodą inżynierii wstecznej albo wyciąć patchem sprawdzanie licencji. Dlatego stosowany jest obowiązkowy, wielowarstwowy proces zaciemniania i wirtualizacji. Wymaganie brzmi: kodu i funkcji **NIE DA SIĘ UKRAŚĆ / PODEJRZEĆ**.

Uwaga: sekret `admin_pin` **nie znajduje się w binarce hosta** — żyje na donglu — więc jego „ukrycie" w hoście nie jest tu czynnikiem.

## 2. Warstwy ochrony

### Warstwa 1: Nuitka Commercial
Konwertuje kod źródłowy Pythona bezpośrednio na zoptymalizowany kod C/C++, kompilowany do natywnego `.exe`. Całkowicie eliminuje bytecode Pythona (`.pyc`), przez co `uncompyle6`, `pyinstxtractor` itp. stają się bezużyteczne — inżynieria wsteczna jest tak trudna jak dla zwykłych binariów C++.

### Warstwa 2: Wirtualizacja Themida zaznaczonych regionów (`marker.start()/end()`)
To **funkcja Themidy, nie Nuitki** — build nie używa żadnej „Nuitka VM". Themida przekształca w bytecode swojej maszyny wirtualnej **wyłącznie oznaczone bloki kodu hosta**: regiony `marker.start()/end()` zaznaczone pluginem `vm_marker_plugin.py` (`--user-plugin=build_plugins/vm_marker_plugin.py`, skrypt linia 224, komentarz „ENABLED"), rodzina VM przez env `COMPASS_VM_MACRO`, domyślnie **`VM_FISH_WHITE`** (najlżejsza/najszybsza). Markery m.in. w `app/frontend/compass_pk.py` i `disso_fitting.py`.

**Zasięg i ograniczenie:** wirtualizacja obejmuje tylko oznaczone regiony, nie cały kod ani wszystkie stałe. `--themida-encrypt-strings` szyfruje stringi w pliku, ale dekoduje je w RAM, więc **zrzut pamięci może ujawnić część stałych** — nie zakładaj bezwarunkowej odporności. **Opcja wzmocnienia:** cięższa rodzina VM (np. Tiger/Dolphin) dla krytycznych regionów — kosztem wydajności.

### Warstwa 3: Themida (opakowanie finalnego `.exe`)
Komercyjny system ochrony opakowujący binarkę Nuitki: Anti-Debugger (własny silnik Themidy), Anti-Dump (blokada zrzutu rozpakowanej binarki z RAM), wirtualizacja fragmentów natywnego kodu x86/x64. Ochrona Anti-VM jest tu **obecnie wyłączona** — zob. §4.

## 3. Włączone obecnie (potwierdzone w skrypcie)

| Flaga | Co chroni |
|---|---|
| `--enable-plugin=themida` | Włącza opakowanie Themidą (wymagane dla pozostałych `--themida-*`). |
| `--themida-entrypoint-obfuscation` | Zaciemnia punkt wejścia — utrudnia znalezienie startu kodu i OEP przy dumpowaniu. |
| `--themida-antipatching` | Wykrywa modyfikację pliku `.exe` (łatanie bajtów, np. wycięcie sprawdzania licencji). |
| `--themida-encrypt-strings` | Szyfruje stałe tekstowe — utrudnia wyszukiwanie stringów (komunikaty, ścieżki). |
| `--themida-advanced-option=OPTION_MACROS_INTEGRITY_CHECKS=true` | Kontrola integralności chronionych makr/regionów VM. |
| Wirtualizacja VM zaznaczonych regionów (Warstwa 2) | Krytyczny kod hosta jako bytecode VM Themidy. |

Opcja stabilnościowa (nie bezpieczeństwo): `--themida-no-compression` (unika problemów z ładowaniem z VFS RAM).

## 4. Wyłączone „do testów" — **DO PRZYWRÓCENIA przed produkcją**

Wszystkie poniższe były **włączone 2026-10-13** i zostały usunięte ze skryptu **ok. 2026-10-19** (pierwszy build bez nich), głównie z powodu crashy pod **Windows 11 z Virtualization-Based Security (VBS) / Hyper-V** na maszynach deweloperskich.

| Flaga / plugin | Co chroni | Czemu wyłączone | Warunek przywrócenia |
|---|---|---|---|
| `--themida-sandbox-monitors` | **Anti-VM / wykrywanie monitorów** (sandbox, monitory plików/rejestru) — główna ochrona przed analizą w VM. | Kolizja z Win11 VBS/Hyper-V (system wygląda jak „VM"). | Build produkcyjny na **bare-metal** (bez VBS) lub maszynie klienta — wtedy **włączyć z powrotem**. |
| `--enable-plugin=anti-debugger` | **Anti-Debugger Nuitki** — wykrywa x64dbg/OllyDbg/GDB i wywala proces. | Ta sama kolizja z VBS/Hyper-V. | Przywrócić w finalnym buildzie produkcyjnym. |
| `--enable-plugin=data-hiding` | **Szyfrowanie stałych/blobów** (dynamiczny GUID-salt) — ukrywa wkompilowane dane; bez niego stałe w zrzucie RAM mogą być widoczne. | Usunięte przy upraszczaniu builda do testów. | Przywrócić — nie koliduje z VBS, brak powodu, by było wyłączone w produkcji. |
| `--enable-plugin=traceback-encryption` | **Szyfrowanie numerów linii / tracebacków** — utrudnia mapowanie kodu z błędów. | Usunięte przy upraszczaniu. | Przywrócić w produkcji. |

## 5. Uwagi / pułapki

* **`--experimental=debug-report-traceback` (obecnie w skrypcie, linia ~217) to pomoc deweloperska — USUŃ w produkcji.** Eksponuje tracebacki, czyli działa **odwrotnie** niż `traceback-encryption` z §4.
* **Biblioteki open-source rozpakowane „na dysk" (unbundled) są poza chronioną VM Themidy** — `plotly`, `kaleido`, `openblas`, `libffi`, `libssl`/`libcrypto`, `numpy _multiarray_umath`, `cryptography`, `nh3` i inne są celowo odbundlowane (crashe/wolne działanie przy ładowaniu z VFS RAM). To **akceptowalne**: nie są to zastrzeżone algorytmy. Zastrzeżone modele C++ (`compass_models.dll`, `safe_space_calc.dll`, `Sim_Rapid.dll`) **są** bundlowane i chronione (EXTRACT_NEVER).
* **Dystrybucja folderowa, nie `--onefile`:** build produkcyjny używa `--mode=standalone` (`run_compass.dist` → `C:\Compilation\exe\run_compass.exe`). Klasyczne pułapki `--onefile` (rozpakowanie >1 GB do `%TEMP%\onefile_XXXXX`) **nie dotyczą** produkcji — tylko deweloperskiego builda `--onefile` (`build.ps1`).
* [`compilation.md`](../compilation/compilation.md) §7 opisuje `--enable-plugin=data-hiding` i `--obfuscate-line-numbers=encrypted` jako włączone — **to już nieaktualne** wobec bieżącego skryptu; ten dokument odzwierciedla realny stan.
* **Logi awaryjne (`CompassLogger`):** singleton podmienia (monkey-patch) `sys.excepthook` i `log_exception` Tornado, więc każda awaria — także wywołana mechanizmem bezpieczeństwa (odłączenie dongla, zmodyfikowana pamięć) — generuje `FATAL_CRASH_REPORT.txt` z pełnym stack trace i kontekstem. Ochrona Themidy (wirtualizacja + szyfrowanie stringów) ma to zaciemniać; przy wyłączonym `data-hiding` stałe w zrzucie RAM mogą być widoczne.
* **Numba JIT vs reguły pamięci Themidy:** część funkcji matematycznych (Numba) kompiluje się do kodu maszynowego w trakcie działania. Trzeba to zgrać z regułami ochrony pamięci Themidy, by uniknąć fałszywych awarii (naruszenia DEP/NX).

## 6. Checklista przed finalnym buildem produkcyjnym

Build na maszynie docelowej / bare-metal (bez VBS/Hyper-V), potem odhaczyć:

- [ ] `--themida-sandbox-monitors` — przywrócone
- [ ] `--enable-plugin=anti-debugger` — przywrócone
- [ ] `--enable-plugin=data-hiding` — przywrócone
- [ ] `--enable-plugin=traceback-encryption` — przywrócone
- [ ] `--experimental=debug-report-traceback` — **usunięte**
- [ ] (opcjonalnie) cięższa wirtualizacja VM krytycznych regionów hosta
- [ ] Build przechodzi i `.exe` startuje na sprzęcie docelowym (nie w VM deweloperskiej)
- [ ] Szybki test: uruchomienie pod debuggerem/VM powinno zostać zablokowane
