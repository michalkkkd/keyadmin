import time
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

        print('\n--- KROK 1: Sprawdzenie licencji ---')
        print('->', compass.check_license())

        print('\n--- KROK 2: Synchronizacja czasu ---')
        print('->', admin.update_current_date(aktualny_czas))

        print('\n--- KROK 3: Aktywacja ---')
        print('->', admin.set_license_days(30))

        print('\n--- KROK 4: Weryfikacja ---')
        print('->', compass.check_license())

        print('\n--- KROK 5: Test Algorytmu ---')
        print('->', compass.calculate_algorithm_1(5, 10))

    finally:
        transport.close()

if __name__ == '__main__':
    main()
