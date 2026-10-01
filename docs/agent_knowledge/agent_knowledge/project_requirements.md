# Oryginalne Wymagania (Projekt Compass)

Oto doslowne wymagania, od ktorych zaczelismy budowe tego systemu:

> Urzadzenie usb potrzebne jest do ochrony aplikacji na Windows, exe.
> a) Mamy 5 funkcji, obecnie napisanych w c++, ktore realizuje proste ale tajemne obliczenia matematyczne.
> b) Kazda z tych funkcji to okolo 100 linii kodu, wiec lacznie po skompilowaniu okolo 20 KB maksymalnie, sa to malo wymagajace obliczeniowo funkcje
> c) Chce z poziomu pythona (aplikacja windows) :
> - wywolywac wybrana funkcje na kluczu (oczywiscie przez zaszyfrowana komunikacje program windows -> urzadzenie usb) aby dostawac wyniki obliczen
> - moc sprawdzic 100% prawdziwa obecna date i czas, pobierajac ja z urzadzenia USB
> d) Wymagania:
> - nie musze aktualizowac nic na kluczu zdalnie
> - chce aby po zapisaniu przeze mnie funkcji i danych, NIE MOZNA BYLO ICH UKRASC / PODEJRZEC
> - chcialbym aby te funkcje wykonywaly sie w jakims izolowanym srodowisku, aby znowu NIE MOZNA BYLO ICH UKRASC / PODEJRZEC
> - bateria RTC musi byc fizyczna i bezpieczna
> - chcialbym aby nie mozna bylo po prostu sklonowac zawartosci urzadzenia usb i przeniesc na inne urzadzenie usb
> - chcialbym aby w sytuacji np. odlaczenia baterii (tampering), klucz sie blokowal czy czyscil pamiec
> - chcialbym aby bylo jak najwiecej mechanizmow anti tampering i aby kod byl 99.9% bezpieczny
> - nie chce pisac architektury bezpieczenstwa kodu urzadzenia USB od zera, chcialbym ze wiekszosc security byla Out of the Box, a ja tylko przenosze moj kod skompilowany, wypalam co trzeba na pamieci itd.
> - urzadzenie musi byc mozliwe do zamontowania w obudowie ala pendrive USB (czyli rozmiar max feather)
> - chce aby urzadzenie bylo to dostepne do zakupu w Polsce, generalnie popularne (dostepne) i w aktywnej produkcji
