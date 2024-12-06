import wifi_manager
import github_manager
import captive_portal
import blink_led
import sys
import machine
import time
import json
import os
import ntptime
import network
# 定数
MAIN_LOOP_INTERVAL = 300  # 5分（秒）
SLEEP_TIME_ON_FAILURE = 3600  # 1時間（秒）

class LogWriter:
    def __init__(self, enable_logging=False, log_dir="/logs", keep_days=2):
        self.enable_logging = enable_logging
        self.log_dir = log_dir
        self.keep_days = keep_days
        self.log_buffer = []
        self._last_save_time = 0
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        try:
            if not os.path.exists(self.log_dir):
                os.mkdir(self.log_dir)
        except Exception as e:
            print(f"Warning: Failed to create log directory: {e}")
    
    def _get_log_filename(self):
        """現在の日付に基づくログファイル名を取得"""
        t = time.localtime()
        date_str = f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}"
        return f"{self.log_dir}/{date_str}_system.log"
    
    def _clean_old_logs(self):
        """古いログファイルを削除"""
        try:
            files = os.listdir(self.log_dir)
            files = [f for f in files if f.endswith("_system.log")]
            files.sort()  # 日付順にソート
            if len(files) > self.keep_days:
                for f in files[:-self.keep_days]:  # 最新2日分を残す
                    os.remove(f"{self.log_dir}/{f}")
                    print(f"Deleted old log file: {f}")
        except Exception as e:
            print(f"Failed to clean old logs: {e}")
    
    def log(self, message):
        if self.enable_logging:
            print(message)
            self.log_buffer.append(message)
            # バッファが一定量たまったら自動保存
            if len(self.log_buffer) > 50:
                self.save_logs()
    
    def save_logs(self):
        if not self.enable_logging or not self.log_buffer:
            return
            
        try:
            # 現在時刻を取得
            t = time.localtime()
            time_str = f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
            
            # ログファイル名を動的に決定
            log_filename = self._get_log_filename()
            
            # ログエントリーの開始部分を書き込み
            with open(log_filename, "a") as f:
                f.write("\n##################################################\n")
                f.write(f"### Session: {time_str}\n")
                f.write("### Mode: " + ("USB Connection" if t[0] < 2022 else "Normal Boot") + "\n")
                f.write("##################################################\n\n")
                
                # ログメッセージを書き込み
                for msg in self.log_buffer:
                    f.write(f"{msg}\n")
                
                # ログエントリーの終了部分を書き込み
                f.write("\n##################################################\n")
                f.write("### End of Session\n")
                f.write("##################################################\n")
            
            print(f"Log saved to {log_filename}")
            self.log_buffer = []
            self._last_save_time = time.time()
            
            # 古いログを削除
            self._clean_old_logs()
            
        except Exception as e:
            print(f"Error saving log: {e}")
            # エラー時でもバッファをクリア
            self.log_buffer = []
    
    def set_logging(self, enable):
        self.enable_logging = enable
        if enable:
            self._ensure_log_directory()

    def __del__(self):
        """オブジェクトが破棄される際に残っているログを保存"""
        if self.log_buffer:
            self.save_logs()


def merge_ssid_lists():
    """優先度順にSSIDリストを統合"""
    ssid_list = []
    seen_pairs = set()  # (ssid, password)のペアを記録

    # 1. captive_portalからの入力（最優先）
    try:
        with open('ssid.txt', 'r') as f:
            for line in f:
                ssid, password = line.strip().split(',')
                pair = (ssid, password)
                if pair not in seen_pairs:
                    ssid_list.append({"ssid": ssid, "password": password})
                    seen_pairs.add(pair)
    except:
        pass

    # 2. GitHubからのリスト
    try:
        with open('/remote_code/ssid_list.txt', 'r') as f:
            for line in f:
                ssid, password = line.strip().split(',')
                pair = (ssid, password)
                if pair not in seen_pairs:
                    ssid_list.append({"ssid": ssid, "password": password})
                    seen_pairs.add(pair)
    except:
        pass

    # 3. ハードコードされたリスト
    hardcoded_list = [
        {"ssid": "740635A8CCFD-2G", "password": "nn5rh49s5d7saa"},
        {"ssid": "TP-Link_A208", "password": "15405173"},
        {"ssid": "moonwalker", "password": "11112222"}
    ]
    for entry in hardcoded_list:
        pair = (entry["ssid"], entry["password"])
        if pair not in seen_pairs:
            ssid_list.append(entry)
            seen_pairs.add(pair)

    return ssid_list

def init_logger():
    """ロガーの初期化"""
    return LogWriter(enable_logging=True)

# グローバル変数として宣言
ntp_synced = False
def sync_ntp_time(logger):
    """NTP同期を試行（IPアドレス使用版）"""
    import ntptime
    try:
        logger.log("NTP時刻同期を開始...")
        ntptime.host = "216.239.35.0"  # GoogleのNTPサーバーのIP
        ntptime.timeout = 5
        ntptime.settime()
        t = time.localtime(time.time() + 9 * 60 * 60)  # JSTに変換
        logger.log(f"NTP同期成功: {t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} (JST)")
        return True
    except Exception as e:
        logger.log(f"NTP同期失敗: {str(e)}")
        return False


def handle_network_connection(logger):
    """WiFi接続とNTP同期を処理"""
    import usocket as socket
    try:
        # 統合されたSSIDリストを取得
        merged_ssid_list = merge_ssid_lists()
        connected = wifi_manager.connect_wifi(merged_ssid_list)
        logger.log(f"WiFi接続結果: {connected}")
        
        if not connected:
            logger.log("WiFi接続失敗、キャプティブポータルを起動します...")
            
            # LED点滅開始
            blink_led.led.start_blink(0.5, 0.5)
            
            # キャプティブポータルを実行
            portal_result = captive_portal.start_portal()
            
            # LED点滅停止
            blink_led.led.stop_blink()
            
            if portal_result:
                logger.log("新しいSSIDが登録されました。再接続を試みます...")
                return handle_network_connection(logger)  # 再試行
            else:
                logger.log("キャプティブポータルでのSSID登録がタイムアウトしました")
                logger.log(f"{SLEEP_TIME_ON_FAILURE//3600}時間スリープします...")
                time.sleep(SLEEP_TIME_ON_FAILURE)
                return False
                
        # WiFi接続成功後のDNS解決確認
        logger.log("DNS解決をテストします...")
        try:
            addr = socket.getaddrinfo("pool.ntp.org", 123)
            logger.log(f"DNS解決成功: {addr[0]}")
        except Exception as e:
            logger.log(f"DNS解決に失敗しました: {e}")
        
        # 接続成功時のNTP同期
        if connected:
            if sync_ntp_time(logger):
                logger.log("ネットワーク初期化完了（時刻同期成功）")
            else:
                logger.log("WiFi接続成功、ただし時刻同期失敗")
        
        return connected
        
    except Exception as e:
        logger.log(f"ネットワーク接続エラー: {str(e)}")
        return False


# 必要なパスを確認し追加
REMOTE_CODE_PATH = "/remote_code"
LIB_PATH = f"{REMOTE_CODE_PATH}/lib"
if REMOTE_CODE_PATH not in sys.path:
    sys.path.append(REMOTE_CODE_PATH)
if LIB_PATH not in sys.path:
    sys.path.append(LIB_PATH)
    
def main():
    logger = init_logger()
    
    while True:  # メインループ
        try:
            logger.log("\n=== Starting main loop ===")
            
            # 時刻状態の確認
            current_year = time.localtime()[0]
            if current_year < 2022:
                logger.log(f"警告: システム時刻が不正です（{current_year}年）")
            
            # ネットワーク接続処理
            if not handle_network_connection(logger):
                logger.log("ネットワーク接続失敗。次回ループまで待機します...")
                logger.log("ネットワーク診断を開始します...")
                network_diagnostics(logger)  # ネットワーク診断を追加
                logger.save_logs()
                logger.log(f"\n=== Waiting for {MAIN_LOOP_INTERVAL} seconds before retry ===")
                time.sleep(MAIN_LOOP_INTERVAL)
                continue

            # GitHubからのコード取得
            logger.log("GitHubの更新を確認します...")
            try:
                if github_manager.fetch_from_github():
                    logger.log("GitHub処理が完了しました")
                else:
                    logger.log("GitHub処理に失敗しましたが、処理を続行します")
            except Exception as e:
                logger.log(f"GitHub処理中に例外が発生しましたが、続行します: {str(e)}")

            # git_main.py の実行
            logger.log("\ngit_main.py を実行します...")
            git_main_path = "/remote_code/git_main.py"
            try:
                os.stat(git_main_path)  # ファイルの存在確認
                logger.log(f"スクリプトファイルを確認: {git_main_path}")
                with open(git_main_path, 'r') as f:
                    content = f.read()
                    logger.log(f"Script content length: {len(content)} bytes")
                
                logger.log("=== Starting git_main.py execution ===")
                global_vars = {
                    'wlan': None,
                    '__name__': '__main__',
                    'print': lambda x: logger.log(str(x)),  # printをlogger.logにリダイレクト
                    'time': time,
                    'sys': sys,
                    'machine': machine,
                    'logger': logger  # loggerを渡す
                }
                try:
                    github_manager.safe_execute_script(git_main_path, global_vars)
                    logger.log("=== Completed git_main.py execution ===")
                except Exception as e:
                    logger.log(f"スクリプト実行中に例外が発生: {str(e)}")
            except OSError as e:
                logger.log(f"git_main.py が見つかりませんでした: {str(e)}")
            except Exception as e:
                logger.log(f"予期せぬエラーが発生: {str(e)}")

            logger.save_logs()
            logger.log(f"\n=== Sleeping for {MAIN_LOOP_INTERVAL} seconds ===")
            time.sleep(MAIN_LOOP_INTERVAL)

        except Exception as e:
            error_message = f"Fatal error: {e}"
            logger.log(error_message)
            import io
            output = io.StringIO()
            sys.print_exception(e, output)
            error_details = output.getvalue()
            logger.log(f"Details: {error_details}")
            logger.save_logs()
            time.sleep(3)
            machine.reset()

def network_diagnostics(logger, retry_count=3):
    """ネットワーク診断とリトライ"""
    import usocket as socket
    logger.log("\n=== ネットワーク診断 ===")
    success = False
    for attempt in range(retry_count):
        try:
            logger.log(f"DNS解決をテストします...（試行 {attempt + 1}/{retry_count}）")
            addr = socket.getaddrinfo("pool.ntp.org", 123)
            logger.log(f"DNS解決成功: {addr[0]}")
            success = True
            break
        except OSError as e:
            if e.args[0] == -2:
                logger.log("DNS解決失敗: DNSサーバーが不明か、到達不可")
            else:
                logger.log(f"DNS解決失敗: {e}")
            time.sleep(2)  # リトライ前に待機

    if not success:
        logger.log("DNS解決に失敗しました。DNS設定を確認してください。")

    try:
        logger.log("NTPサーバーへの接続をテストします...")
        addr = socket.getaddrinfo("time.google.com", 123)
        logger.log(f"NTPサーバーへの接続成功: {addr[0]}")
    except Exception as e:
        logger.log(f"NTPサーバーへの接続失敗: {e}")



if __name__ == "__main__":
    main()
