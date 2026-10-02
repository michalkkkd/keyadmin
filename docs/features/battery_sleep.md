# ZarzÄ…dzanie EnergiÄ… i Wykrywanie USB (Battery Sleep)

## Kontekst Architektoniczny
UkÅ‚ad EFR32MG24 nie posiada wbudowanego sprzÄ™towego kontrolera USB. Na pÅ‚ytkach deweloperskich (np. Seeed XIAO MG24) port USB jest obsÅ‚ugiwany przez koprocesor (SAMD11), ktÃ³ry peÅ‚ni rolÄ™ mostka USB-UART. EFR32 komunikuje siÄ™ z nim wyÅ‚Ä…cznie przez piny `PA08` (TX) i `PA09` (RX). 

PoniewaÅ¼ bateria podtrzymujÄ…ca (np. dla RTC) bÄ™dzie przylutowana na staÅ‚e, ukÅ‚ad musi umieÄ‡ bezbÅ‚Ä™dnie przejÅ›Ä‡ w tryb gÅ‚Ä™bokiego snu (EM2), gdy kabel USB jest odÅ‚Ä…czony (lub aplikacja nieaktywna), aby zminimalizowaÄ‡ drenaÅ¼ baterii. Ze wzglÄ™du na brak bezpoÅ›redniego sprzÄ™towego podÅ‚Ä…czenia pinu VBUS z procesorem, wykrywanie obecnoÅ›ci poÅ‚Ä…czenia zrealizowano **w 100% programowo**, co eliminuje potrzebÄ™ modyfikacji sprzÄ™towych (lutowania dodatkowych rezystorÃ³w na pÅ‚ytce prototypowej).

## Opis RozwiÄ…zania Programowego (Heartbeat + Wake-on-RX)

Mechanizm opiera siÄ™ na dwÃ³ch filarach poÅ‚Ä…czonych ze Å›rodowiskiem Low-Power SDK:

### 1. Zasypianie na podstawie Timeoutu (Heartbeat / Ping-Pong)
Zgodnie z zasadÄ… *Fail Fast*, urzÄ…dzenie musi stale weryfikowaÄ‡, czy aplikacja na komputerze (KeySec) jest aktywna.
* Firmware cyklicznie wysyÅ‚a komunikat na port szeregowy (np. `{"cmd":"ping"}`).
* Oczekuje na natychmiastowÄ… odpowiedÅº od oprogramowania z PC (PONG).
* Brak poprawnej odpowiedzi w wyznaczonym oknie czasowym (timeout) jest rÃ³wnoznaczny z tym, Å¼e kabel zostaÅ‚ odÅ‚Ä…czony lub aplikacja na PC jest wyÅ‚Ä…czona.
* Firmware zdejmuje blokadÄ™ gÅ‚Ä™bokiego snu komendÄ…: `sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1);`, a system operacyjny (Silicon Labs Power Manager) automatycznie usypia procesor do trybu EM2.

### 2. Wybudzanie przerwaniem na linii RX (Wake-on-RX)
Gdy ukÅ‚ad Å›pi w trybie EM2, jego gÅ‚Ã³wny oscylator (zegar wysokiej czÄ™stotliwoÅ›ci) i peryferia UART sÄ… wyÅ‚Ä…czone dla oszczÄ™dzania energii.
* Pin odbiorczy `PA09` (RX) jest skonfigurowany na poziomie sprzÄ™towym jako **asynchroniczne przerwanie GPIO** reagujÄ…ce na zbocze opadajÄ…ce. ModuÅ‚ GPIO jako jeden z nielicznych nasÅ‚uchuje w trybie EM2.
* Aby rozpoczÄ…Ä‡ komunikacjÄ™ z uÅ›pionym urzÄ…dzeniem, aplikacja na komputerze (KeySec) musi wysÅ‚aÄ‡ z wyprzedzeniem tzw. **"Bajt WybudzajÄ…cy" (Dummy Byte)**, np. `0x00`.
* Fizyczna zmiana stanu napiÄ™cia na pinie RX budzi procesor sprzÄ™towo do trybu EM1. Firmware, wybudzony przerwaniem, natychmiast blokuje powrÃ³t do uÅ›pienia (`sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1);`).
* **Uwaga dla warstwy Python:** Pierwszy wysÅ‚any bajt wybudzajÄ…cy ulegnie zniszczeniu, poniewaÅ¼ zegar procesora EFR32 potrzebuje uÅ‚amka sekundy na rozruch. Z tego powodu aplikacja PC zawsze wysyÅ‚a `0x00`, czeka np. 10 milisekund na synchronizacjÄ™ ukÅ‚adu, i dopiero po tym czasie wysyÅ‚a wÅ‚aÅ›ciwÄ… (kryptograficznÄ…) komendÄ™.

---

## Scenariusze UÅ¼ycia (Edge Cases & Fail-Safes)

PoniÅ¼ej opisano zachowanie systemu, opierajÄ…ce siÄ™ na fundamentalnej zasadzie architektonicznej: 
> *System zasypia zawsze przy braku potwierdzonej komunikacji (Timeout), a budzi siÄ™ wyÅ‚Ä…cznie na fizyczny impuls elektryczny (Zbocze OpadajÄ…ce) na linii RX.*

### Scenariusz A: UrzÄ…dzenie odÅ‚Ä…czone âž” Aplikacja startuje âž” UrzÄ…dzenie podÅ‚Ä…czone
* **Stan poczÄ…tkowy:** UrzÄ…dzenie w trybie gÅ‚Ä™bokiego snu (EM2) dziaÅ‚a na baterii. Aplikacja czeka na port COM.
* **Przebieg:** Po podÅ‚Ä…czeniu USB aplikacja PC otwiera nowy port COM, wysyÅ‚a *Bajt WybudzajÄ…cy*, odczekuje chwilÄ™ i wysyÅ‚a pierwszÄ… komendÄ™ operacyjnÄ….
* **Rezultat:** Przerwanie sprzÄ™towe na pinie RX momentalnie budzi EFR32. Komenda jest odbierana poprawnie, system podejmuje normalnÄ… pracÄ™.

### Scenariusz B: UrzÄ…dzenie podÅ‚Ä…czone âž” Aplikacja dopiero startuje
* **Stan poczÄ…tkowy:** UrzÄ…dzenie jest wpiÄ™te do USB komputera, ale Å›pi (EM2), poniewaÅ¼ z powodu braku uprzednio uruchomionej aplikacji PC nastÄ…piÅ‚ timeout.
* **Przebieg:** UÅ¼ytkownik uruchamia aplikacjÄ™ KeySec. Aplikacja otwiera istniejÄ…cy w systemie port, wysyÅ‚a *Bajt WybudzajÄ…cy* i po ok. 10 ms wysyÅ‚a komendÄ™ inicjujÄ…cÄ….
* **Rezultat:** EFR32 wybudza siÄ™ identycznie jak w Scenariuszu A i bÅ‚yskawicznie przystÄ™puje do pracy.

### Scenariusz C: Normalna praca âž” UÅ¼ytkownik zamyka aplikacjÄ™ PC (Crash)
* **Stan poczÄ…tkowy:** UkÅ‚ad wybudzony (EM1), trwa poprawna komunikacja.
* **Przebieg:** Aplikacja PC zostaje niespodziewanie zamkniÄ™ta lub awaryjnie wstrzymana (od tej pory brak odpowiedzi PONG).
* **Rezultat:** UpÅ‚ywa cykl czasu oczekiwania (timeout) w firmware. EFR32 bezpiecznie usuwa wymÃ³g blokady EM1 i natychmiast wraca do trybu gÅ‚Ä™bokiego snu (EM2), radykalnie oszczÄ™dzajÄ…c bateriÄ™. (Realizacja zasady *Fail Fast* oraz *Defensive Programming*).

### Scenariusz D: Normalna praca âž” Kabel USB zostaje fizycznie wyrwany
* **Stan poczÄ…tkowy:** UkÅ‚ad wybudzony (EM1).
* **Przebieg:** Zasilanie ukÅ‚adu mostka SAMD11 na pÅ‚ytce zanika, fizyczna linia transmisyjna milknie. Zrywa siÄ™ poÅ‚Ä…czenie z komputerem.
* **Rezultat:** Zachowanie identyczne do Scenariusza C â€“ EFR32 wysyÅ‚a komunikaty, nie otrzymuje odpowiedzi, wpada w timeout i idzie spaÄ‡ (EM2).

### Scenariusz E: UrzÄ…dzenie wpinane do USB âž” Brak uruchomionej aplikacji PC na docelowym komputerze
* **Stan poczÄ…tkowy:** UrzÄ…dzenie Å›pi (EM2) na baterii.
* **Przebieg:** UrzÄ…dzenie podpiÄ™te pod komputer (lub zewnÄ™trznÄ… Å‚adowarkÄ™ sieciowÄ…). Bateria Å‚aduje siÄ™ poprzez 5V VBUS, ale port COM na PC pozostaje nieotwarty (nikt nie nadaje sygnaÅ‚u RX).
* **Rezultat:** EFR32 **pozostaje gÅ‚Ä™boko uÅ›piony (EM2)**. Jest to zachowanie celowe i poÅ¼Ä…dane â€“ procesor EFR32 ignoruje podÅ‚Ä…czenie zasilania oszczÄ™dzajÄ…c cykle zegarowe, wiedzac Å¼e i tak nie nawiÄ…Å¼e skutecznej autoryzacji z powodu braku oprogramowania PC.

### Scenariusz F: FaÅ‚szywe wybudzenie (Glitches / Obcy terminal)
* **Stan poczÄ…tkowy:** UrzÄ…dzenie Å›pi (EM2).
* **Przebieg:** Na kablu nastÄ™puje zakÅ‚Ã³cenie imitujÄ…ce transmisjÄ™ UART, ALBO przypadkowy uÅ¼ytkownik otwiera port w zewnÄ™trznym terminalu typu PuTTY i naciska klawisz spacji.
* **Rezultat:** EFR32 Å‚apie impuls na pinie RX i wybudza siÄ™ profilaktycznie do EM1. Procesor zablokowuje usypianie i wysyÅ‚a PING, oczekujÄ…c formalnej wymiany danych (np. poprawny JSON). PoniewaÅ¼ ani impuls-Å›mieÄ‡, ani przypadkowy terminal nie odpowie poprawnym JSON-em z symbolem PONG, urzÄ…dzenie bardzo szybko raportuje timeout. Po 1 lub 2 sekundach firmware bezpowrotnie uÅ›pi ukÅ‚ad do stanu EM2.
* **Wniosek:** UrzÄ…dzenie posiada wysokÄ… tolerancjÄ™ na zakÅ‚Ã³cenia (False Wakeups), chroniÄ…c bateriÄ™ przed nieuzasadnionym rozÅ‚adowaniem.

