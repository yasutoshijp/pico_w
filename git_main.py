import os

def execute_script(script_path):
    """スクリプトを外部プロセスとして実行"""
    try:
        exit_code = os.system(f"python {script_path}")
        if exit_code == 0:
            print(f"Executed successfully: {script_path}")
            return True
        else:
            print(f"Script failed with exit code {exit_code}: {script_path}")
            return False
    except Exception as e:
        print(f"Error executing script {script_path}: {e}")
        return False

def run():
    print("Running git_main.py...")

    # 実行するスクリプトリスト
    scripts = [
        "/remote_code/01.send_to_ss.py",
        "/remote_code/02.send_to_ss.py",
    ]

    # スクリプトを順番に実行
    for script_path in scripts:
        print(f"Executing {script_path}...")
        success = execute_script(script_path)
        if success:
            print(f"{script_path} executed successfully.")
        else:
            print(f"Error executing {script_path}.")

# 実行
if __name__ == "__main__":
    run()
