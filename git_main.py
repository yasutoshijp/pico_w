import time

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
    except FileNotFoundError:
        print(f"Script file not found: {script_path}")
        return False
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        return False

def run(wlan):
    print("Running git_main.py...")

    # スクリプトの実行状態を保持する辞書
    global script_states
    if 'script_states' not in globals():
        script_states = {
            "/remote_code/01.send_to_ss.py": {"interval": 900, "last_run": 0},  # 15分
            "/remote_code/02.send_to_ss.py": {"interval": 180, "last_run": 0},  # 3分
        }

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
                print(f"Successfully executed and updated last_run time for {script_path}")
            else:
                print(f"Failed to execute {script_path}")
        else:
            remaining_time = state['interval'] - (now - state['last_run'])
            print(f"Skipping {script_path} - not yet time to run. Remaining time: {remaining_time:.2f} seconds")

# 例: wlanオブジェクトを渡して呼び出し
if __name__ == "__main__":
    wlan = None  # wlanは実際の環境で設定
    run(wlan)
