from machine import Pin
import network
import time
import urequests
import gc
import sys
import socket

# 必要なパスを確認し追加
REMOTE_CODE_PATH = "/remote_code"
LIB_PATH = f"{REMOTE_CODE_PATH}/lib"
if REMOTE_CODE_PATH not in sys.path:
    sys.path.append(REMOTE_CODE_PATH)
if LIB_PATH not in sys.path:
    sys.path.append(LIB_PATH)

# デバッグモード
DEBUG = True

# LED設定
led = Pin("LED", Pin.OUT)

# 設定
CHATWORK_API_TOKEN = "fba258f13899e421b3ab7a3a50488807"
CHATWORK_ROOM_ID = "67575950"
CHATWORK_API_URL = f"https://api.chatwork.com/v2/rooms/{CHATWORK_ROOM_ID}/messages"

MAX_WAIT = 30
MAX_RETRIES = 3
RETRY_DELAY = 10

# Wi-Fi設定
WIFI_SETTINGS = [
    {"ssid": "740635A8CCFD-2G", "password": "nn5rh49s5d7saa"},
    {"ssid": "TP-Link_A208", "password": "15405173"},
    {"ssid": "moonwalker", "password": "11112222"}
]

# グローバル変数
wlan = None
current_ssid = None

def debug_print(*args):
    if DEBUG:
        print("DEBUG:", *args)

def connect_wifi():
    """Wi-Fi接続を確立"""
    global wlan, current_ssid
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        debug_print("Wi-Fi already connected.")
        return True, current_ssid or wlan.config("essid"), wlan

    wlan.active(False)
    time.sleep(1)
    wlan.active(True)
    
    for wifi_setting in WIFI_SETTINGS:
        try:
            debug_print(f"接続試行中: {wifi_setting['ssid']}...")
            wlan.connect(wifi_setting["ssid"], wifi_setting["password"])
            start = time.time()
            while time.time() - start < MAX_WAIT:
                if wlan.isconnected():
                    led.value(1)
                    current_ssid = wifi_setting["ssid"]
                    return True, current_ssid, wlan
                time.sleep(1)
        except Exception as e:
            debug_print(f"接続エラー: {e}")
    
    led.value(0)
    return False, None, None

def find_raspberry_pi():
    """RaspberryPiのIPを探す"""
    try:
        # ngrokの管理インターフェースポートをスキャン
        debug_print("Scanning for Raspberry Pi...")
        
        # まずlocalhost（USB接続されているRaspberryPi）をチェック
        try:
            response = urequests.get("http://localhost:4040/api/tunnels", timeout=5)
            return "localhost", True
        except:
            debug_print("localhost:4040 not accessible")

        # ローカルネットワークの一般的なRaspberry PiのIPレンジをスキャン
        base_ip = wlan.ifconfig()[0].rsplit('.', 1)[0]
        for i in range(1, 255):
            ip = f"{base_ip}.{i}"
            try:
                response = urequests.get(f"http://{ip}:4040/api/tunnels", timeout=1)
                return ip, True
            except:
                continue
            
        return None, False
            
    except Exception as e:
        debug_print(f"Error finding Raspberry Pi: {e}")
        return None, False

def send_to_chatwork(message):
    """Chatworkにメッセージを送信"""
    try:
        headers = {
            'X-ChatWorkToken': CHATWORK_API_TOKEN,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = f"body={message}"
        
        response = urequests.post(
            CHATWORK_API_URL,
            data=data,
            headers=headers
        )
        
        debug_print(f"Chatwork response: {response.status_code}")
        response.close()
        return True
    except Exception as e:
        debug_print(f"Error sending to Chatwork: {e}")
        return False

def main():
    """メイン処理"""
    debug_print("開始")
    
    try:
        # Wi-Fi接続
        connected, ssid, local_wlan = connect_wifi()
        if not connected:
            send_to_chatwork("[IP確認失敗] Wi-Fi接続できませんでした")
            return False
            
        # RaspberryPiを探す
        ip, found = find_raspberry_pi()
        
        if found:
            message = f"[IP確認成功] RaspberryPiのIP: {ip}"
            led.value(1)
        else:
            message = "[IP確認失敗] RaspberryPiが見つかりませんでした"
            # エラー時のLED点滅
            for _ in range(3):
                led.value(1)
                time.sleep(0.2)
                led.value(0)
                time.sleep(0.2)
        
        # Chatworkに送信
        sent = send_to_chatwork(message)
        if not sent:
            debug_print("Chatworkへの送信に失敗しました")
            
    except Exception as e:
        debug_print(f"メインループエラー: {e}")
        try:
            send_to_chatwork(f"[エラー] {str(e)}")
        except:
            pass
        time.sleep(5)
    finally:
        led.value(0)
        if local_wlan and local_wlan.isconnected():
            local_wlan.active(False)
        gc.collect()

try:
    main()
except Exception as e:
    debug_print(f"致命的エラー: {e}")
    try:
        send_to_chatwork(f"[致命的エラー] {str(e)}")
    except:
        pass
