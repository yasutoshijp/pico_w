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

from dht import DHT11

# 定数定義
DEBUG = True
LED = Pin("LED", Pin.OUT)
DHT_PIN = 28
dht = DHT11(Pin(DHT_PIN))

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
    """デバッグ情報を出力"""
    if DEBUG:
        print("DEBUG:", *args)

def connect_wifi():
    """Wi-Fi接続を確立（変更なし）"""
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
                    LED.value(1)
                    current_ssid = wifi_setting["ssid"]
                    return True, current_ssid, wlan
                time.sleep(1)
        except Exception as e:
            debug_print(f"接続エラー: {e}")

    LED.value(0)
    return False, None, None

def read_dht11_raw_timing(pin_num):
    """DHT11の生データ（タイミング）を取得"""
    pin = Pin(pin_num, Pin.IN)
    timings = []
    last_transition = time.ticks_us()
    
    # 開始シグナル
    pin.init(Pin.OUT)
    pin.value(1)
    time.sleep_ms(50)
    pin.value(0)
    time.sleep_ms(20)
    
    # ピンを入力モードに切り替え
    pin.init(Pin.IN)
    
    # データ読み取り
    level = 0
    for _ in range(85):  # 応答 + 40ビットデータ
        while pin.value() == level:
            if time.ticks_diff(time.ticks_us(), last_transition) > 100000:
                return None
        
        current = time.ticks_us()
        timings.append(time.ticks_diff(current, last_transition))
        last_transition = current
        level = pin.value()
    
    return timings

def parse_raw_timings(timings):
    """生データから温度・湿度を計算"""
    if not timings or len(timings) < 40:
        return None, None
    
    # データビットの解析
    bits = []
    for i in range(0, len(timings)-1, 2):
        # 26-28μsがビット"0"、70μsがビット"1"
        if 60 <= timings[i+1] <= 80:
            bits.append(1)
        else:
            bits.append(0)
    
    # バイトに変換
    bytes_data = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i+j < len(bits):
                byte = (byte << 1) | bits[i+j]
        bytes_data.append(byte)
    
    if len(bytes_data) >= 4:
        raw_humidity = bytes_data[0]
        raw_temperature = bytes_data[2]
        return raw_temperature, raw_humidity
    return None, None

def try_send_data():
    """データを送信する（修正版）"""
    global wlan
    response = None
    local_wlan = None
    
    try:
        gc.collect()
        connected, ssid, local_wlan = connect_wifi()
        if not connected:
            return False

        try:
            debug_print("Reading raw DHT11 data...")
            # まず生データを取得
            raw_timings = read_dht11_raw_timing(DHT_PIN)
            raw_temp, raw_hum = parse_raw_timings(raw_timings) if raw_timings else (None, None)
            
            # 次に通常の測定
            dht.measure()
            temperature = dht.temperature()
            humidity = dht.humidity()
            
            debug_print(f"ライブラリ温度: {temperature}°C")
            debug_print(f"ライブラリ湿度: {humidity}%")
            debug_print(f"生データ温度: {raw_temp}°C")
            debug_print(f"生データ湿度: {raw_hum}%")
            debug_print(f"タイミングデータ: {raw_timings}")
            
        except Exception as e:
            debug_print(f"Error reading from DHT11: {e}")
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
            "raw_data": raw_timings,
            "raw_temperature": raw_temp,
            "raw_humidity": raw_hum,
            "timestamp": time.time()
        }
        
        debug_print("Attempting to send data...")
        debug_print(f"Data: {data}")
        
        try:
            response = urequests.post(
                ENDPOINT,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            debug_print(f"Response status: {response.status_code}")
            debug_print(f"Response text: {response.text}")

            if response.status_code == 400:
                debug_print("400 Bad Request: Ignored as acceptable.")
                return True

            if response.status_code != 200:
                debug_print("Unexpected response status, treating as failure.")
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
        LED.value(0)
        gc.collect()

def send_data_with_retry():
    """リトライ機能付きでデータを送信（変更なし）"""
    for attempt in range(MAX_RETRIES):
        if try_send_data():
            return True
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    return False

def main():
    """メイン処理（変更なし）"""
    debug_print("測定開始")
    
    try:
        if send_data_with_retry():
            LED.value(1)
            time.sleep(0.5)
            LED.value(0)
        else:
            for _ in range(3):
                LED.value(1)
                time.sleep(0.2)
                LED.value(0)
                time.sleep(0.2)

    except Exception as e:
        debug_print(f"メインループエラー: {e}")
        time.sleep(5)

# メイン実行
try:
    main()
except Exception as e:
    debug_print(f"致命的エラー: {e}")
