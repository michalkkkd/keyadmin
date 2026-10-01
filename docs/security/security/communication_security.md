# Projekt Bezpieczeństwa: Szyfrowanie Komunikacji (Compass ↔ KeyFirmware)

Ten dokument opisuje mechanizmy szyfrowania komunikacji pomiędzy aplikacją PC (`compass`) a kluczem sprzętowym na mikrokontrolerze (Seeed XIAO MG24 - EFR32MG24).

## 1. Środowisko i Model Zagrożeń (Threat Model)

Projekt zakłada rygorystyczne i specyficzne warunki wdrożeniowe, które całkowicie dyktują dobór kryptografii:
*   **Środowisko Air-gapped:** Komputery Windows uruchamiające aplikację nie mają dostępu do Internetu. Odrzuca to możliwość stosowania serwerów autoryzacyjnych w chmurze (Cloud Licensing/KMS).
*   **Brak przypisania do maszyny (No Machine-Binding):** Z przyczyn biznesowych, firma kupująca licencję ma prawo instalować/przenosić aplikację na dowolne komputery (zmieniać stacje robocze). Zabezpieczenie nie może opierać się na cechach sprzętowych płyty głównej PC.
*   **Profil Przeciwnika (Wynajęci Specjaliści RE):** Głównym wektorem ataku jest sytuacja, w której nieuczciwy klient zatrudnia ekspertów od inżynierii wstecznej (Reverse Engineering). Ich celem jest przełamanie zabezpieczeń lub "sklonowanie/zemulowanie" klucza sprzętowego w oprogramowaniu, aby móc używać aplikacji na nieskończonej liczbie stanowisk bez płacenia za kolejne licencje (obchodząc ograniczenia czasowe i limitu użytkowników narzucane przez klucz).

## 2. Możliwości Mikrokontrolera EFR32MG24 (Secure Vault High & PUF)

Dokumentacja układów EFR32MG24 potwierdza obecność technologii **Secure Vault High**, z mechanizmem **PUF (Physically Unclonable Function)**:
1. **Unikalny Root Key (RK):** Przy każdym uruchomieniu zasilania mikrokontroler sprzętowo "odbudowuje" klucz główny na podstawie mikroskopijnych różnic produkcyjnych SRAM.
2. **Key Wrapping:** Klucze prywatne są szyfrowane przez RK.
3. **Zabezpieczenie przed kradzieżą (Non-exportable keys):** Zaszyfrowany w MCU klucz jest bezużyteczny nawet przy fizycznym zrzucie pamięci Flash przez atakującego. Odporność na ataki DPA (Differential Power Analysis).

## 3. Zestawienie Najlepszych Bibliotek (TOP 5)

Z uwagi na model zagrożeń i odcięcie od internetu, stosujemy sprawdzone, wbudowane rozwiązania.

| L.p. | Nazwa Biblioteki | Środowisko | Rekomendacja |
|---|---|---|---|
| 1. | **PSA Crypto API (mbedTLS)** | C (MCU) | **Główny wybór dla MCU** (Wspiera PUF i HSE, natywna SiLabs). |
| 2. | **cryptography** | Python (PC) | **Główny wybór dla PC** (Dobrze współpracuje z Nuitka, bogate wsparcie asymetryczne). |
| 3. | **PyCryptodome** | Python (PC) | Alternatywa dla PC. |
| 4. | **PyNaCl (libsodium)**| Python (PC) | Świetna do Ed25519, ale wymagałaby portowania na EFR32. |
| 5. | **Tink** | Py/C++ | Bezpieczna, ale zbyt ciężka do integracji z offline exe. |

---

## 4. Wybór Architektury i Wariantów (Wpływ Modelu Zagrożeń)

W świetle faktu, że bronimy się przed **wynajętymi specjalistami mającymi za zadanie napisać emulator klucza sprzętowego**, całkowicie zmienia to rekomendowane podejście do szyfrowania.

### Dlaczego klasyczna kryptografia symetryczna (Wariant C - PSK) zawodzi?
W wariancie symetrycznym, PC oraz Dongle muszą dzielić ten sam sekret (Master Key), a my nie możemy go przypisać do maszyny (Machine Binding) ani pobrać z chmury. Oznacza to, że klucz Master musiałby być przenoszony w pliku licencji obok EXE lub wkompilowany Themidą. Specjalista od inżynierii wstecznej, monitorując pamięć RAM (memory dump) procesu Pythona, wyciągnie ten klucz. 
**Krytyczny błąd:** Mając klucz symetryczny, specjalista tworzy wirtualny sterownik portu COM (software dongle). Ponieważ obie strony symetryczne "wiedzą to samo", oprogramowanie uwierzytelni fałszywego dongla i uruchomi nielimitowaną produkcję.

### Rekomendacja: Asymetryczne uwierzytelnianie i kluczowanie (Wariant ECDH / ECDSA)
Aby pokonać ten wektor ataku, musimy wykorzystać fakt, że PUF na mikrokontrolerze jest nie do złamania. 

**Proponowana Architektura Docelowa (Wariant B+):**
1. **Fabryka (Provisioning):** Każdy Dongle generuje własną parę kluczy asymetrycznych (Klucz Publiczny oraz Prywatny chroniony wewnątrz PUF). Aplikacja PC nie posiada *żadnego* klucza prywatnego ani symetrycznego sekreta – posiada **jedynie wbudowany Klucz Publiczny** urządzenia (lub certyfikat Twojego Root CA).
2. **Autoryzacja (Challenge-Response):** Po uruchomieniu, `compass.exe` generuje losowy ciąg znaków (Challenge) i prosi urządzenie o jego kryptograficzny podpis. Urządzenie podpisuje go swoim uwięzionym w PUF kluczem prywatnym (ECDSA). Aplikacja weryfikuje podpis publicznym kluczem.
3. **Ustalenie sesji (ECDH):** Następnie z użyciem krzywych eliptycznych (ECDH) ustanawiany jest unikalny klucz sesyjny (AES-256-GCM) dla szyfrowania całego ruchu. 

**Dlaczego to unieszkodliwia hakerów?**
Nawet jeśli wynajęty specjalista całkowicie złamie obfuskację Themidy i zrzuci RAM Pythona, znajdzie tam tylko **Klucz Publiczny**. Mając klucz publiczny, **nie da się napisać emulatora sprzętu** (nie podrobi on podpisu ECDSA). Specjalista musiałby ukraść klucz prywatny z samego Dongla, co ze względu na technologię Secure Vault High i PUF wiąże się z atakami na poziomie mikroskopu elektronowego (koszty dziesiątek tysięcy dolarów, nieopłacalne dla oszczędności na licencji).

*(Zabezpieczenie przed "patchowaniem" pliku EXE, by ignorował sprawdzanie Dongla, to zadanie dla Themidy oraz integralnego powiązania samej logiki biznesowej z Donglem – np. trzymania krytycznych wzorów/wag matematycznych tylko na zaszyfrowanym Flaszu MCU, które urządzenie wydaje po kropli przez zaszyfrowany kanał)*.

## 5. Priorytet: Maksymalne utrudnienie podsłuchu USB (Klucze Efemeryczne)

Skoro nadrzędnym celem jest zabezpieczenie *samego kanału komunikacyjnego* (kabla USB) przed deszyfracją i podsłuchem (np. analizatorami portu COM), architektura Wariantu B+ musi zostać rozszerzona do standardu przypominającego TLS 1.3, czyli wykorzystać **ECDHE (Elliptic Curve Diffie-Hellman Ephemeral)**.

**Mechanika działania i utrudnienia ataków:**
1. **Klucze Tymczasowe (Ephemeral):** Przy *każdym* podłączeniu kabla USB, zarówno Dongle jak i `compass.exe` na PC generują w locie zupełnie nowe, jednorazowe pary kluczy tylko na potrzeby tej konkretnej sesji (klucze efemeryczne).
2. **Uwierzytelnienie wymiany (Ochrona przed MitM):** Aby udaremnić podstawienie własnego klucza w locie przez aktywnego hakera, Dongle *podpisuje* swój efemeryczny klucz publiczny stałym, fabrycznym kluczem prywatnym uwięzionym w PUF.
3. **Poufność Uprzednia (Perfect Forward Secrecy - PFS):** Haker nasłuchujący komunikacji z USB rejestruje tylko zbitki losowych danych i wymieniane klucze publiczne. Nawet jeśli ten sam haker po 5 latach ukradnie *z pamięci PC lub Dongla* główne, stałe klucze tożsamości, **nie odszyfruje żadnej historycznej rozmowy**. Każda sesja była bowiem zaszyfrowana tymczasowym kluczem (Session Key), który bezpowrotnie zniknął z pamięci RAM obu urządzeń sekundę po odłączeniu kabla.
4. **Rotacja w trakcie trwania (Rekeying):** By uderzyć w specjalistów zrzucających pamięć RAM PC podczas działania programu (gdy klucz sesyjny akurat w niej żyje), klucz ten jest automatycznie podmieniany ("ratcheting") po określonym czasie, drastycznie zmniejszając użyteczność takiego ataku. Zanim haker zlokalizuje klucz w pamięci i spróbuje go użyć do dekodowania strumienia USB, sprzęt zacznie posługiwać się już nowym kluczem.
