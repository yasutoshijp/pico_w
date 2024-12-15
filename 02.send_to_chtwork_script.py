import urequests
import gc
import time
import sys
import network

# LED設定
from machine import Pin
led = Pin("LED", Pin.OUT)

# デバッグモード
DEBUG = True

# ChatWork API設定
CHATWORK_API_TOKEN = 'fba258f13899e421b3ab7a3a50488807'
CHATWORK_ROOM_ID = '67549413'
CHATWORK_API_ENDPOINT = f"https://api.chatwork.com/v2/rooms/{CHATWORK_ROOM_ID}/messages"

# グローバル変数
wlan = None

def debug_print(*args):
    """デバッグプリント"""
    if DEBUG:
        print("DEBUG:", *args)

def connect_wifi():
    """Wi-Fi接続を確立（呼び出し元で実行済と想定）"""
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

import json  # 修正ポイント

def send_to_chatwork(info):
    """ChatWorkに情報を送信"""
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
        'Content-Type': 'application/x-www-form-urlencoded'  # 修正ポイント
    }
    data = {
        'body': message_body
    }

    try:
        debug_print("ChatWorkに送信中...")
        response = urequests.post(
            CHATWORK_API_ENDPOINT,
            headers=headers,
            data=json.dumps(data)  # 修正ポイント: JSON形式に変換
        )
        debug_print(f"レスポンス: {response.status_code}, {response.text}")
        response.close()
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
            debug_print("ChatWorkへの送信に失敗しました。")
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
