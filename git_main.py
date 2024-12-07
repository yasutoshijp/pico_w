import sys
import time
import machine

# BME280モジュールの読み込み
try:
    with open('/remote_code/lib/bme280.py', 'r') as f:
        bme280_code = f.read()
        module_namespace = {'__name__': 'bme280', 'machine': machine, 'time': time}
        exec(bme280_code, module_namespace)
        BME280 = module_namespace['BME280']
        sys.modules['bme280'] = type('Module', (), {'BME280': BME280})
    print("BME280 module loaded successfully")
except Exception as e:
    print(f"Error loading BME280 module: {e}")

def execute_script(script_path):
    """スクリプトを実行"""
    print(f"\n=== Executing {script_path} ===")
    try:
        with open(script_path, "r") as script_file:
            code = script_file.read()
            globals_dict = {
                'machine': machine,
                'time': time,
                'BME280': BME280,
            }
            exec(code, globals_dict)
        print(f"Successfully executed: {script_path}")
        return True
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        return False

def run():
    """メイン関数"""
    scripts = [
        "/remote_code/01.send_to_ss.py",
    ]
    
    for script_path in scripts:
        execute_script(script_path)
        time.sleep(2)

if __name__ == "__main__":
    run()
