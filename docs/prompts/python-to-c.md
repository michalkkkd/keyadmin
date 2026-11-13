**Zadanie:** Przenieś metodę matematyczną Pythona `[METHOD_NAME]` z frontendu `compass` na urządzenie `KeyFirmware`. 

**Cel:** Musimy bezbłędnie przetłumaczyć logikę Pythona (NumPy/Pandas) na wysoce zoptymalizowany kod C/C++. Aby zagwarantować, że dane przekazywane między Pythonem a urządzeniem są IDEALNE, wszystkie wejścia i wyjścia muszą być ściśle serializowane jako JSON.

Przeprowadź migrację, wykonując następujące kroki:

**1. Tłumaczenie matematyki (firmware w C)**
* Dodaj logikę do `KeyFirmware/src/prod/` (tajna logika algorytmów mieszka w `src/prod/compass_core.cpp`; katalog `src/logic/` **nie istnieje**).
* Przetłumacz główny algorytm. Zwróć szczególną uwagę na dokładność matematyczną, zastępując funkcje Pandas/NumPy wydajnymi odpowiednikami w C.
* Użyj biblioteki `cJSON` do parsowania przychodzącej konfiguracji i do generowania wyjściowej odpowiedzi JSON (która w zależności od metody może być tablicą, obiektem lub pojedynczą wartością).
* **Ostrzeżenie dotyczące pamięci:** Upewnij się, że statyczne bufory JSON do odbioru/nadawania mają rozmiar odpowiedni do payloadu tej konkretnej metody, aby zapobiec awariom `ERR: OOM`. Nie używaj niebezpiecznie małych, ogólnych buforów.

**2. API dzielenia JSON na fragmenty (chunking) (`KeySec` i firmware)**
* Ponieważ konfiguracje JSON mogą być duże, używamy 4-etapowego protokołu chunkingu (`INIT`, `CHUNK`, `PROCESS`, `READ`).
* Zarezerwuj 4 nowe, kolejne identyfikatory hex w `KeySec/keycomm/core/transport.py` (np. `0x40-0x43`).
* Zarejestruj te identyfikatory w warstwie routingu firmware (`KeyFirmware/src/core/router_common.c/.h` + właściwy router domenowy; pliku `rpc_router.h` **nie ma**) i zaimplementuj 4 standardowe handlery. 
* **API Pythona:** Logikę transmisji zamknij w klasie `[MethodName]Runner(BaseRunner)` w `KeySec/keycomm/logic_dummy/` (metody `execute_send` / `execute_process` / `execute_receive`), która dzielenie na fragmenty realizuje przez `ChunkStreamer` (`keycomm/core/chunk_streamer.py`) z 4 nowymi identyfikatorami — NIE pisz ręcznych pętli chunkingu. Następnie w `KeySec/keycomm/api/compass_api.py` dodaj cienki wrapper `execute_[method_name](self, data_dict, vrx_token)`, który serializuje słownik do JSON i deleguje jedną linią: `return [MethodName]Runner(self.rpc, self.user_hash, int(vrx_token)).execute(data_dict)` (wzorzec jak `execute_sim_pk_gi` → `SimPkGiRunner`, `compass_api.py:118-121`).

**3. Integracja z frontendem (`compass`)**
* Znajdź `[METHOD_NAME]` w logice `compass/app/`.
* Zduplikuj metodę jako `[METHOD_NAME]_device`. 
* Na początku oryginalnej funkcji wstaw: `if Functions.USE_DEVICE: return [METHOD_NAME]_device(app_conf)`.
* W metodzie `_device` wykonaj wywołanie API, sparsuj zwrócony łańcuch JSON z powrotem do dokładnie tych samych, oryginalnych struktur danych Pythona (DataFrame, słownik, float itp.) i zwróć wynik.

**4. Payload testowy**
* Jeśli musisz wygenerować payload testowy, zapisz go w `KeySec/keycomm/api/test_payloads.py`, używając **surowego bloku w potrójnych cudzysłowach** (`r"""..."""`), aby Python nie interpretował niepoprawnie znaków ucieczki w ścieżkach plików Windows (`\\`).

Skup się przede wszystkim na tym, by tłumaczenie matematyki na C dokładnie odtwarzało wyniki Pythona. Daj znać, jeśli masz pytania dotyczące typów danych, zanim zaczniesz pisać logikę w C.