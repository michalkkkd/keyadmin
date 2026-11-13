# Pierwotne wymagania (projekt Compass)

Oto dosłowne wymagania, od których zaczęliśmy budowę tego systemu:

> Urządzenie USB jest potrzebne do zabezpieczenia aplikacji Windows (exe).
> a) Mamy 5 funkcji, obecnie napisanych w C++, które wykonują proste, ale tajne obliczenia matematyczne.
> b) Każda z tych funkcji ma około 100 linii kodu, więc łącznie po kompilacji to maksymalnie około 20 KB. Są to funkcje mało wymagające obliczeniowo.
> c) Chcę mieć możliwość wykonania z poziomu Pythona (aplikacja Windows) następujących operacji:
> - wywołać wybraną funkcję na kluczu (oczywiście przez szyfrowaną komunikację: program windows -> urządzenie usb), aby otrzymać wyniki obliczeń.
> - sprawdzić w 100% prawdziwą bieżącą datę i godzinę, pobierając ją z urządzenia USB.
> d) Wymagania:
> - Nie muszę niczego zdalnie aktualizować na kluczu.
> - Chcę, żeby po zapisaniu funkcji i danych NIE DAŁO SIĘ ICH UKRAŚĆ / PODEJRZEĆ.
> - Chciałbym, żeby te funkcje wykonywały się w jakimś odizolowanym środowisku, znowu po to, żeby NIE DAŁO SIĘ ICH UKRAŚĆ / PODEJRZEĆ.
> - Bateria RTC musi być fizyczna i bezpieczna.
> - Chciałbym, żeby nie dało się po prostu sklonować zawartości urządzenia usb i przenieść jej na inne urządzenie usb.
> - Chciałbym, żeby klucz blokował się lub czyścił swoją pamięć w sytuacji takiej jak odłączenie baterii (tampering, czyli próba ingerencji).
> - Chciałbym, żeby było jak najwięcej mechanizmów anti-tampering, a kod był w 99.9% bezpieczny.
> - Nie chcę pisać od zera architektury bezpieczeństwa dla kodu urządzenia USB. Chciałbym, żeby większość zabezpieczeń działała Out of the Box (gotowa od razu), a ja tylko przenoszę swój skompilowany kod, wypalam w pamięci to, co trzeba, itd.
> - Urządzenie musi dać się zamontować w obudowie podobnej do pendrive'a (więc maksymalny rozmiar to format feather).
> - Admin musi móc ustawić datę wygaśnięcia licencji, a aplikacja Python może sprawdzić, czy licencja jest nadal aktywna.
> - Admin musi móc ustawić maksymalną liczbę użytkowników aplikacji, a aplikacja Python może odczytać, ilu użytkowników jest przypisanych.
> - Chcę, żeby urządzenie było dostępne do kupienia w Polsce, ogólnie popularne (łatwo dostępne) i nadal produkowane.
