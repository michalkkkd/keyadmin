# Mechanizm szyfrowania komunikacji

## 1. Przegląd
Kanał komunikacji między aplikacją Python na Windows (host) a donglem USB działa przez wirtualny port szeregowy (VCOM/UART). Ponieważ tę magistralę można podsłuchiwać programowymi snifferami USB (np. Wireshark lub Device Monitoring Studio), payloady RPC TinyFrame muszą być silnie zaszyfrowane.

## 2. Projekt i implementacja (faza 2/3)
* **Protokół bazowy:** TinyFrame pełni rolę binarnej warstwy transportowej, zapewniając integralność ramek (CRC16/CRC32) i routing.
* **Payload kryptograficzny:** Wewnątrz payloadu danych TinyFrame wszystkie parametry i odpowiedzi będą szyfrowane.
* **Proponowane algorytmy:**
  - **Wymiana kluczy:** ECDH (Elliptic-Curve Diffie-Hellman, czyli Diffie-Hellman na krzywych eliptycznych) wykonywany podczas początkowego handshake'u w celu ustalenia wspólnego klucza sesji, co zapobiega atakom typu replay i podsłuchowi.
  - **Szyfrowanie symetryczne:** AES-256-GCM lub ChaCha20-Poly1305. Algorytmy te zapewniają uwierzytelnione szyfrowanie z danymi powiązanymi (Authenticated Encryption with Associated Data, AEAD), gwarantując zarówno poufność, jak i integralność.
* **Akceleracja sprzętowa:** EFR32MG24 ma zintegrowany silnik kryptograficzny (Secure Vault), który zostanie wykorzystany do wykonywania operacji AES bez obciążania CPU i z bardzo wysoką odpornością na ataki side-channel (ataki kanałem bocznym).

## 3. Ograniczanie zagrożeń
* **Ataki typu replay:** Handshake'i będą zawierać nonce lub licznik monotoniczny, aby przechwyconego polecenia „Calculate Algorithm” nie dało się wysłać ponownie.
* **Man-in-the-Middle (MitM):** Początkowe klucze publiczne będą wgrane z góry (pre-provisioning) lub podpisane, aby host miał pewność, że komunikuje się z oryginalnym donglem, a dongle - z oryginalną aplikacją hosta.
