import builtins
import sys
from datetime import datetime

LOG_CONFIG = {
    'Transport': False,      # e.g., [Transport] Port opened...
    'Raw': False,            # e.g., > RAW: 0181...
    'SecureChannel': True,   # e.g., [SecureChannel] Sending Handshake Init...
    'Protocol': False,       # e.g., [Protocol] Sending ID: ...
    'MCU': True,             # e.g., [MCU] TEST-INFO: ...
    'Info': True,            # e.g., [INFO] or [+]
    'Flow': True,            # e.g., -> OK: or ERR:
    'Other': True            # everything else
}

_original_print = builtins.print

def _timestamped_print(*args, **kwargs):
    if args and isinstance(args[0], str):
        msg = str(args[0]).lstrip('\n ')
        
        if msg.startswith('[Transport]') and not LOG_CONFIG.get('Transport', True): return
        if msg.startswith('> RAW:') and not LOG_CONFIG.get('Raw', True): return
        if msg.startswith('[SecureChannel]') and not LOG_CONFIG.get('SecureChannel', True): return
        if msg.startswith('[Protocol]') and not LOG_CONFIG.get('Protocol', True): return
        if msg.startswith('[MCU]') and not LOG_CONFIG.get('MCU', True): return
        if (msg.startswith('[INFO]') or msg.startswith('[+]')) and not LOG_CONFIG.get('Info', True): return
        if (msg.startswith('->') or msg.startswith('OK:') or msg.startswith('ERR:')) and not LOG_CONFIG.get('Flow', True): return

    ts = datetime.now().strftime('[%H:%M:%S.%f]')
    _original_print(ts, *args, **kwargs)
    sys.stdout.flush()

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
    
    import time as _t
    t0 = _t.perf_counter()
    hs_result = sec_chan.init_handshake()
    t1 = _t.perf_counter()
    handshake_time = t1 - t0
    
    if not hs_result:
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

        print('\n--- STEP 5: PERFORMANCE BENCHMARK ---')
        user_hash_1 = 123456789
        
        # Measure a single simple function call
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        
        t0_alg = _t.perf_counter()
        res = compass.calculate_algorithm_1(user_hash_1, a, b)
        t1_alg = _t.perf_counter()
        alg_time = t1_alg - t0_alg
        
        print(f'\n============================================================')
        print(f'  === PERFORMANCE METRICS ===')
        print(f'============================================================')
        print(f'[+] 1. Full ECDHE Session Handshake : {handshake_time*1000:.2f} ms')
        print(f'[+] 2. Single Crypto Algorithm Call : {alg_time*1000:.2f} ms')
        print(f'============================================================\n')

    finally:
        transport.close()

if __name__ == '__main__':
    main()




