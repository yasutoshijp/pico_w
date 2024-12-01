from machine import Pin, I2C
import time
from bme280 import BME280

# I2Cの初期化
i2c = I2C(0, scl=Pin(1), sda=Pin(0))

# BME280の初期化
sensor = BME280(i2c)

# メインループ
while True:
    try:
        # センサー値の読み取り
        temperature, pressure, humidity = sensor.read()
        
        # 結果の表示
        print(f"Temperature: {temperature:.1f}°C")
        print(f"Pressure: {pressure:.1f}hPa")
        print(f"Humidity: {humidity:.1f}%")
        print("-" * 20)
        
        # 10秒待機
        time.sleep(10)
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)