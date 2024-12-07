import os
import sys
import time
import machine

REMOTE_CODE_PATH = "/remote_code"

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

def execute_scripts():
    """remote_code 配下のスクリプトを動的にロードして実行"""
    try:
        # remote_code 配下のスクリプトを取得
        scripts = [
            f for f in os.listdir(REMOTE_CODE_PATH)
            if f.endswith("_script.py")  # スクリプト命名規則に基づく
        ]

        if not scripts:
            print("No scripts found to execute.")
            return

        for script in scripts:
            try:
                script_path = f"{REMOTE_CODE_PATH}/{script}"
                print(f"Executing script: {script_path}")

                # スクリプトを読み込んで実行
                with open(script_path, "r") as file:
                    code = file.read()
                    exec(code)  # スクリプトを実行

            except Exception as e:
                print(f"Error executing script {script}: {e}")

    except Exception as e:
        print(f"Error in execute_scripts: {e}")

if __name__ == "__main__":
    execute_scripts()

