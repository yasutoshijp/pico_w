def execute_script(script_path, wlan):
    """スクリプトを直接実行っっっっっっっっっっっっっっっっっっっっっっっっｚ"""
    
    try:
        print(f"Attempting to execute script: {script_path}")
        with open(script_path, "r") as script_file:
            code = script_file.read()
            # ローカルスコープで実行
            local_scope = {"wlan": wlan}
            exec(code, {}, local_scope)  # ローカルスコープにオブジェクトを渡す
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

    # 実行するスクリプトリスト
    scripts = [
        {"path": "/remote_code/01.send_to_ss.py", "interval": 120, "last_run": 0},
        {"path": "/remote_code/02.send_to_ss.py", "interval": 180, "last_run": 0},
    ]

    now = time.time()
    print(f"Current time: {now}")
    for script in scripts:
        print(f"Checking script: {script['path']}")
        print(f"Last run: {script['last_run']}, Interval: {script['interval']}")
        if now - script["last_run"] >= script["interval"]:
            print(f"Condition met for: {script['path']}")
            print(f"Attempting to execute: {script['path']}")
            success = execute_script(script["path"], wlan)
            if success:
                print(f"{script['path']} executed successfully.")
            else:
                print(f"Error executing {script['path']}.")
            script["last_run"] = now
        else:
            print(f"Condition not met for: {script['path']}")
