from machine import Pin
import network
import time
import urequests
import gc
import sys
# 必要なパスを確認し追加
REMOTE_CODE_PATH = "/remote_code"
LIB_PATH = f"{REMOTE_CODE_PATH}/lib"
if REMOTE_CODE_PATH not in sys.path:
    sys.path.append(REMOTE_CODE_PATH)
if LIB_PATH not in sys.path:
    sys.path.append(LIB_PATH)
from dht import DHT22  # DHT11からDHT22に変更
# デバッグモード
DEBUG = True
# LED設定
led = Pin("LED", Pin.OUT)
# DHT22センサー設定
dht = DHT22(Pin(28))  # GPIO 28に接続。DHT11からDHT22に変更
# 設定
ENDPOINT = "https://script.google.com/macros/s/AKfycbztdwfhufixP7Rd2Xs2UgaymT5IwNn294LgEB2q7gX1dyhR1i0FSw4X0RpW5NO1skM0/exec"
MAX_WAIT = 30
MAX_RETRIES = 3
RETRY_DELAY = 10
SEND_INTERVAL = 120
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
    # wlanが未初期化の場合は初期化
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    # 既に接続されている場合はスキップ
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
            # 接続待機
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
def try_send_data():
    """データを送信する"""
    global wlan
    response = None
    local_wlan = None
    try:
        gc.collect()
        connected, ssid, local_wlan = connect_wifi()
        if not connected:
            return False
        # DHT22センサーから読み取り
        try:
            debug_print("Reading DHT22 sensor...")  # メッセージをDHT22に更新
            dht.measure()
            temperature = dht.temperature()
            humidity = dht.humidity()
            
            debug_print(f"温度: {temperature}°C")
            debug_print(f"湿度: {humidity}%")
        except Exception as e:
            debug_print(f"Error reading from DHT22: {e}")  # エラーメッセージをDHT22に更新
            return False
        # データ作成
        data = {
            "device_id": "PicoW-01",
            "ip_address": local_wlan.ifconfig()[0],
            "wifi_ssid": ssid,
            "mac_address": ":".join(["{:02x}".format(b) for b in local_wlan.config('mac')]),
            "memory_free": gc.mem_free(),
            "signal_strength": local_wlan.status('rssi') if local_wlan else None,
            "temperature": temperature,
            "humidity": humidity,
            "pressure": None,
            "timestamp": time.time()
        }
        
        debug_print("Attempting to send data...")
        debug_print(f"Endpoint: {ENDPOINT}")
        debug_print(f"Data: {data}")
        
        # データ送信
        try:
            response = urequests.post(
                ENDPOINT,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            debug_print(f"Response status: {response.status_code}")
            debug_print(f"Response text: {response.text}")
            # ステータスコードが400でも許容
            if response.status_code == 400:
                debug_print("400 Bad Request: Ignored as acceptable.")
                return True
            # 許容外のステータスコードは失敗扱い
            if response.status_code != 200:
                debug_print("Unexpected response status, treating as failure.")
                return False
        except OSError as e:
            debug_print(f"Network error: {e}")
            if str(e) == "-2":
                debug_print("Connection failed - this might be a DNS or SSL/TLS issue")
            return False
        except Exception as e:
            debug_print(f"Error sending data: {e}")
            return False
            
    except Exception as e:
        debug_print(f"エラー: {e}")
        return False
        
    finally:
        if response:
            response.close()
        if local_wlan and local_wlan.isconnected():
            local_wlan.active(False)
        led.value(0)
        gc.collect()
def send_data_with_retry():
    """リトライ機能付きでデータを送信"""
    for attempt in range(MAX_RETRIES):
        if try_send_data():
            return True
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    return False
def main():
    """メイン処理"""
    debug_print("測定開始")
    
    try:
        if send_data_with_retry():
            led.value(1)
            time.sleep(0.5)
            led.value(0)
        else:
            for _ in range(3):  # エラー時のLED点滅
                led.value(1)
                time.sleep(0.2)
                led.value(0)
                time.sleep(0.2)
    except Exception as e:
        debug_print(f"メインループエラー: {e}")
        time.sleep(5)
try:
    main()
except Exception as e:
    debug_print(f"致命的エラー: {e}")
