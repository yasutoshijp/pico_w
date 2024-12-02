import time
import json

# 状態ファイルとログファイルのパス
STATE_FILE = "script_states.txt"
LOG_FILE = "script_logs.txt"

def load_script_states():
    """ファイルから実行状態を読み込む"""
    try:
        with open(STATE_FILE, "r") as f:
            states = {}
            for line in f:
                path, interval, last_run, last_status = line.strip().split(",")
                states[path] = {
                    "interval": int(interval),
                    "last_run": float(last_run),
                    "last_status": last_status == "True"  # "True"/"False" を bool に変換
                }
            return states
    except:
        # デフォルト値を返す
        return {
            "/remote_code/01.send_to_ss.py": {"interval": 900, "last_run": 0, "last_status": True},  # 15分
            "/remote_code/02.send_to_ss.py": {"interval": 180, "last_run": 0, "last_status": True},  # 3分
        }

def save_script_states(states):
    """実行状態をファイルに保存"""
    try:
        with open(STATE_FILE, "w") as f:
            for path, state in states.items():
                f.write(f"{path},{state['interval']},{state['last_run']},{state['last_status']}\n")
    except Exception as e:
        print(f"Error saving states: {e}")

def log_execution(script_path, status, message=""):
    """スクリプトの実行ログを記録"""
    try:
        timestamp = time.localtime()
        formatted_time = f"{timestamp[0]:04d}-{timestamp[1]:02d}-{timestamp[2]:02d} {timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"
        
        log_entry = f"[{formatted_time}] {script_path} - Status: {'Success' if status else 'Failed'}"
        if message:
            log_entry += f" - {message}"
        
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Error writing log: {e}")

def execute_script(script_path, wlan):
    """スクリプトを実行"""
    try:
        print(f"Attempting to execute script: {script_path}")
        with open(script_path, "r") as script_file:
            code = script_file.read()
            # グローバルスコープにwlanを追加
            global_scope = globals()
            global_scope['wlan'] = wlan
            exec(code, global_scope)
        print(f"Executed successfully: {script_path}")
        return True
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        return False

def run(wlan):
    print("Running git_main.py...")

    # 状態をファイルから読み込む
    script_states = load_script_states()
    
    now = time.time()
    print(f"Current time: {now}")
    
    for script_path, state in script_states.items():
        print(f"Checking script: {script_path}")
        print(f"Last run: {state['last_run']}, Interval: {state['interval']}, Last status: {state['last_status']}")
        
        # 前回失敗時または実行間隔を超えている場合に実行
        if not state['last_status'] or now - state['last_run'] >= state['interval']:
            print(f"Executing script: {script_path}")
            execution_success = execute_script(script_path, wlan)
            
            # 実行結果を記録
            state['last_status'] = execution_success
            if execution_success:
                state['last_run'] = now
                log_execution(script_path, True)
            else:
                log_execution(script_path, False, "Execution failed")
            
            save_script_states(script_states)
            print(f"Updated state for {script_path}: Success={execution_success}")
        else:
            remaining_time = state['interval'] - (now - state['last_run'])
            message = f"Skipping - Next run in {remaining_time:.2f} seconds"
            print(f"Skipping {script_path} - {message}")
            log_execution(script_path, True, message)

if __name__ == "__main__":
    wlan = None  # wlanは実際の環境で設定
    run(wlan)
