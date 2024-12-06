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

# グローバル変数を明示
ntp_synced = False

def sync_ntp_time(logger):
    global ntp_synced
    try:
        logger.log("NTP時刻同期を開始...")
        ntptime.timeout = 5
        ntptime.settime()
        ntp_synced = True
        t = time.localtime()
        logger.log(f"NTP同期成功: {t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} (JST)")
        return True
    except Exception as e:
        logger.log(f"NTP同期失敗: {e}")
        ntp_synced = False
        return False


def get_current_jst_time():
    """現在の日本時間を取得（UNIXタイム形式）"""
    return time.time() + 9 * 60 * 60  # UTC + 9時間

def format_jst_time(timestamp):
    """UNIXタイムスタンプを日本時間のyyyy/mm/dd hh:mm:ss形式に変換"""
    t = time.localtime(timestamp + 9 * 60 * 60)  # JST（UTC+9）に変換
    return "{:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])

def parse_jst_time(formatted_time):
    """日本時間のyyyy/mm/dd hh:mm:ss形式をUNIXタイムスタンプに変換"""
    try:
        # フォーマットを分解
        year, month, day, hour, minute, second = map(int, formatted_time.replace("/", " ").replace(":", " ").split())
        # 日本時間のローカルタイムをUNIXタイムに変換（UTC補正を引く）
        return time.mktime((year, month, day, hour, minute, second, 0, 0)) - 9 * 60 * 60
    except Exception as e:
        print(f"Error parsing time: {formatted_time}, {e}")
        return None
    
def format_time(timestamp):
    """UNIXタイムスタンプを読みやすい形式に変換"""
    try:
        t = time.localtime(int(timestamp))
        return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    except Exception as e:
        return f"Invalid time ({timestamp})"

def format_duration(seconds):
    """秒数を読みやすい時間表記に変換"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{int(minutes)}分{int(remaining_seconds)}秒"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{int(hours)}時間{int(remaining_minutes)}分"

def is_valid_time():
    """システム時刻が有効かチェック（2022年以降を有効とする）"""
    try:
        return time.localtime()[0] >= 2022
    except:
        return False

# BME280クラスをグローバルに定義
try:
    with open('/remote_code/lib/bme280.py', 'r') as f:
        bme280_code = f.read()
        # モジュールの名前空間を作成
        module_namespace = {
            '__name__': 'bme280',
            'machine': machine,
            'time': time
        }
        exec(bme280_code, module_namespace)
        # グローバル空間にBME280クラスを追加
        BME280 = module_namespace['BME280']
        sys.modules['bme280'] = type('Module', (), {'BME280': BME280})
    print("BME280 module loaded successfully")
except Exception as e:
    print(f"Error loading BME280 module: {e}")

# 状態ファイルとログファイルのパス
STATE_FILE = "script_states.txt"
LOG_FILE = "script_logs.txt"

def get_default_states():
    """デフォルトの状態を返す（last_runはUTCで記録）"""
    current_time = time.time()  # UTC
    default_states = {
        "/remote_code/01.send_to_ss.py": {"interval": 900, "last_run": current_time, "last_status": True},  # 15分
        "/remote_code/02.send_to_ss.py": {"interval": 180, "last_run": current_time, "last_status": True},  # 3分
    }
    print(f"Using default states with current UTC time: {format_utc_time(current_time)}")
    return default_states


def load_script_states():
    print(f"\nChecking if {STATE_FILE} exists...")
    try:
        os.stat(STATE_FILE)
        print(f"{STATE_FILE} found, loading states...")
        with open(STATE_FILE, "r") as f:
            lines = f.readlines()
            states = {}
            for line in lines:
                parts = line.strip().split(",")
                if len(parts) != 4:
                    print(f"Invalid line format: {line.strip()}")
                    continue
                path, interval_str, last_run_str, status_str = parts
                try:
                    interval = int(interval_str)
                    last_run = parse_jst_time(last_run_str) if last_run_str != "None" else None
                    status = status_str.lower() == "true"
                    states[path] = {"interval": interval, "last_run": last_run, "last_status": status}
                except Exception as e:
                    print(f"Error parsing line: {line.strip()} ({e})")
            return states
    except OSError:
        print(f"{STATE_FILE} not found, using default states")
        return get_default_states()


def save_script_states(states):
    try:
        temp_file = STATE_FILE + ".tmp"
        with open(temp_file, "w") as f:
            for path, state in states.items():
                last_run_str = format_jst_time(state['last_run']) if state['last_run'] else "None"
                line = f"{path},{state['interval']},{last_run_str},{state['last_status']}\n"
                print(f"★★Writing line: {line.strip()}")  # 確認用出力
                f.write(line)
        os.rename(temp_file, STATE_FILE)
        print(f"★★States saved successfully to {STATE_FILE}")  # 確認用出力
    except Exception as e:
        print(f"Error saving states: {e}")


def log_execution(script_path, status, message=""):
    """スクリプトの実行ログを記録"""
    try:
        current_time = time.time()
        formatted_time = format_time(current_time)
        
        log_entry = f"[{formatted_time}] {script_path} - Status: {'Success' if status else 'Failed'}"
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
                'BME280': BME280,
                'bme280': sys.modules['bme280']
            }
            
            print(f"Starting execution with globals: {list(globals_dict.keys())}")
            exec(code, globals_dict)
            
        print(f"Successfully executed: {script_path}")
        return True
        
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        sys.print_exception(e)
        return False

def run(wlan):
    """メインの実行関数"""
    print("\n=== Starting main loop ===")
    script_states = load_script_states()
    now = time.time()  # 現在時刻（UTC）

    # NTP同期を試行
    ntp_synced = sync_ntp_time(logger)
    print(f"NTP同期状態: {'成功' if ntp_synced else '失敗'}")

    for script_path, state in script_states.items():
        print(f"\nProcessing script: {script_path}")
        
        # 時刻チェックをスキップする場合
        if not ntp_synced:
            print(f"警告: NTP同期に失敗したため、時刻チェックをスキップしてスクリプトを実行します。")
            execute_script(script_path, wlan)
            continue

        # 時刻チェックを行う場合
        last_run = state.get("last_run")
        if last_run is None:
            print(f"警告: {script_path} の last_run が未設定です。現在時刻を代わりに使用します。")
            last_run = now
        
        time_since_last_run = now - last_run
        should_run = (not state["last_status"]) or (time_since_last_run >= state["interval"])
        
        print(f"Last run (JST): {format_jst_time(last_run)}")
        print(f"Time since last run: {format_duration(time_since_last_run)}")
        print(f"Should run: {should_run}")

        if should_run:
            print(f"実行中: {script_path}")
            execution_success = execute_script(script_path, wlan)
            state["last_status"] = execution_success
            state["last_run"] = now  # 実行後の更新
            print(f"★Updated state: {state}")  # 確認用出力
            print(f"スクリプト実行結果: {execution_success}")
        else:
            print(f"スクリプト {script_path} をスキップします")

    # 状態を保存
    save_script_states(script_states)
    print("\n=== Completed main loop ===")

if __name__ == "__main__":
    wlan = None  # wlanは実際の環境で設定
    run(wlan)


