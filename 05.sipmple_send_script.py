from machine import Pin
import network
import time
import urequests
import gc
import sys

# 設定
DEBUG = True
led = Pin("LED", Pin.OUT)
CHATWORK_API_TOKEN = "fba258f13899e421b3ab7a3a50488807"
CHATWORK_ROOM_ID = "67575950"
CHATWORK_API_URL = f"https://api.chatwork.com/v2/rooms/{CHATWORK_ROOM_ID}/messages"

# Wi-Fi設定
WIFI_SETTINGS = [
    {"ssid": "740635A8CCFD-2G", "password": "nn5rh49s5d7saa"},
    {"ssid": "TP-Link_A208", "password": "15405173"},
    {"ssid": "moonwalker", "password": "11112222"}
]

def debug_print(*args):
    if DEBUG:
        print("DEBUG:", *args)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    for wifi in WIFI_SETTINGS:
        try:
            debug_print(f"Trying to connect to {wifi['ssid']}")
            wlan.connect(wifi["ssid"], wifi["password"])
            for _ in range(10):  # 10秒待つ
                if wlan.isconnected():
                    return wlan
                time.sleep(1)
        except:
            continue
    return None

def send_to_chatwork(message):
    try:
        headers = {
            'X-ChatWorkToken': CHATWORK_API_TOKEN,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = f"body={message}"
        response = urequests.post(CHATWORK_API_URL, data=data, headers=headers)
        response.close()
        return True
    except Exception as e:
        debug_print(f"Chatwork error: {e}")
        return False

def scan_network():
    import socket
    
    wlan = connect_wifi()
    if not wlan:
        return "Wi-Fi接続失敗"
    
    # このデバイスのネットワーク情報
    ip = wlan.ifconfig()[0]
    base_ip = ip.rsplit('.', 1)[0]
    
    # 結果を格納するリスト
    devices = [f"Pico W: {ip}"]
    devices.append(f"Gateway: {wlan.ifconfig()[2]}")
    
    # RaspberryPiの一般的なMACアドレスプレフィックス
    raspberry_pi_macs = [
        "B8:27:EB",  # Raspberry Pi 1,2,3
        "DC:A6:32",  # Raspberry Pi 4
        "E4:5F:01"   # Raspberry Pi 4
    ]
    
    # ネットワークスキャン
    for i in range(1, 255):
        try:
            target_ip = f"{base_ip}.{i}"
            if target_ip == ip:  # 自分自身はスキップ
                continue
                
            s = socket.socket()
            s.settimeout(0.1)  # 100ms
            if s.connect_ex((target_ip, 22)) == 0:  # SSHポート
                devices.append(f"Found device (SSH open): {target_ip}")
            s.close()
            
            # 4040ポート（ngrok）もチェック
            s = socket.socket()
            s.settimeout(0.1)
            if s.connect_ex((target_ip, 4040)) == 0:
                devices.append(f"Found device (ngrok port open): {target_ip}")
            s.close()
            
        except:
            continue
    
    return "\n".join(devices)

def main():
    try:
        result = scan_network()
        message = f"[ネットワークスキャン結果]\n{result}"
        if send_to_chatwork(message):
            led.value(1)
            time.sleep(0.5)
            led.value(0)
        else:
            for _ in range(3):  # エラー時は点滅
                led.value(1)
                time.sleep(0.2)
                led.value(0)
                time.sleep(0.2)
    except Exception as e:
        error_msg = f"[エラー] {str(e)}"
        debug_print(error_msg)
        send_to_chatwork(error_msg)
    finally:
        gc.collect()

try:
    main()
except Exception as e:
    debug_print(f"Fatal error: {e}")
