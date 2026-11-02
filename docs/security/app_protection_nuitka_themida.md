# Ochrona głównej aplikacji (Nuitka i Themida)

## 1. Przegląd
Aplikacja hosta dla Windows (Compass) współpracuje z bezpiecznym donglem USB. Jeśli aplikację hosta da się łatwo zdekompilować (np. standardowy bytecode Pythona), atakujący może po prostu wydobyć `admin_pin`, odtworzyć klucze kryptograficzne metodą inżynierii wstecznej albo wyciąć patchem sprawdzanie licencji. Aby temu zapobiec, stosowany jest obowiązkowy, wielowarstwowy proces zaciemniania i wirtualizacji.

## 2. Warstwy ochrony

### Warstwa 1: Nuitka Commercial
* **Mechanizm:** Konwertuje kod źródłowy Pythona bezpośrednio na zoptymalizowany kod C/C++, który jest następnie kompilowany do natywnego pliku wykonywalnego Windows (.exe).
* **Korzyść:** Całkowicie eliminuje bytecode Pythona (.pyc), przez co narzędzia takie jak uncompyle6 czy pyinstxtractor stają się bezużyteczne. Inżynieria wsteczna logiki staje się tak samo trudna jak w przypadku standardowych binariów C++.

### Warstwa 2: Nuitka VM
* **Mechanizm:** Funkcja Nuitka Commercial, która wirtualizuje krytyczne ścieżki wykonania i chroni wrażliwe stałe.
* **Korzyść:** Zaszywa łańcuchy znaków, klucze szyfrujące oraz `admin_pin` w niestandardowym zestawie instrukcji maszyny wirtualnej. Atakujący, którzy uruchomią strings lub narzędzia do zrzutu pamięci, nie znajdą sekretów w postaci jawnego tekstu.

### Warstwa 3: Themida
* **Mechanizm:** Komercyjny system ochrony oprogramowania, który opakowuje skompilowaną binarkę Nuitki.
* **Korzyść:** 
  - **Anti-Debugger:** Wykrywa uruchomienie pod x64dbg, OllyDbg lub GDB i wtedy wywołuje awarię programu.
  - **Anti-Dump:** Uniemożliwia zrzucenie rozpakowanego pliku wykonywalnego z RAM.
  - **Anti-VM/Emulation:** Blokuje uruchamianie w maszynach wirtualnych i sandboksach, często używanych przez osoby zajmujące się inżynierią wsteczną.
  - **Wirtualizacja kodu:** Przekształca fragmenty natywnego kodu asemblera x86/x64 w nierozpoznawalny, własnościowy bytecode maszyny wirtualnej.

## 3. Synergia zabezpieczeń
Sprzętowe zabezpieczenia dongla są tylko tak silne, jak komunikująca się z nim aplikacja hosta. Połączenie Nuitka Commercial, Nuitka VM i Themidy sprawia, że koszt i czas potrzebny na inżynierię wsteczną hosta w Pythonie przewyższają wartość samego oprogramowania, co spełnia wymaganie, by kodu i funkcji **NIE DAŁO SIĘ UKRAŚĆ / PODEJRZEĆ**.
