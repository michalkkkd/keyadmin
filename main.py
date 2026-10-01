import time
import random
from core.transport import SerialTransport
from core.protocol import RpcProtocol
from api.admin_api import AdminApi
from api.compass_api import CompassApi

def main():
    print('=' * 60)
    print('  === KEYSEC DONGLE v0.5 - MODULAR ARCHITECTURE ===')
    print('=' * 60)

    # 1. Layer Initialization
    transport = SerialTransport(port='COM7')
    rpc = RpcProtocol(transport)

    admin = AdminApi(rpc, admin_pin='1234')
    compass = CompassApi(rpc)

    try:
        current_time = int(time.time())

        # print('\n--- STEP 0: Factory Reset (Time Wipe) ---')
        # print('->', admin.wipe_device())
        # time.sleep(1)

        print('\n--- STEP 1: License Check ---')
        lic_status = compass.check_license()
        print('->', lic_status)
        
        print('\n--- STEP 1.5: Detailed Global RTC Diagnostics ---')
        print(admin.debug_time())
        
        print('\n--- STEP 1.8: Memory Diagnostics ---')
        print(admin.get_memory_info())
        
        if 'RTC out of sync' in lic_status or 'No license' in lic_status or 'EXPIRED' in lic_status:
            print('\n--- STEP 2: Time Synchronization ---')
            print('->', admin.update_current_date(current_time))
            
            print('\n--- STEP 3: License Activation (30 days and 5 users) ---')
            print('->', admin.set_license_days(30))
            print('->', admin.set_max_users(1))
            print('   (Waiting 2s for NVM3 repack...)')
            time.sleep(2)
        else:
            print('   (Synchronization skipped - MCU already configured)')
        
        print('\n--- FORCING USER LIMIT TO 1 ---'); print('->', admin.set_max_users(1)); print('\n--- STEP 4: Verification ---')
        print('->', compass.check_license())
        print('->', compass.get_max_users())

        print('\n--- STEP 5: Algorithm Test ---')
        user_hash_1 = 123456789
        user_hash_2 = 987654321
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        print(f'   [INFO] Generating random numbers: {a} and {b}')
        print('-> User 1: ', compass.calculate_algorithm_1(user_hash_1, a, b))
        print('-> User 2: ', compass.calculate_algorithm_1(user_hash_2, a, b))

    finally:
        transport.close()

if __name__ == '__main__':
    main()
