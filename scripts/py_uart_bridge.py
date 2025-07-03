import os
import pty
import threading
import serial
import select
import time
import json

# --- CONFIGURATION ---
UART_PORT = '/dev/ttyS0'
UART_BAUDRATE = 115200
TIMEOUT = 0.1  # seconds
GPS_POLL_RATE = 2 # seconds

# --- CREATE VIRTUAL PORTS ---
master1, slave1 = pty.openpty()
# master2, slave2 = pty.openpty()

port1 = os.ttyname(slave1)
# port2 = os.ttyname(slave2)

# print(f"✅ Virtual ports created:\n  {port1}\n  {port2}")
print(f"✅ Virtual ports created:\n  {port1}")

# --- OPEN REAL UART ---
uart = serial.Serial(UART_PORT, UART_BAUDRATE, timeout=TIMEOUT)

def check_gps_data(line):

    if line.startswith('+CGNSINF:'):

        infos = line[len('+CGNSINF: '):].split(',')
        
        run_status = infos[0]
        fix_status = infos[1]
        utc_date = infos[2]

        lat = infos[3]
        lon = infos[4]

        sattelites_in_view = infos[14]
        sattelites_in_view_GLONASS = infos[16]

        print(f'Run status: {run_status}; Fix status: {fix_status}; Lat: {lat}; Lon: {lon}; Utc: {utc_date}; Sattelites: {sattelites_in_view}')

        data = {
            'run_status': run_status,
            'fix_status': fix_status,
            'utc_date': utc_date,
            'lat': lat,
            'lon': lon,
            'sattelites_in_view': sattelites_in_view
        }

        with open('./gps.json', 'w') as f:
            f.write(json.dumps(data))
            f.flush()


# --- FUNCTION: FORWARD DATA FROM SOURCE FD TO TARGET FD(S) ---
def forward(src_fd, targets, label, out = False):

    if out:
        for t in targets:


            os.write(t, 'AT+CGNSPWR=1\r\n'.encode('utf-8'))
            time.sleep(0.1)
            os.write(t, 'AT+CGNSSEQ=\"RMC\"\r\n'.encode('utf-8'))
            # time.sleep(0.1)
            # os.write(t, 'AT+CGNSINF'.encode('utf-8'))

    last_gps_request = time.time()
    current_line = ''
    while True:

        cur_time = time.time() 

        # send gps requests
        if out and (cur_time - last_gps_request) > GPS_POLL_RATE:

            print('making gps request')

            last_gps_request = cur_time
            for t in targets:
                os.write(t, 'AT+CGNSINF\r\n'.encode('utf-8'))


        rlist, _, _ = select.select([src_fd], [], [], TIMEOUT)
        if src_fd in rlist:
            try:
                data = os.read(src_fd, 1024)
                try:

                    if not out:
                        decoded = data.decode('utf-8')
                        current_line += decoded

                        if '\n' in current_line:
                            lines = current_line.split('\n')

                            for l in lines[:-1]:
                                check_gps_data(l)

                            current_line = lines[-1]

                except:
                    pass
                i = 0
                for t in targets:
                    os.write(t, data)
                    # print(f'sending on {label}-{i}: {data} ')
                    i += 1
            except OSError as e:
                print(f"[{label}] Error: {e}")
                break

# --- START THREADS ---
# real UART → virtual ports
threading.Thread(
    target=forward,
    # args=(uart.fileno(), [master1, master2], 'UART→VIRTUAL'),
    args=(uart.fileno(), [master1], 'UART-VIRTUAL'),
    daemon=True
).start()

# virtual ports → real UART
threading.Thread(
    target=forward,
    args=(master1, [uart.fileno()], 'VIRTUAL1-UART', True),
    daemon=True
).start()

# threading.Thread(
#     target=forward,
#     args=(master2, [uart.fileno()], 'VIRTUAL2→UART'),
#     daemon=True
# ).start()

# --- KEEP ALIVE ---
try:
    print("\n🔁 Multiplexing active. Use these ports from your scripts:")
    print(f"    Script 1: {port1}")
    # print(f"    Script 2: {port2}")
    # input("\nPress Enter to stop...\n")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[🛑] Shutting down.")
finally:
    uart.close()
