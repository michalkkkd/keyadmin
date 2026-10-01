import builtins
from datetime import datetime

_original_print = builtins.print
def _timestamped_print(*args, **kwargs):
    ts = datetime.now().strftime('[%H:%M:%S.%f]')[:-3] + ']'
    _original_print(ts, *args, **kwargs); import sys; sys.stdout.flush()
builtins.print = _timestamped_print
import time
import os
from core.secure_channel import SecureChannel
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
    
    # Establish Secure Channel (ECDHE)
    root_ca_path = os.path.join('keys', 'root_ca_pub.pem')
    sec_chan = SecureChannel(rpc, root_ca_path)
    if not sec_chan.init_handshake():
        print('[-] FATAL: Failed to establish secure ECDHE channel.')
        transport.close()
        return
    rpc.secure_channel = sec_chan
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

        print('\\n--- STEP 5: Algorithm Test (STRESS TEST 1000x) ---')
        user_hash_1 = 123456789
        user_hash_2 = 987654321
        
        success_count = 0
        error_count = 0
        import time as _t
        
        start_time_total = _t.perf_counter()
        for i in range(1, 1001):
            a = random.randint(1, 100)
            b = random.randint(1, 100)
            try:
                res1 = compass.calculate_algorithm_1(user_hash_1, a, b)
                _t.sleep(0.05)
                res2 = compass.calculate_algorithm_1(user_hash_2, a, b)
                _t.sleep(0.05)
                
                if "OK:" in res1 and "ERR:" in res2:
                    success_count += 1
                else:
                    print(f'[!] Iteration {i} logic mismatch! User1: {res1} | User2: {res2}')
                    error_count += 1
                
                if i % 50 == 0:
                    print(f'   [INFO] Progress: {i}/1000. Success: {success_count}, Errors: {error_count}')
            except Exception as e:
                print(f'[!] Exception at iteration {i}: {e}')
                error_count += 1
                continue

        total_time = _t.perf_counter() - start_time_total
        print('\\n--- TEST COMPLETE ---')
        print(f'Time taken: {total_time:.2f} seconds')
        print(f'Total iterations: 1000, Success: {success_count}, Errors: {error_count}')

    finally:
        transport.close()

if __name__ == '__main__':
    main()




