import time

# 状態ファイルのパス
STATE_FILE = "script_states.txt"

def load_script_states():
    """ファイルから実行状態を読み込む"""
    try:
        with open(STATE_FILE, "r") as f:
            states = {}
            for line in f:
                path, interval, last_run = line.strip().split(",")
                states[path] = {
                    "interval": int(interval),
                    "last_run": float(last_run)
                }
            return states
    except:
        # ファイルが存在しない、または読み込みエラーの場合はデフォルト値を返す
        return {
            "/remote_code/01.send_to_ss.py": {"interval": 900, "last_run": 0},  # 15分
            "/remote_code/02.send_to_ss.py": {"interval": 180, "last_run": 0},  # 3分
        }

def save_script_states(states):
    """実行状態をファイルに保存"""
    try:
        with open(STATE_FILE, "w") as f:
            for path, state in states.items():
                f.write(f"{path},{state['interval']},{state['last_run']}\n")
    except Exception as e:
        print(f"Error saving states: {e}")

def execute_script(script_path, wlan):
    """スクリプトを直接実行"""
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
        print(f"Last run: {state['last_run']}, Interval: {state['interval']}")
        
        # 実行間隔を満たしているか確認
        if now - state['last_run'] >= state['interval']:
            print(f"Executing script: {script_path}")
            if execute_script(script_path, wlan):
                state['last_run'] = now  # 実行時刻を更新
                save_script_states(script_states)  # 状態を保存
                print(f"Successfully executed and updated last_run time for {script_path}")
            else:
                print(f"Failed to execute {script_path}")
        else:
            remaining_time = state['interval'] - (now - state['last_run'])
            print(f"Skipping {script_path} - not yet time to run. Remaining time: {remaining_time:.2f} seconds")

if __name__ == "__main__":
    wlan = None  # wlanは実際の環境で設定
    run(wlan)
