# Ochrona głównej aplikacji (Nuitka i Themida)

> **Checklista utwardzania (co jest włączone / co przywrócić przed produkcją):** [`themida_nuitka_hardening.md`](themida_nuitka_hardening.md). Część opcji ochronnych (m.in. `--themida-sandbox-monitors`, anti-debugger) została w trakcie prac **wyłączona do testów** — przed oddaniem produkcyjnym trzeba je przywrócić.

## 1. Przegląd
Aplikacja hosta dla Windows (Compass) współpracuje z bezpiecznym donglem USB. Jeśli aplikację hosta da się łatwo zdekompilować (np. standardowy bytecode Pythona), atakujący może po prostu wydobyć `admin_pin`, odtworzyć klucze kryptograficzne metodą inżynierii wstecznej albo wyciąć patchem sprawdzanie licencji. Aby temu zapobiec, stosowany jest obowiązkowy, wielowarstwowy proces zaciemniania i wirtualizacji.

## 2. Warstwy ochrony

### Warstwa 1: Nuitka Commercial
* **Mechanizm:** Konwertuje kod źródłowy Pythona bezpośrednio na zoptymalizowany kod C/C++, który jest następnie kompilowany do natywnego pliku wykonywalnego Windows (.exe).
* **Korzyść:** Całkowicie eliminuje bytecode Pythona (.pyc), przez co narzędzia takie jak uncompyle6 czy pyinstxtractor stają się bezużyteczne. Inżynieria wsteczna logiki staje się tak samo trudna jak w przypadku standardowych binariów C++.

### Warstwa 2: Wirtualizacja Themida (regiony `marker.start()/end()`)
* **Mechanizm:** To **funkcja Themidy**, nie Nuitki. Build nie używa żadnej „Nuitka VM”. Themida przekształca w bytecode swojej maszyny wirtualnej **wyłącznie oznaczone bloki kodu hosta** — regiony `marker.start()/end()` zaznaczone przez plugin `vm_marker_plugin.py` (`--user-plugin=…`, rodzina VM `VM_FISH_WHITE`, zob. `build-nuitka-comm-themida.ps1`); obecnie są to m.in. `app/frontend/compass_pk.py` i `disso_fitting.py`.
* **Zasięg i ograniczenie:** Wirtualizacja nie obejmuje całego kodu ani wszystkich stałych — tylko oznaczone regiony. Dodatkowo szyfrowanie stałych Nuitki (`--enable-plugin=data-hiding`) jest **obecnie wyłączone** (do przywrócenia przed produkcją — zob. [`themida_nuitka_hardening.md`](themida_nuitka_hardening.md)). `--themida-encrypt-strings` szyfruje stringi w pliku, ale dekoduje je w RAM, więc **zrzut pamięci może ujawnić część stałych** — nie należy zakładać bezwarunkowej odporności. Sekret `admin_pin` **nie znajduje się w binarce hosta** — żyje na donglu — więc jego „ukrycie” w hoście nie jest tu czynnikiem.

### Warstwa 3: Themida
* **Mechanizm:** Komercyjny system ochrony oprogramowania, który opakowuje skompilowaną binarkę Nuitki.
* **Korzyść:** 
  - **Anti-Debugger:** własny silnik Themidy wykrywa debugery i wywołuje awarię. **Uwaga:** plugin anti-debugger **Nuitki** jest w buildzie produkcyjnym **celowo pominięty** (kolizje z Windows 11 VBS/Hyper-V — zob. `compilation.md`).
  - **Anti-Dump:** Uniemożliwia zrzucenie rozpakowanego pliku wykonywalnego z RAM.
  - **Anti-VM/Emulation:** Themida potrafi blokować uruchamianie w VM/sandboksach, **ale w buildzie produkcyjnym jest to WYŁĄCZONE** — `--themida-sandbox-monitors` celowo pominięte, aby aplikacja działała pod Windows 11 VBS/Hyper-V (`compilation.md`). W produkcji Anti-VM **nie jest aktywne**.
  - **Wirtualizacja kodu:** Przekształca fragmenty natywnego kodu asemblera x86/x64 w nierozpoznawalny, własnościowy bytecode maszyny wirtualnej.

## 3. Synergia zabezpieczeń
Sprzętowe zabezpieczenia dongla są tylko tak silne, jak komunikująca się z nim aplikacja hosta. Połączenie Nuitka Commercial i Themidy (opakowanie + wirtualizacja oznaczonych regionów) sprawia, że koszt i czas potrzebny na inżynierię wsteczną hosta w Pythonie przewyższają wartość samego oprogramowania, co spełnia wymaganie, by kodu i funkcji **NIE DAŁO SIĘ UKRAŚĆ / PODEJRZEĆ**.
