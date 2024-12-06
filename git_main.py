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


# グローバル変数
ntp_synced = False
system_time_offset = 0

def sync_ntp_time(logger):
    global ntp_synced, system_time_offset
    try:
        logger.log("NTP時刻同期を開始...")
        ntptime.host = "216.239.35.0"
        ntptime.timeout = 5
        ntptime.settime()
        system_time_offset = 0
        ntp_synced = True
        t = time.localtime(time.time() + 9 * 60 * 60)
        logger.log(f"NTP同期成功: {t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} (JST)")
        return True
    except Exception as e:
        logger.log(f"NTP同期失敗: {str(e)}")
        ntp_synced = False
        system_time_offset += 5 * 60
        return False

def get_current_time():
    """現在の時刻（NTP同期状態に基づく）"""
    if ntp_synced:
        return time.time()
    else:
        # システム時刻にオフセットを加えて推定時刻を返す
        return time.time() + system_time_offset


def format_time(timestamp):
    """UNIXタイムスタンプを読みやすいUTC形式に変換"""
    try:
        t = time.localtime(float(timestamp))  # floatとして処理
        return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    except Exception as e:
        return f"Invalid time ({timestamp}): {str(e)}"


def get_current_jst_time():
    """現在の日本時間を取得（UNIXタイム形式）"""
    return time.time() + 9 * 60 * 60  # UTC + 9時間

def format_jst_time(timestamp):
    """UNIXタイムスタンプを日本時間のyyyy/mm/dd hh:mm:ss形式に変換（表示用）"""
    timestamp = float(timestamp)  # 確実にfloatに変換
    t = time.localtime(timestamp + 9 * 60 * 60)  # JST変換
    return "{:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(*t[:6])

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
    print(f"Using default states with current UTC time: {format_time(current_time)}")
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
                    if last_run_str.lower() == "none":
                        last_run = None
                    else:
                        # UTCエポック秒としてパース
                        last_run = float(last_run_str)
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
                # UTCエポック秒をそのまま文字列化
                last_run_str = str(state['last_run']) if state['last_run'] is not None else "None"
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
        current_time = time.time()  # UTC
        formatted_time = format_time(current_time)  # UTC時刻を表示用フォーマット
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
def execute_script(script_path, wlan, logger):  # loggerパラメータを追加
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
                'logger': logger  # loggerを追加
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
    global ntp_synced, system_time_offset
    logger.log("\n=== Starting main loop ===")
    
    # デバッグ出力を追加
    def debug_value(val, name=""):
        logger.log(f"DEBUG {name}: type={type(val)}, value={val}")
    
    script_states = load_script_states()
    now = time.time()
    debug_value(now, "now")

    ntp_synced = sync_ntp_time(logger)
    logger.log(f"NTP同期状態: {'成功' if ntp_synced else '失敗'}")

    for script_path, state in script_states.items():
        logger.log(f"\nProcessing script: {script_path}")
        debug_value(state, "state")
        
        last_run = state.get("last_run")
        debug_value(last_run, "last_run")
        
        if last_run is None:
            logger.log(f"警告: {script_path} の last_run が未設定です。現在のUTC時刻を使用します。")
            last_run = now
            state["last_run"] = now
            debug_value(last_run, "updated last_run")

        time_since_last_run = now - last_run
        debug_value(time_since_last_run, "time_since_last_run")
        
        should_run = (not state["last_status"]) or (time_since_last_run >= state["interval"])
        debug_value(should_run, "should_run")
        
        try:
            logger.log(f"Last run (JST): {format_jst_time(last_run)}")
        except Exception as e:
            logger.log(f"Error in format_jst_time: {str(e)}")
            logger.log(f"Input value: {last_run} (type: {type(last_run)})")

# メインループの実行
if __name__ == "__main__":
    class DummyLogger:
        def log(self, msg):
            print(msg)
    wlan = None
    logger = DummyLogger()
    run(wlan, logger)
