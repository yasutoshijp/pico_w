import sys
import time
import json
import os
import machine
import gc
import network
import urequests
import io
import ubinascii
import ntptime

# BME280クラスをグローバルに定義
try:
    with open('/remote_code/lib/bme280.py', 'r') as f:
        bme280_code = f.read()
        module_namespace = {
            '__name__': 'bme280',
            'machine': machine,
            'time': time
        }
        exec(bme280_code, module_namespace)
        BME280 = module_namespace['BME280']
        sys.modules['bme280'] = type('Module', (), {'BME280': BME280})
    print("BME280 module loaded successfully")
except Exception as e:
    print(f"Error loading BME280 module: {e}")

def execute_script(script_path, wlan, logger):
    """スクリプトを実行"""
    logger.log(f"\n=== Executing {script_path} ===")
    try:
        logger.log("Reading script file...")
        with open(script_path, "r") as script_file:
            code = script_file.read()
            logger.log(f"Loaded {len(code)} bytes of code")
            
            globals_dict = {
                'wlan': wlan,
                'machine': machine,
                'Pin': machine.Pin,
                'I2C': machine.I2C,
                'gc': gc,
                'network': network,
                'time': time,
                'os': os,
                'urequests': urequests,
                'json': json,
                'io': io,
                'sys': sys,
                'ubinascii': ubinascii,
                'BME280': BME280,
                'bme280': sys.modules['bme280'],
                'logger': logger
            }
            
            logger.log(f"Starting execution with globals: {list(globals_dict.keys())}")
            exec(code, globals_dict)
            
        logger.log(f"Successfully executed: {script_path}")
        return True
        
    except Exception as e:
        logger.log(f"Error executing script {script_path}: {e}")
        sys.print_exception(e)
        return False

def run(wlan, logger):
    """メイン関数"""
    logger.log("\n=== Starting main execution ===")
    
    scripts = [
        "/remote_code/01.send_to_ss.py",
        "/remote_code/02.send_to_ss.py"
    ]
    
    for script_path in scripts:
        execute_script(script_path, wlan, logger)
        time.sleep(5)  # 実行間隔を空ける
    
    logger.log("=== Completed all executions ===")

if __name__ == "__main__":
    class DummyLogger:
        def log(self, msg):
            print(msg)
    wlan = None
    logger = DummyLogger()
    run(wlan, logger)
