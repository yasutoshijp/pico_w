import urequests
import gc
import time
import sys
import network
from machine import Pin
#★6時間毎に変更してみた
# ファイル名
LAST_SENT_FILE = "last_sent_time.txt"

# LED設定
led = Pin("LED", Pin.OUT)

# デバッグモード
DEBUG = True

# ChatWork API設定
CHATWORK_API_TOKEN = 'fba258f13899e421b3ab7a3a50488807'
CHATWORK_ROOM_ID = '67575950'
CHATWORK_API_ENDPOINT = f"https://api.chatwork.com/v2/rooms/{CHATWORK_ROOM_ID}/messages"

# グローバル変数
wlan = None

def debug_print(*args):
    """デバッグプリント"""
    if DEBUG:
        print("DEBUG:", *args)

def connect_wifi():
    """Wi-Fi接続を確立"""
    global wlan
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        debug_print("Wi-Fi未接続です。接続してください。")
        return False, None, None
    return True, wlan.config("essid"), wlan

def get_pico_info():
    """Pico Wの最低限のシステム情報を取得"""
    global wlan
    connected, ssid, local_wlan = connect_wifi()
    if not connected:
        return None
    # システム情報を作成
    gc.collect()
    pico_info = {
        "device_id": "PicoW-01",
        "ip_address": local_wlan.ifconfig()[0],
        "wifi_ssid": ssid,
        "mac_address": ":".join(["{:02x}".format(b) for b in local_wlan.config('mac')]),
        "memory_free": gc.mem_free(),
        "signal_strength": local_wlan.status('rssi') if local_wlan else None,
        "uptime": time.ticks_ms() // 1000  # 秒単位の起動時間
    }
    return pico_info

def read_last_sent_time():
    """前回送信時刻をファイルから読み取る"""
    try:
        with open(LAST_SENT_FILE, "r") as file:
            last_time = int(file.read().strip())
            debug_print(f"前回送信時刻を読み取り: {last_time}")
            return last_time
    except Exception as e:
        debug_print(f"前回送信時刻の読み取りエラー: {e}")
        return 0  # ファイルが存在しない場合は初期値を返す

def save_last_sent_time(timestamp):
    """現在の送信時刻をファイルに保存"""
    try:
        with open(LAST_SENT_FILE, "w") as file:
            file.write(str(timestamp))
            debug_print(f"送信時刻を保存: {timestamp}")
    except Exception as e:
        debug_print(f"送信時刻の保存エラー: {e}")

def send_to_chatwork(info):
    """ChatWorkに情報を送信"""
    last_sent_time = read_last_sent_time()
    current_time = time.time()

    # 前回送信から6時間（21600秒）未満ならスキップ
    if current_time - last_sent_time < 21600:
        debug_print("6時間未満のため送信をスキップします。")
        return False

    message_body = (
        "Raspberry Pi Pico Wから送信しています。\n"
        f"IPアドレス: {info['ip_address']}\n"
        f"Wi-Fi SSID: {info['wifi_ssid']}\n"
        f"MACアドレス: {info['mac_address']}\n"
        f"空きメモリ: {info['memory_free']} bytes\n"
        f"Wi-Fi信号強度: {info['signal_strength']} dBm\n"
        f"起動時間: {info['uptime']} 秒"
    )
    
    headers = {
        'X-ChatWorkToken': CHATWORK_API_TOKEN,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = f"body={message_body}"

    try:
        debug_print("ChatWorkに送信中...")
        response = urequests.post(
            CHATWORK_API_ENDPOINT,
            headers=headers,
            data=data
        )
        debug_print(f"レスポンス: {response.status_code}, {response.text}")
        response.close()
        if response.status_code == 200:
            save_last_sent_time(current_time)  # 送信成功時にファイルへ保存
        return response.status_code == 200
    except Exception as e:
        debug_print(f"エラー: {e}")
        return False

def main():
    """メイン処理"""
    debug_print("測定開始")
    try:
        info = get_pico_info()
        if not info:
            debug_print("システム情報の取得に失敗しました。")
            return
        if send_to_chatwork(info):
            debug_print("ChatWorkへの送信成功")
            led.value(1)
            time.sleep(0.5)
            led.value(0)
        else:
            debug_print("ChatWorkへの送信をスキップまたは失敗しました。")
            for _ in range(3):  # エラー時のLED点滅
                led.value(1)
                time.sleep(0.2)
                led.value(0)
                time.sleep(0.2)
    except Exception as e:
        debug_print(f"メインループエラー: {e}")
        time.sleep(5)

try:
    main()
except Exception as e:
    debug_print(f"致命的エラー: {e}")
