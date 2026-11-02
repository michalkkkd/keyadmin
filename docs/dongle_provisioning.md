# Provisioning dongla, skrypty budowania i wgrywania

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
Pełny pipeline produkcyjny znajduje się w KeySec: `python KeySec/keyadmin/scripts/provision_dongle.py 365 3 [--lock]` (dostępny także w menu konsoli administracyjnej, sekcja *FACTORY*). Najpierw uruchom go z `--check`: to wstępna kontrola tylko do odczytu (skrypty, obrazy, para Root CA, sonda pyOCD, wolny port COM, SWD niezablokowane, zgodność Command Key z nagłówkiem), która niczego nie zmienia.
Sam niczego nie wgrywa: wywołuje `compile.bat`, `set_factory_mode.bat` i `set_production_mode.bat` z tego folderu, więc te skrypty pozostają jedynym źródłem budowania i wgrywania obrazów firmware'u.

---

## Secure Debug Lock (blokada SWD)

Pełny opis: [security/secure_debug_lock.md](security/secure_debug_lock.md).

Firmware produkcyjny blokuje własny port SWD za pomocą Secure Engine (bez potrzeby użycia J-Linka), przez nieszyfrowane RPC `0x60-0x63`.
Strona hosta: `KeySec/keyadmin/scripts/secure_debug_lock.py` oraz sekcja menu konsoli administracyjnej *SECURE DEBUG LOCK*.

1. **Raz na produkt (klucz wspólny dla całej produkcji):** `python KeySec/keyadmin/scripts/generate_debug_command_key.py` tworzy `KeySec/keyadmin/keys/debug_command_key.pem` (obok Root CA) i zapisuje klucz publiczny do `src/secure/debug_command_pubkey.h`. Przebuduj za pomocą `compile.bat`. Obecny klucz jest kluczem deweloperskim; przed właściwą produkcją wygeneruj nowe klucze.
2. **Ochrona dongli deweloperskich:** `python KeySec/keyadmin/scripts/secure_debug_lock.py protect` dodaje podłączony dongle do `KeySec/keyadmin/keys/secure_debug/protected_devices.json`. Każda ścieżka blokowania (CLI, menu administracyjne, `provision_dongle.py ... --lock`) odrzuca chronione numery seryjne, zanim cokolwiek zostanie wysłane do dongla.
3. **Blokada:** `python KeySec/keyadmin/scripts/provision_dongle.py 365 3 --lock` lub `python KeySec/keyadmin/scripts/secure_debug_lock.py lock`. Zapisuje publiczny Command Key do OTP (nieodwracalnie), włącza secure debug i nakłada blokadę. Kasowanie urządzenia (device erase) pozostaje dostępne.
4. **Odblokowanie (do następnego resetu):** `python KeySec/keyadmin/scripts/secure_debug_lock.py unlock`, a następnie odczyt pamięci przez pyOCD w trybie attach (`-M attach`) bez resetowania dongla.

Po zablokowaniu `flash.bat`, `set_factory_mode.bat` i `set_production_mode.bat` działają tylko bezpośrednio po odblokowaniu (reset na końcu wgrywania ponownie blokuje port).
Dane poszczególnych dongli znajdują się w `KeySec/keyadmin/keys/secure_debug/devices/device_<SE serial>/` (`device.json`, certyfikat dostępu, foldery `challenge_<hex>/`).

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


