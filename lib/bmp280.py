from machine import Pin, I2C

# BME280 default address.
BME280_I2CADDR = 0x76

# Operating Modes
BME280_OSAMPLE_1 = 1
BME280_OSAMPLE_2 = 2
BME280_OSAMPLE_4 = 3
BME280_OSAMPLE_8 = 4
BME280_OSAMPLE_16 = 5

BME280_REGISTER_CONTROL_HUM = 0xF2
BME280_REGISTER_STATUS = 0xF3
BME280_REGISTER_CONTROL = 0xF4

class BMP280:

    def __init__(self,
                 i2c,
                 mode=BME280_OSAMPLE_1,
                 address=BME280_I2CADDR,
                 **kwargs):
        self.i2c = i2c
        self.address = address
        self.mode = mode
        # Load calibration values.
        self._load_calibration()
        self._data = bytearray(8)
        ctrl = self.mode << 5 | self.mode << 2 | 1
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL,
                            bytes([ctrl]))
        self.t_fine = 0

    def _load_calibration(self):
        # Read calibration values
        cal = self.i2c.readfrom_mem(self.address, 0x88, 24)
        self.dig_T1 = cal[0] | cal[1] << 8
        self.dig_T2 = cal[2] | cal[3] << 8
        if self.dig_T2 & (1 << 15):
            self.dig_T2 = -(self.dig_T2 & ~(1 << 15))
        self.dig_T3 = cal[4] | cal[5] << 8
        if self.dig_T3 & (1 << 15):
            self.dig_T3 = -(self.dig_T3 & ~(1 << 15))
        self.dig_P1 = cal[6] | cal[7] << 8
        self.dig_P2 = cal[8] | cal[9] << 8
        if self.dig_P2 & (1 << 15):
            self.dig_P2 = -(self.dig_P2 & ~(1 << 15))
        self.dig_P3 = cal[10] | cal[11] << 8
        if self.dig_P3 & (1 << 15):
            self.dig_P3 = -(self.dig_P3 & ~(1 << 15))
        self.dig_P4 = cal[12] | cal[13] << 8
        if self.dig_P4 & (1 << 15):
            self.dig_P4 = -(self.dig_P4 & ~(1 << 15))
        self.dig_P5 = cal[14] | cal[15] << 8
        if self.dig_P5 & (1 << 15):
            self.dig_P5 = -(self.dig_P5 & ~(1 << 15))
        self.dig_P6 = cal[16] | cal[17] << 8
        if self.dig_P6 & (1 << 15):
            self.dig_P6 = -(self.dig_P6 & ~(1 << 15))
        self.dig_P7 = cal[18] | cal[19] << 8
        if self.dig_P7 & (1 << 15):
            self.dig_P7 = -(self.dig_P7 & ~(1 << 15))
        self.dig_P8 = cal[20] | cal[21] << 8
        if self.dig_P8 & (1 << 15):
            self.dig_P8 = -(self.dig_P8 & ~(1 << 15))
        self.dig_P9 = cal[22] | cal[23] << 8
        if self.dig_P9 & (1 << 15):
            self.dig_P9 = -(self.dig_P9 & ~(1 << 15))

    def read_raw_data(self):
        """Reads the raw (uncompensated) data from the sensor."""
        self.i2c.readfrom_mem_into(self.address, 0xF7, self._data)
        raw_p = ((self._data[0] << 16) | (self._data[1] << 8) | self._data[2]) >> 4
        raw_t = ((self._data[3] << 16) | (self._data[4] << 8) | self._data[5]) >> 4
        return (raw_t, raw_p)

    def read_compensated_data(self):
        """Returns (temperature, pressure) as a tuple."""
        raw_t, raw_p = self.read_raw_data()

        # Temperature
        var1 = ((raw_t >> 3) - (self.dig_T1 << 1)) * self.dig_T2 >> 11
        var2 = (((((raw_t >> 4) - self.dig_T1) *
                  ((raw_t >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        self.t_fine = var1 + var2
        temp = (self.t_fine * 5 + 128) >> 8

        # Pressure
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = ((var1 * var1 * self.dig_P3) >> 8) + ((var1 * self.dig_P2) << 12)
        var1 = (((1 << 47) + var1) * self.dig_P1) >> 33
        if var1 == 0:
            pressure = 0
        else:
            p = 1048576 - raw_p
            p = (((p << 31) - var2) * 3125) // var1
            var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
            var2 = (self.dig_P8 * p) >> 19
            pressure = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)

        return (temp / 100, pressure / 256)

    @property
    def temperature(self):
        """Returns the temperature in degrees celsius."""
        t, _ = self.read_compensated_data()
        return t

    @property
    def pressure(self):
        """Returns the pressure in hectopascals."""
        _, p = self.read_compensated_data()
        return p