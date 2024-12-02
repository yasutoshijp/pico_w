import time
import json
import os
import machine
import gc
import network
import urequests
import sys
import io
import ubinascii
try:
    import bme280
except ImportError:
    print("Warning: BME280 module not found")

# 状態ファイルとログファイルのパス
STATE_FILE = "script_states.txt"
LOG_FILE = "script_logs.txt"

def load_script_states():
    """ファイルから実行状態を読み込む"""
    print(f"\nChecking if {STATE_FILE} exists...")
    try:
        os.stat(STATE_FILE)
        print(f"{STATE_FILE} found, loading states...")
        try:
            with open(STATE_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    print("State file is empty, using default states")
                    return get_default_states()
                    
                states = {}
                for line in f:
                    path, interval, last_run, last_status = line.strip().split(",")
                    states[path] = {
                        "interval": int(interval),
                        "last_run": float(last_run),
                        "last_status": last_status == "True"
                    }
                if not states:
                    print("No states loaded, using default states")
                    return get_default_states()
                    
                print(f"Successfully loaded states: {states}")
                return states
        except Exception as e:
            print(f"Error reading {STATE_FILE}: {e}")
            return get_default_states()
    except OSError:
        print(f"{STATE_FILE} not found, using default states")
        return get_default_states()

def get_default_states():
    """デフォルトの状態を返す"""
    default_states = {
        "/remote_code/01.send_to_ss.py": {"interval": 900, "last_run": 0, "last_status": True},  # 15分
        "/remote_code/02.send_to_ss.py": {"interval": 180, "last_run": 0, "last_status": True},  # 3分
    }
    print(f"Using default states: {default_states}")
    return default_states

def save_script_states(states):
    """実行状態をファイルに保存"""
    try:
        with open(STATE_FILE, "w") as f:
            for path, state in states.items():
                f.write(f"{path},{state['interval']},{state['last_run']},{state['last_status']}\n")
        print(f"Successfully saved states to {STATE_FILE}")
    except Exception as e:
        print(f"Error saving states: {e}")

def log_execution(script_path, status, message=""):
    """スクリプトの実行ログを記録"""
    try:
        t = time.localtime()
        unix_timestamp = time.time()
        formatted_time = f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
        
        log_entry = f"[{formatted_time}] ({unix_timestamp}) {script_path} - Status: {'Success' if status else 'Failed'}"
        if message:
            log_entry += f" - {message}"
        
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
        print(f"Logged execution: {log_entry}")
    except Exception as e:
        print(f"Error writing log: {e}")

def execute_script(script_path, wlan):
    """スクリプトを実行"""
    print(f"\n=== Executing {script_path} ===")
    try:
        print(f"Reading script file...")
        with open(script_path, "r") as script_file:
            code = script_file.read()
            print(f"Loaded {len(code)} bytes of code")
            
            # 必要なモジュールを直接インポート
            import machine
            import network
            import time
            import os
            import urequests
            import json
            import io
            import sys
            import ubinascii
            import gc
            
            try:
                from bme280 import BME280
            except ImportError:
                print("Warning: BME280 module not available")
                BME280 = None
            
            # グローバルスコープにモジュールと必要なオブジェクトを追加
            globals_dict = globals()  # 現在のグローバル名前空間を取得
            globals_dict.update({
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
                'BME280': BME280
            })
            
            print(f"Starting execution with globals: {list(globals_dict.keys())}")
            exec(code, globals_dict)
            
        print(f"Successfully executed: {script_path}")
        return True
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        return False

def run(wlan):
    print("\n=== Starting git_main.py execution ===")
    print("Loading script states...")

    # 状態をファイルから読み込む
    script_states = load_script_states()
    
    now = time.time()
    print(f"\nCurrent time: {now}")
    print(f"Current formatted time: {time.localtime()}")
    
    for script_path, state in script_states.items():
        print(f"\nProcessing script: {script_path}")
        print(f"Last run: {state['last_run']}")
        print(f"Interval: {state['interval']}")
        print(f"Last status: {state['last_status']}")
        
        # 前回失敗時または実行間隔を超えている場合に実行
        should_run = not state['last_status'] or now - state['last_run'] >= state['interval']
        if should_run:
            reason = "previous failure" if not state['last_status'] else "interval elapsed"
            print(f"Executing {script_path} (reason: {reason})")
            
            execution_success = execute_script(script_path, wlan)
            
            # 実行結果を記録
            state['last_status'] = execution_success
            if execution_success:
                state['last_run'] = now
                log_execution(script_path, True, f"Executed ({reason})")
            else:
                log_execution(script_path, False, f"Execution failed ({reason})")
            
            save_script_states(script_states)
            print(f"Updated state for {script_path}: Success={execution_success}")
        else:
            remaining_time = state['interval'] - (now - state['last_run'])
            message = f"Skipping - Next run in {remaining_time:.2f} seconds"
            print(f"Skipping {script_path} - {message}")
            log_execution(script_path, True, message)

        print(f"Finished processing {script_path}")

    print("\n=== Completed git_main.py execution ===")

if __name__ == "__main__":
    wlan = None  # wlanは実際の環境で設定
    run(wlan)
