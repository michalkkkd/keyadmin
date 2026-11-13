# Provisioning dongla: narzędzia budowania i wgrywania

> **Kanon narzędzi build/flash.** To jedyne miejsce opisujące skrypty `flashbat/` i pipeline `provision_dongle.py`. Cykl życia **kluczy** podczas provisioningu (co powstaje, gdzie leży) — [`cryptography-and-keys.md`](cryptography-and-keys.md). Blokada SWD — [`secure_debug_lock.md`](secure_debug_lock.md).

Budowanie, wgrywanie (flashowanie) i fabryczny provisioning dongla KeySec (Seeed Studio XIAO MG24, Silicon Labs EFR32MG24).
Skrypty budowania i wgrywania znajdują się w `KeyFirmware/flashbat/`; pipeline provisioningu znajduje się w `KeySec/keyadmin/scripts/provision_dongle.py`.

---

## Główne skrypty robocze (`KeyFirmware/flashbat/`)

### `compile.bat`
Kompiluje oba cele firmware'u TrustZone (`keyfirmware.hex` i `keyfirmware_prov.hex`) za pomocą CMake i Ninja.
Automatycznie scala binaria części secure i non-secure w jednolite pliki HEX gotowe do wgrania.

### `flash.bat`
Niskopoziomowe narzędzie do wgrywania, które zapisuje dowolny obraz `.hex` do docelowego MCU przez pyOCD po SWD.
Wywołane bez argumentów domyślnie wgrywa obraz produkcyjny (`keyfirmware.hex`).

### `set_factory_mode.bat`
Wgrywa fabryczny firmware provisioningowy (`keyfirmware_prov.hex`), aby przełączyć dongla w niezapieczętowany tryb administracyjny.
W tym trybie urządzenie przyjmuje przez port szeregowy polecenia administracyjne służące do wprowadzenia kluczy kryptograficznych, timestampów i licencji.

### `set_production_mode.bat`
Wgrywa finalny firmware produkcyjny (`keyfirmware.hex`), aby zapieczętować dongla przed dystrybucją do klientów.
W tym trybie provisioning administracyjny jest trwale zablokowany i akceptowane są tylko zaszyfrowane zapytania aplikacji.

### Provisioning fabryczny (nie tutaj)
Pełny pipeline produkcyjny znajduje się w KeySec: `python KeySec/keyadmin/scripts/provision_dongle.py 365 3` — **domyślnie pieczętuje** (Secure Debug Lock + OTP tamper); `--no-lock` to pomija (tryb deweloperski). Dostępny także w menu konsoli administracyjnej, sekcja *FACTORY*. Najpierw uruchom go z `--check`: to wstępna kontrola tylko do odczytu (skrypty, obrazy, para Root CA, sonda pyOCD, wolny port COM, SWD niezablokowane, zgodność Command Key z nagłówkiem), która niczego nie zmienia.
Sam niczego nie wgrywa: wywołuje `compile.bat`, `set_factory_mode.bat` i `set_production_mode.bat` z tego folderu, więc te skrypty pozostają jedynym źródłem budowania i wgrywania obrazów firmware'u.

---

## Secure Debug Lock (blokada SWD) — wpływ na build/flash

Pełny opis blokady, kluczy i trybów: [`secure_debug_lock.md`](secure_debug_lock.md). Pieczętowanie jest domyślnym krokiem 6 provisioningu (`provision_dongle.py`, pomijane przez `--no-lock`).

Tu tylko konsekwencja dla narzędzi z `flashbat/`: **po zablokowaniu** `flash.bat`, `set_factory_mode.bat` i `set_production_mode.bat` działają wyłącznie bezpośrednio po odblokowaniu (`secure_debug_lock.py unlock`), bo reset na końcu wgrywania ponownie blokuje port. Kasowanie urządzenia (device erase) pozostaje dostępne zawsze.

---

## Wewnętrzne narzędzia pomocnicze i silniki (`KeyFirmware/flashbat/`)

### `get_python.bat`
Wspólne narzędzie, które wyszukuje w systemie prawidłową instalację Pythona 3 i eksportuje `PYTHON_EXE`.
Pomija puste zaślepki ze Sklepu Windows i weryfikuje interpreter, dzięki czemu wszystkie skrypty wsadowe działają niezawodnie na dowolnej maszynie deweloperskiej.

### `xiao_mg24_flash.py`
Wieloplatformowy silnik w Pythonie, który zarządza uruchamianiem pyOCD, automatycznym sprawdzaniem zależności pakietów i wgrywaniem przez SWD.
Wywoływany pod spodem przez `flash.bat`, `set_factory_mode.bat` i `set_production_mode.bat`.

### `merge_hex.py`
Skrypt w Pythonie uruchamiany po zbudowaniu, który scala pliki HEX części Secure i Non-Secure ARM TrustZone za pomocą biblioteki `intelhex`.
Generuje monolityczne pliki hex zapisywane w `cmake_gcc/build/base/`.

### `SiliconLabs.GeckoPlatform_EFR32MG24_DFP.2025.6.0.pack`
CMSIS Device Family Pack dostarczający algorytmy programowania pamięci flash i definicje rejestrów dla EFR32MG24.
Pozwala pyOCD programować układ bez konieczności instalowania pełnego Simplicity Studio.


