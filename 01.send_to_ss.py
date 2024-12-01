from machine import Pin, I2C
import network
import time
import urequests
import gc
from bme280 import BME280

# デバッグモード
DEBUG = True

# LED設定
led = Pin("LED", Pin.OUT)

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

def debug_print(*args):
    if DEBUG:
        print("DEBUG:", *args)

def connect_wifi():
    """Wi-Fi接続を確立"""
    # 既に接続されている場合はスキップ
    if wlan.isconnected():
        debug_print("Wi-Fi already connected.")
        return True, wlan.config("essid"), wlan

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
                    return True, wifi_setting["ssid"], wlan
                time.sleep(1)
        except Exception as e:
            debug_print(f"接続エラー: {e}")

    led.value(0)
    return False, None, None


def try_send_data():
    response = None
    try:
        gc.collect()
        connected, ssid, wlan = connect_wifi()
        if not connected:
            return False

        # BME280センサー初期化と読み取り
        i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
        try:
            debug_print("Initializing BME280...")
            sensor = BME280(i2c=i2c)
            debug_print("BME280 initialized successfully.")
            
            # センサーからデータを取得
            temp, press, hum = sensor.read_compensated_data()
            temperature = temp / 100.0  # 温度: °C
            pressure = press / 25600.0  # 気圧: hPa
            humidity = hum / 1024.0  # 湿度: %
            
            debug_print(f"温度: {temperature:.1f}°C")
            debug_print(f"気圧: {pressure:.1f}hPa")
            debug_print(f"湿度: {humidity:.1f}%")
        except Exception as e:
            debug_print(f"Error initializing or reading from BME280: {e}")
            return False

        # データ作成
        signal_strength = wlan.status('rssi') if wlan else None
        data = {
            "device_id": "PicoW-01",
            "ip_address": wlan.ifconfig()[0],
            "wifi_ssid": ssid,
            "mac_address": ":".join(["{:02x}".format(b) for b in wlan.config('mac')]),
            "memory_free": gc.mem_free(),
            "signal_strength": signal_strength,
            "temperature": temperature,
            "pressure": pressure,
            "humidity": humidity,
            "timestamp": time.time()
        }
        
        # データ送信
        response = urequests.post(
            ENDPOINT,
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        success = response.status_code in [200, 400, 405]
        if response:
            response.close()
        return success
            
    except Exception as e:
        debug_print(f"エラー: {e}")
        return False
        
    finally:
        if response:
            response.close()
        if wlan:
            wlan.active(False)
        led.value(0)
        gc.collect()


def send_data_with_retry():
    for attempt in range(MAX_RETRIES):
        if try_send_data():
            return True
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    return False

def main():
    debug_print("測定開始")
    
    while True:
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
            
            time.sleep(SEND_INTERVAL)
            
        except Exception as e:
            debug_print(f"メインループエラー: {e}")
            time.sleep(5)

try:
    main()
except Exception as e:
    debug_print(f"致命的エラー: {e}")
