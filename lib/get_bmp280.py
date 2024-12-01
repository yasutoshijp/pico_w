from machine import I2C, Pin
import bmp280

class BMP280Sensor:
    def __init__(self):
        # I2Cの初期化
        self.i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=10000)
        # BMP280の初期化
        self.bmp = bmp280.BMP280(self.i2c)
    
    def get_measurements(self):
        """温度と気圧の測定値を返す"""
        try:
            temp = self.bmp.temperature
            pressure = self.pressure = self.bmp.pressure / 100  # hPaに変換
            return {
                "temperature": round(temp, 1),
                "pressure": round(pressure, 1)
            }
        except Exception as e:
            print("測定エラー:", e)
            return {
                "temperature": None,
                "pressure": None
            }