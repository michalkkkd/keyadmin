# Utwardzanie Themida / Nuitka — checklista produkcyjna

> **Po co ten dokument:** w trakcie prac część opcji ochronnych Themidy/Nuitki została **celowo wyłączona, żeby w ogóle sprawdzić, czy build działa** (głównie z powodu crashy pod Windows 11 VBS / Hyper-V na stacjach deweloperskich/VM). Ten plik listuje, **co jest włączone teraz, co było włączone wcześniej i co trzeba przywrócić przed oddaniem produkcyjnym**, żeby `.exe` był bezpieczniejszy.
>
> **Źródło prawdy:** skrypt builda `C:\Compilation\build-nuitka-comm-themida.ps1` (w repo Compass: `build-nuitka-comm-themida.ps1`) oraz `Compass/_internal/agent/compilation.md §7`. Stan zweryfikowany 2026-11-13 wobec skryptu i historii jego backupów. Powiązane: [`app_protection_nuitka_themida.md`](app_protection_nuitka_themida.md).

---

## 1. Włączone obecnie (potwierdzone w skrypcie)

| Flaga | Co chroni |
|---|---|
| `--enable-plugin=themida` | Włącza opakowanie Themidą (wymagane dla pozostałych `--themida-*`). |
| `--themida-entrypoint-obfuscation` | Zaciemnia punkt wejścia — utrudnia znalezienie startu kodu i OEP przy dumpowaniu. |
| `--themida-antipatching` | Wykrywa modyfikację pliku `.exe` (łatanie bajtów, np. wycięcie sprawdzania licencji). |
| `--themida-encrypt-strings` | Szyfruje stałe tekstowe — utrudnia wyszukiwanie stringów (np. komunikatów, ścieżek). |
| `--themida-advanced-option=OPTION_MACROS_INTEGRITY_CHECKS=true` | Kontrola integralności chronionych makr/regionów VM. |

Opcja stabilnościowa (nie bezpieczeństwo): `--themida-no-compression` (unika problemów z ładowaniem z VFS RAM).

## 2. Wyłączone „do testów" — **DO PRZYWRÓCENIA przed produkcją**

Wszystkie poniższe były **włączone 2026-10-13** i zostały usunięte ze skryptu **ok. 2026-10-19** (pierwszy build bez nich), bo powodowały crashe pod **Windows 11 z Virtualization-Based Security (VBS) / Hyper-V** na maszynach deweloperskich.

| Flaga / plugin | Co chroni | Czemu wyłączone | Warunek przywrócenia |
|---|---|---|---|
| `--themida-sandbox-monitors` | **Anti-VM / wykrywanie monitorów** (sandbox, monitory plików/rejestru) — główna ochrona przed analizą w maszynie wirtualnej. | Kolizja z Win11 VBS/Hyper-V (system wygląda jak „VM"). | Build produkcyjny na **bare-metal** (bez VBS) lub maszynie docelowej klienta — wtedy **włączyć z powrotem**. |
| `--enable-plugin=anti-debugger` | **Anti-Debugger Nuitki** — wykrywa x64dbg/OllyDbg/GDB i wywala proces. | Ta sama kolizja z VBS/Hyper-V. | Jw. — przywrócić w finalnym buildzie produkcyjnym. |
| `--enable-plugin=data-hiding` | **Szyfrowanie stałych/blobów** (dynamiczny GUID-salt) — ukrywa wkompilowane dane. | Usunięte w trakcie upraszczania builda do testów. | Przywrócić — nie koliduje z VBS, brak powodu, by było wyłączone w produkcji. |
| `--enable-plugin=traceback-encryption` | **Szyfrowanie numerów linii / tracebacków** — utrudnia mapowanie kodu z błędów. | Usunięte w trakcie upraszczania. | Przywrócić w produkcji. |

## 3. Wirtualizacja VM zaznaczonych regionów — WŁĄCZONA (można wzmocnić)

| Pozycja | Co daje | Status |
|---|---|---|
| **Wirtualizacja VM zaznaczonych regionów** (`marker.start()/end()` → makra Themida VM) | Przekształca krytyczny kod hosta w bytecode maszyny wirtualnej Themidy — najtrudniejszy do inżynierii wstecznej. | **WŁĄCZONA**: `--user-plugin=build_plugins/vm_marker_plugin.py` (skrypt linia 224, komentarz „ENABLED"), rodzina VM przez env `COMPASS_VM_MACRO`, domyślnie **`VM_FISH_WHITE`** (najlżejsza/najszybsza). Markery w `app/frontend/compass_pk.py` i `disso_fitting.py`. **Opcja wzmocnienia:** cięższa rodzina VM (np. Tiger/Dolphin) dla krytycznych regionów — kosztem wydajności. |

## 4. Uwagi / pułapki

* **`--experimental=debug-report-traceback` (obecnie w skrypcie, linia ~217) to pomoc deweloperska — USUŃ w produkcji.** Eksponuje tracebacki, czyli działa **odwrotnie** niż `traceback-encryption` z §2.
* **Biblioteki open-source rozpakowane „na dysk" (unbundled) są poza chronioną VM Themidy** — `plotly`, `kaleido`, `openblas`, `libffi`, `libssl`/`libcrypto`, `numpy _multiarray_umath`, `cryptography`, `nh3` i inne są celowo odbundlowane (crashe/wolne działanie przy ładowaniu z VFS RAM). To **akceptowalne**: nie są to nasze zastrzeżone algorytmy. Zastrzeżone modele C++ (`compass_models.dll`, `safe_space_calc.dll`, `Sim_Rapid.dll`) **są** bundlowane i chronione.
* `compilation.md §7` (w repo Compass) opisuje `--enable-plugin=data-hiding` i `--obfuscate-line-numbers=encrypted` jako włączone — **to już nieaktualne** wobec bieżącego skryptu (ich tam nie ma); ten dokument odzwierciedla realny stan skryptu.

## 5. Checklista przed finalnym buildem produkcyjnym

Build na maszynie docelowej / bare-metal (bez VBS/Hyper-V), potem odhaczyć:

- [ ] `--themida-sandbox-monitors` — przywrócone
- [ ] `--enable-plugin=anti-debugger` — przywrócone
- [ ] `--enable-plugin=data-hiding` — przywrócone
- [ ] `--enable-plugin=traceback-encryption` — przywrócone
- [ ] `--experimental=debug-report-traceback` — **usunięte**
- [ ] (opcjonalnie) wirtualizacja VM krytycznych regionów hosta
- [ ] Build przechodzi i `.exe` startuje na sprzęcie docelowym (nie w VM deweloperskiej)
- [ ] Szybki test: uruchomienie pod debuggerem/VM powinno zostać zablokowane
