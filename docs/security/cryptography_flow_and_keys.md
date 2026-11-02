# Przepływ kryptografii i architektura kluczy (wariant B+ ECDHE z Root CA)

Ten dokument opisuje przepływ informacji, rolę oraz miejsce przechowywania każdego elementu wykorzystywanego w procesie kryptograficznym chroniącym aplikację Compass i sprzętowy dongle KeyFirmware.

## 1. Lista wszystkich używanych kluczy

Poniższa tabela zbiera wszystkie klucze kryptograficzne używane w systemie:

| Nazwa klucza | Gdzie jest generowany? | Gdzie i jak jest przechowywany? | Do czego służy? | Poufność |
|---|---|---|---|---|
| **Klucz prywatny Root CA** | Skrypt narzędziowy na odizolowanym firmowym komputerze w fabryce. | Zabezpieczony plik (np. .pem z hasłem) offline. **Nigdy** nie trafia do klienta. | Podpisywanie publicznych certyfikatów tożsamości nowo wyprodukowanych dongli. (Provisioning). | **KRYTYCZNA** |
| **Klucz publiczny Root CA** | Pochodny od klucza prywatnego Root CA. | Zapisany na stałe (hardcoded) bezpośrednio w kodzie aplikacji klienckiej Compass. | Weryfikacja autentyczności (sprawdzanie podpisu) podłączonego dongla. PC sprawdza, czy certyfikat dongla pochodzi z Twojej fabryki. | Publiczna |
| **PUF Root Key (RK)** | Krzem EFR32MG24 (automatycznie przy starcie, fizyka pamięci SRAM). | Istnieje wyłącznie w ulotnych komórkach sprzętowych i jest ukryty przed głównym procesorem Cortex-M33. Znika po wyłączeniu zasilania. | Używany przez wbudowany sprzętowy silnik bezpieczeństwa (HSE) do opakowywania (szyfrowania) innych kluczy przechowywanych w pamięci Flash. | **KRYTYCZNA** |
| **Klucz prywatny tożsamości (urządzenie)** | Wewnątrz procesora kryptograficznego EFR32 (podczas provisioningu). | Przechowywany w pamięci Flash (NVM3), ale opakowany (zaszyfrowany) kluczem PUF. Nikt (nawet Twój kod w C) nie ma dostępu do jego postaci jawnej. | Tożsamość urządzenia. Używany WYŁĄCZNIE do podpisywania klucza efemerycznego przy podłączeniu USB, co dowodzi, że jest to autentyczny dongle. | **KRYTYCZNA** |
| **Klucz publiczny tożsamości (urządzenie)** | Pochodny od powyższego klucza prywatnego tożsamości podczas provisioningu. | Część certyfikatu urządzenia przechowywanego w postaci jawnej w pamięci Flash NVM3 dongla. Wysyłany do PC przy starcie. | Weryfikowany przez PC, poświadcza powiązanie fizycznego urządzenia z fabryką. | Publiczna |
| **Klucz efemeryczny PC (ECDHE)** | Proces Pythona (Compass) na komputerze klienta, przy każdym połączeniu. | Pamięć RAM aplikacji. Niszczony po wyprowadzeniu klucza sesji. | Jedna połowa układanki Diffiego-Hellmana służącej do wyprowadzenia klucza sesji. Zmienia się po rozłączeniu/wymuszonej rotacji. | Chroniona (PFS) |
| **Klucz efemeryczny urządzenia (ECDHE)** | Mikrokontroler EFR32MG24, przy każdym połączeniu. | Pamięć RAM silnika kryptograficznego. Niszczony po wyprowadzeniu klucza sesji. | Druga połowa układanki Diffiego-Hellmana. | Chroniona (PFS) |
| **Klucz sesji (AES-256-GCM)** | Wynik HKDF na obu urządzeniach (PC i dongle) na podstawie wymiany kluczy efemerycznych. | Pamięć RAM PC i ulotne sloty koprocesora w EFR32. Całkowicie niszczony po rotacji klucza (np. co minutę) lub odłączeniu USB. | Właściwe „mięso”. Tym kluczem szyfrujemy fizyczne dane przepływające przez port COM. Rotacja chroni przed zrzutami pamięci RAM z PC. | **WYSOKA** |

---

## 2. Diagramy przepływu

### Proces A: Provisioning (produkcja fabryczna)
Ten proces wykonujesz przy swoim biurku po przylutowaniu płytki, używając skryptów KeySec.

`mermaid
sequenceDiagram
    participant Factory (KeySec)
    participant EFR32 (KeyFirmware)
    participant HSE (Hardware Security Engine)

    Note over Factory (KeySec): Przechowuje „klucz prywatny Root CA” w sejfie offline
    Factory (KeySec)->>EFR32 (KeyFirmware): CMD_PROVISION_IDENTITY
    EFR32 (KeyFirmware)->>HSE (Hardware Security Engine): Generuje parę kluczy (tożsamości)
    HSE (Hardware Security Engine)-->>EFR32 (KeyFirmware): Zwraca klucz publiczny, ukrywa prywatny (PUF)
    EFR32 (KeyFirmware)-->>Factory (KeySec): Klucz publiczny tożsamości
    Note over Factory (KeySec): Tworzenie certyfikatu:<br>1. Tworzy payload: „klucz publiczny EFR32”<br>2. Podpisuje payload kluczem prywatnym Root CA
    Factory (KeySec)->>EFR32 (KeyFirmware): CMD_SAVE_CERTIFICATE (certyfikat urządzenia)
    EFR32 (KeyFirmware)->>EFR32 (KeyFirmware): Zapisuje certyfikat w NVM3
    Note over EFR32 (KeyFirmware), Factory (KeySec): PROCES ZAKOŃCZONY - URZĄDZENIE GOTOWE DO WYSYŁKI
`

### Proces B: Handshake i ochrona (u klienta)
Ten proces uruchamia się natychmiast za każdym razem, gdy oprogramowanie klienckie (Compass) próbuje komunikować się z donglem.

`mermaid
sequenceDiagram
    participant Compass (PC Client)
    participant EFR32 (PUF Dongle)

    Note over Compass (PC Client): Przechowuje zapisany na stałe klucz publiczny Root CA
    Compass (PC Client)->>EFR32 (PUF Dongle): CMD_HELLO
    EFR32 (PUF Dongle)-->>Compass (PC Client): Wysyła swój certyfikat urządzenia (z NVM3)
    Note over Compass (PC Client): Weryfikuje certyfikat kluczem publicznym Root CA.<br>Sprawdza, czy dongle nie jest podróbką.
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): --- START WYMIANY ECDHE ---
    Compass (PC Client)->>Compass (PC Client): Generuje PC_Ephemeral_Key
    EFR32 (PUF Dongle)->>EFR32 (PUF Dongle): Generuje Device_Ephemeral_Key
    
    Compass (PC Client)->>EFR32 (PUF Dongle): PC_Ephemeral_Pub_Key
    Note over EFR32 (PUF Dongle): Sprzęt podpisuje (ECDSA)<br>swój klucz efemeryczny kluczem prywatnym tożsamości (z PUF)
    EFR32 (PUF Dongle)-->>Compass (PC Client): Device_Ephemeral_Pub_Key + SIGNATURE
    
    Note over Compass (PC Client): Weryfikuje SIGNATURE kluczem publicznym z certyfikatu dongla.<br>Zabezpiecza przed atakiem Man-in-the-Middle!
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): Obie strony obliczają Shared Secret = f(My_Priv, Their_Pub)<br>Z niego wyprowadzają docelowy Session_Key (HKDF)
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): --- KOMUNIKACJA SZYFROWANA ---
    Compass (PC Client)->>EFR32 (PUF Dongle): GCM_ENCRYPT(AES_Session_Key, Counter=1, Data="Check status")
    EFR32 (PUF Dongle)-->>Compass (PC Client): GCM_ENCRYPT(AES_Session_Key, Counter=2, Data="OK")
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): (Po 1 minucie) - REKEYING
    Compass (PC Client)->>EFR32 (PUF Dongle): CMD_REKEY (bez zrywania sesji)
    Note over Compass (PC Client), EFR32 (PUF Dongle): Zniszczenie AES_Session_Key, wygenerowanie nowego.
`
