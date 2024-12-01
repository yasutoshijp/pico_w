from machine import Pin, I2C
import time

class BME280:
    def __init__(self, i2c, addr=0x76):
        self.i2c = i2c
        self.addr = addr
        
        # リセット
        self.i2c.writeto_mem(self.addr, 0xE0, b'\xB6')
        time.sleep(0.2)
        
        # キャリブレーションデータ読み取り
        self.cal1 = self.i2c.readfrom_mem(self.addr, 0x88, 24)
        self.cal2 = self.i2c.readfrom_mem(self.addr, 0xA1, 1)
        self.cal3 = self.i2c.readfrom_mem(self.addr, 0xE1, 7)
        
        # センサー設定
        self.i2c.writeto_mem(self.addr, 0xF2, b'\x01')  # 湿度 x1
        self.i2c.writeto_mem(self.addr, 0xF4, b'\x27')  # 温度 x1, 気圧 x1, ノーマルモード
        time.sleep(0.1)
        
    def read_raw(self):
        """生データの読み取り"""
        data = self.i2c.readfrom_mem(self.addr, 0xF7, 8)
        pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        hum_raw = (data[6] << 8) | data[7]
        return pres_raw, temp_raw, hum_raw
    
    def get_signed_short(self, data, index):
        """符号付き16ビット整数の取得"""
        val = data[index + 1] << 8 | data[index]
        return val if val < 32768 else val - 65536
    
    def get_unsigned_short(self, data, index):
        """符号なし16ビット整数の取得"""
        return data[index + 1] << 8 | data[index]

    def read_compensated_data(self):
        # 温度補正係数
        dig_T1 = self.get_unsigned_short(self.cal1, 0)
        dig_T2 = self.get_signed_short(self.cal1, 2)
        dig_T3 = self.get_signed_short(self.cal1, 4)
        
        # 気圧補正係数
        dig_P1 = self.get_unsigned_short(self.cal1, 6)
        dig_P2 = self.get_signed_short(self.cal1, 8)
        dig_P3 = self.get_signed_short(self.cal1, 10)
        dig_P4 = self.get_signed_short(self.cal1, 12)
        dig_P5 = self.get_signed_short(self.cal1, 14)
        dig_P6 = self.get_signed_short(self.cal1, 16)
        dig_P7 = self.get_signed_short(self.cal1, 18)
        dig_P8 = self.get_signed_short(self.cal1, 20)
        dig_P9 = self.get_signed_short(self.cal1, 22)

        # 湿度補正係数
        dig_H1 = self.cal2[0]
        dig_H2 = self.get_signed_short(self.cal3, 0)
        dig_H3 = self.cal3[2]
        dig_H4 = (self.cal3[3] << 4) | (self.cal3[4] & 0x0F)
        dig_H5 = (self.cal3[4] >> 4) | (self.cal3[5] << 4)
        dig_H6 = self.cal3[6]
        if dig_H6 > 127:
            dig_H6 -= 256
        
        # 生データ読み取り
        pres_raw, temp_raw, hum_raw = self.read_raw()
        
        # 温度計算
        var1 = (((temp_raw >> 3) - (dig_T1 << 1)) * dig_T2) >> 11
        var2 = (((((temp_raw >> 4) - dig_T1) * ((temp_raw >> 4) - dig_T1)) >> 12) * dig_T3) >> 14
        t_fine = var1 + var2
        temperature = (t_fine * 5 + 128) >> 8
        temperature = temperature / 100.0

        # 気圧計算
        var1 = t_fine - 128000
        var2 = var1 * var1 * dig_P6
        var2 = var2 + ((var1 * dig_P5) << 17)
        var2 = var2 + (dig_P4 << 35)
        var1 = ((var1 * var1 * dig_P3) >> 8) + ((var1 * dig_P2) << 12)
        var1 = (((1 << 47) + var1)) * dig_P1 >> 33

        if var1 == 0:
            pressure = 0
        else:
            pressure = 1048576 - pres_raw
            pressure = (((pressure << 31) - var2) * 3125) // var1
            var1 = (dig_P9 * (pressure >> 13) * (pressure >> 13)) >> 25
            var2 = (dig_P8 * pressure) >> 19
            pressure = ((pressure + var1 + var2) >> 8) + (dig_P7 << 4)
            pressure = float(pressure) / 256.0

        # 湿度計算
        v_x1 = t_fine - 76800
        v_x1 = (((((hum_raw << 14) - (dig_H4 << 20) - (dig_H5 * v_x1)) + 16384) >> 15) *
                (((((((v_x1 * dig_H6) >> 10) * (((v_x1 * dig_H3) >> 11) + 32768)) >> 10) + 2097152) *
                 dig_H2 + 8192) >> 14))
        v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) * dig_H1) >> 4)
        v_x1 = max(0, min(v_x1, 419430400))
        humidity = v_x1 >> 12
        humidity = humidity / 1024.0

        return temperature, pressure/100.0, humidity

    def read(self):
        return self.read_compensated_data()