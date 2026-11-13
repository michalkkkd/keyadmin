# Mechanizm szyfrowania komunikacji

## 1. Przegląd
Kanał komunikacji między aplikacją Python na Windows (host) a donglem USB działa przez wirtualny port szeregowy (VCOM/UART). Ponieważ tę magistralę można podsłuchiwać programowymi snifferami USB (np. Wireshark lub Device Monitoring Studio), payloady RPC TinyFrame muszą być silnie zaszyfrowane.

## 2. Projekt i implementacja (wdrożone)
* **Protokół bazowy:** TinyFrame pełni rolę binarnej warstwy transportowej, zapewniając integralność ramek (CRC32, `TF_CKSUM_CRC32`) i routing.
* **Payload kryptograficzny:** Wewnątrz payloadu danych TinyFrame wszystkie parametry i odpowiedzi są szyfrowane (po nawiązaniu sesji) AES-256-GCM z AAD.
* **Algorytmy (wdrożone):**
  - **Wymiana kluczy:** ECDH (Elliptic-Curve Diffie-Hellman, czyli Diffie-Hellman na krzywych eliptycznych) wykonywany podczas początkowego handshake'u w celu ustalenia wspólnego klucza sesji, co zapobiega **podsłuchowi** (poufność). Ataki typu replay blokuje osobno **monotoniczny licznik** w nonce (patrz §3).
  - **Szyfrowanie symetryczne:** **AES-256-GCM** (ChaCha20-Poly1305 **nieużywane** w firmware). Zapewnia uwierzytelnione szyfrowanie z danymi powiązanymi (Authenticated Encryption with Associated Data, AEAD), gwarantując zarówno poufność, jak i integralność.
* **Akceleracja sprzętowa:** EFR32MG24 ma zintegrowany silnik kryptograficzny (Secure Vault), wykorzystywany do operacji AES bez obciążania CPU i z bardzo wysoką odpornością na ataki side-channel (ataki kanałem bocznym).

## 3. Ograniczanie zagrożeń
* **Ataki typu replay:** Każdy szyfrowany pakiet niesie **monotoniczny licznik** (nonce = licznik LE | bajt kierunku | zera), więc przechwyconego polecenia „Calculate Algorithm” nie da się wysłać ponownie (wdrożone).
* **Man-in-the-Middle (MitM):** Tożsamość dongla jest **podpisana przez Root CA** (certyfikat w NVM3, zweryfikowany przy handshake), a host uwierzytelnia się kluczem hosta — host ma pewność, że rozmawia z oryginalnym donglem, a dongle z oryginalną aplikacją (wdrożone).
