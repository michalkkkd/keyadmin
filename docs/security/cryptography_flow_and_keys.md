# Architektura Kryptograficzna (Wariant B+ ECDHE z Root CA)

Ten dokument precyzuje przepływ informacji, rolę oraz miejsce przechowywania każdego elementu używanego w procesie kryptograficznym chroniącym aplikację `Compass` oraz układ sprzętowy `KeyFirmware`.

## 1. Wykaz wszystkich używanych kluczy

Poniższa tabela zbiera wszystkie klucze kryptograficzne wykorzystywane w systemie:

| Nazwa Klucza | Gdzie jest generowany? | Gdzie i jak jest przechowywany? | Do czego służy? | Poufność |
|---|---|---|---|---|
| **Root CA Private Key** | Skrypt narzędziowy (np. `KeySec`) na odizolowanym komputerze firmowym w fabryce. | Zabezpieczony plik (np. `.pem` z hasłem) offline. **Nigdy** nie trafia do klienta. | Podpisywanie publicznych certyfikatów tożsamości dla nowo wyprodukowanych Dongli. (Provisioning). | **KRYTYCZNA** |
| **Root CA Public Key** | Wyciągany z Root CA Private Key. | Wkompilowany na stałe (zahardcodowany) w kod aplikacji klienckiej `Compass`. | Weryfikacja autentyczności (podpisu) podłączonego Dongla. PC sprawdza czy certyfikat Dongla pochodzi z Twojej fabryki. | Jawny |
| **PUF Root Key (RK)** | Krzem EFR32MG24 (Automatycznie przy starcie, fizyka układu SRAM). | Znajduje się tylko w lotnych komórkach sprzętowych i jest ukryty przed głównym procesorem Cortex-M33. Znika po wyłączeniu prądu. | Używany przez wbudowany sprzętowy akcelerator (HSE) do szyfrowania (wrapping) innych kluczy trzymanych we Flaszu. | **KRYTYCZNA** |
| **Identity Private Key (Device)** | Wnętrze procesora krypto EFR32 (podczas procesu provisioningu). | Przechowywany we Flaszu (NVM3), ale jest zaszyfrowany (wrapped) kluczem PUF. Nikt (nawet Twój kod C) nie ma do niego dostępu tekstowego. | Tożsamość urządzenia. Używany wyłącznie do podpisywania klucza efemerycznego w trakcie wpinania do USB, by udowodnić, że to oryginalny dongle. | **KRYTYCZNA** |
| **Identity Public Key (Device)** | Wyciągany z powyższego Identity Private Key w trakcie provisioningu. | Część Certyfikatu Urządzenia (Device Certificate) trzymanego jawnie w pamięci Flash NVM3 Dongla. Wysyłany do PC na start. | Weryfikowany przez PC, poświadcza o powiązaniu fizycznego urządzenia z fabryką. | Jawny |
| **PC Ephemeral Key (ECDHE)** | Proces RAM pythona (`Compass`) na komputerze klienta, przy każdym połączeniu. | Pamięć RAM aplikacji. Zniszczony po wyliczeniu klucza sesji. | Połówka zagadki Diffie-Hellman do wyliczenia klucza sesji. Zmienia się po odpięciu/wymuszonej rotacji. | Chroniona (PFS) |
| **Device Ephemeral Key (ECDHE)** | Mikrokontroler EFR32MG24, przy każdym podłączeniu. | Pamięć RAM ukłądu krypto. Zniszczony po wyliczeniu klucza sesji. | Druga połówka zagadki Diffie-Hellman. | Chroniona (PFS) |
| **Session Key (AES-256-GCM)** | Wynik równania (KDF) na obu urządzeniach (PC i Dongle) na podstawie wymiany Efemerycznej. | RAM komputera PC oraz lotne sloty koprocesora w EFR32. Znika całkowicie po rotacji klucza (np. po minucie) lub po wyjęciu kabla USB. | Główne "mięso". Tym kluczem szyfrujemy fizyczne dane lecące przez port COM. Zmiana chroni przed zrzutem pamięci RAM komputera. | **WYSOKA** |

---

## 2. Diagramy Przepływu (Flow)

### Proces A: Provisioning (Produkcja w Fabryce)
Ten proces wykonujesz u siebie przy biurku po zlutowaniu płytki, za pomocą skryptów `KeySec`.

```mermaid
sequenceDiagram
    participant Fabryka (KeySec)
    participant EFR32 (KeyFirmware)
    participant HSE (Hardware Security Engine)

    Note over Fabryka (KeySec): Posiada "Root CA Private Key" w zabezpieczonym sejfie offline
    Fabryka (KeySec)->>EFR32 (KeyFirmware): CMD_PROVISION_IDENTITY
    EFR32 (KeyFirmware)->>HSE (Hardware Security Engine): Generuj parę kluczy (Identity)
    HSE (Hardware Security Engine)-->>EFR32 (KeyFirmware): Zwróć Klucz Publiczny, ukryj Prywatny (PUF)
    EFR32 (KeyFirmware)-->>Fabryka (KeySec): Identity Public Key
    Note over Fabryka (KeySec): Tworzenie Certyfikatu:<br>1. Tworzy payload: "Klucz Publiczny EFR32"<br>2. Podpisuje payload używając Root CA Priv Key
    Fabryka (KeySec)->>EFR32 (KeyFirmware): CMD_SAVE_CERTIFICATE (Device Cert)
    EFR32 (KeyFirmware)->>EFR32 (KeyFirmware): Zapisz Certyfikat w NVM3
    Note over EFR32 (KeyFirmware), Fabryka (KeySec): PROCES ZAKOŃCZONY - URZĄDZENIE GOTOWE DO WYSYŁKI
```

### Proces B: Handshake i Ochrona (U Klienta)
Ten proces uruchamia się natychmiast za każdym razem, gdy oprogramowanie klienckie (`Compass`) próbuje "pogadać" z Donglem.

```mermaid
sequenceDiagram
    participant Compass (Klient PC)
    participant EFR32 (Dongle z PUF)

    Note over Compass (Klient PC): Posiada zahardcodowany Root CA Public Key
    Compass (Klient PC)->>EFR32 (Dongle z PUF): CMD_HELLO (Wyzwanie: nonce 32 bajty)
    EFR32 (Dongle z PUF)-->>Compass (Klient PC): Wysyła swój Device Certificate (z NVM3)
    Note over Compass (Klient PC): Weryfikuje Certyfikat używając Root CA Pub Key.<br>Sprawdza, czy Dongle nie jest podrobiony.
    
    Note over Compass (Klient PC), EFR32 (Dongle z PUF): --- ROZPOCZĘCIE WYMIANY ECDHE ---
    Compass (Klient PC)->>Compass (Klient PC): Generuje PC_Ephemeral_Key
    EFR32 (Dongle z PUF)->>EFR32 (Dongle z PUF): Generuje Device_Ephemeral_Key
    
    Compass (Klient PC)->>EFR32 (Dongle z PUF): PC_Ephemeral_Pub_Key
    Note over EFR32 (Dongle z PUF): Sprzętowo podpisuje (ECDSA)<br>swoją efemerydę z użyciem Identity Private Key (z PUF)
    EFR32 (Dongle z PUF)-->>Compass (Klient PC): Device_Ephemeral_Pub_Key + SIGNATURE
    
    Note over Compass (Klient PC): Weryfikuje SIGNATURE używając Pub Key z Certyfikatu Dongla.<br>Zabezpiecza przed Man-in-the-Middle!
    
    Note over Compass (Klient PC), EFR32 (Dongle z PUF): Obie strony wyliczają Shared Secret = f(My_Priv, Their_Pub)<br>Z niego wyciągają docelowy Session_Key (HKDF)
    
    Note over Compass (Klient PC), EFR32 (Dongle z PUF): --- SZYFROWANA KOMUNIKACJA ---
    Compass (Klient PC)->>EFR32 (Dongle z PUF): GCM_ENCRYPT(AES_Session_Key, Licznik=1, Data="Zwróć status")
    EFR32 (Dongle z PUF)-->>Compass (Klient PC): GCM_ENCRYPT(AES_Session_Key, Licznik=2, Data="OK")
    
    Note over Compass (Klient PC), EFR32 (Dongle z PUF): (Po upływie 1 minuty) - REKEYING
    Compass (Klient PC)->>EFR32 (Dongle z PUF): CMD_REKEY (Bez zrywania sesji)
    Note over Compass (Klient PC), EFR32 (Dongle z PUF): Zniszczenie AES_Session_Key, wygenerowanie nowego.
```
