import urequests
import gc
import network
from get_bmp280 import BMP280Sensor  # 追加

# GASエンドポイント
ENDPOINT = "https://script.google.com/macros/s/AKfycbztdwfhufixP7Rd2Xs2UgaymT5IwNn294LgEB2q7gX1dyhR1i0FSw4X0RpW5NO1skM0/exec"

def send_data():
    # BMP280センサーのインスタンス作成
    bmp_sensor = BMP280Sensor()
    # センサーデータ取得
    sensor_data = bmp_sensor.get_measurements()
    
    # Wi-Fi情報を取得
    wlan = network.WLAN(network.STA_IF)
    ip_address = wlan.ifconfig()[0]
    ssid = wlan.config('ssid')
    mac = ":".join("{:02x}".format(b) for b in wlan.config('mac'))
    
    # 送信データの作成
    data = {
        "device_id": "PicoW-01",
        "ip_address": ip_address,
        "wifi_ssid": ssid,
        "mac_address": mac,
        "memory_free": gc.mem_free(),
        "signal_strength": -30,
        "temperature": sensor_data["temperature"],  # 追加
        "pressure": sensor_data["pressure"]         # 追加
    }
    
    headers = {'Content-Type': 'application/json'}
    try:
        response = urequests.post(ENDPOINT, json=data, headers=headers)
        print("Response:", response.status_code, response.text)
        response.close()
    except Exception as e:
        print("Failed to send data:", e)