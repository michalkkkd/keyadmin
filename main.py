import time
import random
from core.transport import SerialTransport
from core.protocol import RpcProtocol
from api.admin_api import AdminApi
from api.compass_api import CompassApi

def main():
    print('=' * 60)
    print('  === KEYSEC DONGLE v0.5 - ARCHITEKTURA MODULARNA ===')
    print('=' * 60)

    # 1. Inicjalizacja warstw
    transport = SerialTransport(port='COM7')
    rpc = RpcProtocol(transport)

    admin = AdminApi(rpc, admin_pin='1234')
    compass = CompassApi(rpc)

    try:
        aktualny_czas = int(time.time())

        # print('\n--- KROK 0: Reset Fabryczny (Czyszczenie czasu) ---')
        # print('->', admin.wipe_device())
        # time.sleep(1)

        print('\n--- KROK 1: Sprawdzenie licencji ---')
        lic_status = compass.check_license()
        print('->', lic_status)
        
        print('\n--- KROK 1.5: Szczegolowa diagnostyka Global RTC ---')
        print(admin.debug_time())
        
        if 'RTC niezsynchronizowany' in lic_status or 'Brak licencji' in lic_status or 'EXPIRED' in lic_status:
            print('\n--- KROK 2: Synchronizacja czasu ---')
            print('->', admin.update_current_date(aktualny_czas))
            
            print('\n--- KROK 3: Aktywacja licencji (30 dni) ---')
            print('->', admin.set_license_days(30))
            print('   (Czekam 2s na NVM3 repack...)')
            time.sleep(2)
        else:
            print('   (Pominieto synchronizacje - MCU juz skonfigurowany)')
        
        print('\n--- KROK 4: Weryfikacja ---')
        print('->', compass.check_license())

        print('\n--- KROK 5: Test Algorytmu ---')
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        print(f'   [INFO] Generuje losowe liczby: {a} i {b}')
        print('->', compass.calculate_algorithm_1(a, b))

    finally:
        transport.close()

if __name__ == '__main__':
    main()
