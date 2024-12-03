# git_main.py
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

def get_default_states():
    """デフォルトの状態を返す"""
    default_states = {
        "/remote_code/01.send_to_ss.py": {"interval": 900, "last_run": 0, "last_status": True},  # 15分
        "/remote_code/02.send_to_ss.py": {"interval": 180, "last_run": 0, "last_status": True},  # 3分
    }
    print(f"Using default states: {default_states}")
    return default_states

def load_script_states():
    """ファイルから実行状態を読み込む"""
    print(f"\nChecking if {STATE_FILE} exists...")
    try:
        # ファイルが存在するか確認
        os.stat(STATE_FILE)
        print(f"{STATE_FILE} found, loading states...")
        
        states = {}
        try:
            with open(STATE_FILE, "r") as f:
                lines = f.readlines()  # 全行を一度に読み込む
                
                if not lines:
                    print("State file is empty, using default states")
                    return get_default_states()
                
                for line in lines:
                    try:
                        path, interval, last_run, last_status = line.strip().split(",")
                        states[path] = {
                            "interval": int(interval),
                            "last_run": float(last_run),
                            "last_status": last_status.lower() == "true"
                        }
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing line: {line.strip()}, Error: {e}")
                        continue
                
                if not states:
                    print("No valid states loaded, using default states")
                    return get_default_states()
                
                print(f"Successfully loaded states: {states}")
                return states
                
        except Exception as e:
            print(f"Error reading {STATE_FILE}: {e}")
            return get_default_states()
            
    except OSError:
        print(f"{STATE_FILE} not found, using default states")
        return get_default_states()

def save_script_states(states):
    """実行状態をファイルに保存"""
    try:
        temp_file = STATE_FILE + ".tmp"
        # まず一時ファイルに書き込む
        with open(temp_file, "w") as f:
            for path, state in states.items():
                line = f"{path},{state['interval']},{state['last_run']},{state['last_status']}\n"
                f.write(line)
        
        # 書き込みが成功したら、一時ファイルを本ファイルに rename
        try:
            os.remove(STATE_FILE)  # 既存ファイルを削除
        except OSError:
            pass  # ファイルが存在しない場合は無視
            
        os.rename(temp_file, STATE_FILE)
        print(f"Successfully saved states to {STATE_FILE}")
        
    except Exception as e:
        print(f"Error saving states: {e}")
        # エラーが発生した場合は一時ファイルを削除
        try:
            os.remove(temp_file)
        except:
            pass

def log_execution(script_path, status, message=""):
    """スクリプトの実行ログを記録"""
    try:
        t = time.localtime()
        unix_timestamp = time.time()
        formatted_time = f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
        
        log_entry = f"[{formatted_time}] ({unix_timestamp}) {script_path} - Status: {'Success' if status else 'Failed'}"
        if message:
            log_entry += f" - {message}"
        
        # 一時ファイルを使用してログを書き込む
        temp_log = LOG_FILE + ".tmp"
        with open(temp_log, "w") as f:
            f.write(log_entry + "\n")
            
        # 既存のログファイルとマージ
        try:
            with open(LOG_FILE, "r") as old_f:
                with open(temp_log, "a") as new_f:
                    new_f.write(old_f.read())
        except OSError:
            pass  # 既存ログが存在しない場合は無視
            
        os.rename(temp_log, LOG_FILE)
        print(f"Logged execution: {log_entry}")
        
    except Exception as e:
        print(f"Error writing log: {e}")
        try:
            os.remove(temp_log)
        except:
            pass

def execute_script(script_path, wlan):
    """スクリプトを実行"""
    print(f"\n=== Executing {script_path} ===")
    try:
        print(f"Reading script file...")
        with open(script_path, "r") as script_file:
            code = script_file.read()
            print(f"Loaded {len(code)} bytes of code")
            
            # グローバルスコープの準備
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
            }
            
            # BME280モジュールが利用可能な場合は追加
            try:
                from bme280 import BME280
                globals_dict['BME280'] = BME280
            except ImportError:
                print("Warning: BME280 module not available")
            
            print(f"Starting execution with globals: {list(globals_dict.keys())}")
            exec(code, globals_dict)
            
        print(f"Successfully executed: {script_path}")
        return True
        
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        sys.print_exception(e)  # 詳細なエラー情報を出力
        return False

def run(wlan):
    """メインの実行関数"""
    print("\n=== Starting git_main.py execution ===")
    print("Loading script states...")

    script_states = load_script_states()
    now = time.time()
    
    print(f"\nCurrent time: {now}")
    print(f"Current formatted time: {time.localtime()}")
    
    for script_path, state in script_states.items():
        print(f"\nProcessing script: {script_path}")
        print(f"Last run: {state['last_run']}")
        print(f"Interval: {state['interval']}")
        print(f"Last status: {state['last_status']}")
        
        try:
            time_since_last_run = now - state['last_run']
            should_run = (not state['last_status']) or (time_since_last_run >= state['interval'])
            
            if should_run:
                reason = "previous failure" if not state['last_status'] else f"interval elapsed ({time_since_last_run:.1f}s >= {state['interval']}s)"
                print(f"Executing {script_path} (reason: {reason})")
                
                # スクリプトの存在確認
                try:
                    os.stat(script_path)
                except OSError:
                    print(f"Script not found: {script_path}")
                    log_execution(script_path, False, "Script file not found")
                    continue
                
                # スクリプト実行
                execution_success = execute_script(script_path, wlan)
                
                # 状態の更新
                state['last_status'] = execution_success
                if execution_success:
                    state['last_run'] = now
                    log_execution(script_path, True, f"Executed ({reason})")
                else:
                    log_execution(script_path, False, f"Execution failed ({reason})")
                
                # 状態の保存
                save_script_states(script_states)
                print(f"Updated state for {script_path}: Success={execution_success}")
                
            else:
                remaining_time = state['interval'] - time_since_last_run
                message = f"Skipping - Next run in {remaining_time:.1f} seconds"
                print(f"Skipping {script_path} - {message}")
                log_execution(script_path, True, message)
                
        except Exception as e:
            print(f"Error processing script {script_path}: {e}")
            sys.print_exception(e)
            log_execution(script_path, False, f"Processing error: {str(e)}")
            
        print(f"Finished processing {script_path}")
        
    print("\n=== Completed git_main.py execution ===")

if __name__ == "__main__":
    wlan = None  # wlanは実際の環境で設定
    run(wlan)
