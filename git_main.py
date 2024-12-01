def execute_script(script_path, wlan):
    """スクリプトを直接実行"""
    try:
        with open(script_path, "r") as script_file:
            code = script_file.read()
            # ローカルスコープで実行
            local_scope = {"wlan": wlan}
            exec(code, {}, local_scope)  # ローカルスコープにオブジェクトを渡す
        print(f"Executed successfully: {script_path}")
        return True
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
    for script in scripts:
        if now - script["last_run"] >= script["interval"]:
            print(f"Executing {script['path']}...")
            success = execute_script(script["path"], wlan)
            if success:
                print(f"{script['path']} executed successfully.")
            else:
                print(f"Error executing {script['path']}.")
            script["last_run"] = now
