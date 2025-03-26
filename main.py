import network
import socket
import time
import urequests
import ujson
import gc
from machine import Pin, reset

# Wi-Fi Configuration
SSID = 'WIFI_SSID'
PASSWORD = 'PASSWORD'

# Telegram Bot Configuration
BOT_TOKEN = 'TELEGRAM_BOT_TOKEN'
LAST_UPDATE_ID = 0

# PC Configuration
PC_MAC = 'A036BCBD082B'  # Format: AABBCCDDEEFF or AA:BB:CC:DD:EE:FF
BROADCAST_ADDR = '255.255.255.255'
WOL_PORT = 9

# Auto-reboot interval in seconds (for testing, set to 1 hour; change as needed)
REBOOT_INTERVAL = 1 * 60 * 60

led = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    retries = 0
    while not wlan.isconnected() and retries < 20:
        print('Connecting to Wi-Fi...')
        time.sleep(1)
        retries += 1
    if wlan.isconnected():
        print('Connected:', wlan.ifconfig())
    else:
        print('Wi-Fi failed after retries.')
    return wlan

def ensure_wifi(wlan):
    if not wlan.isconnected():
        print("Wi-Fi lost. Reconnecting...")
        wlan.disconnect()
        wlan.connect(SSID, PASSWORD)
        retries = 0
        while not wlan.isconnected() and retries < 10:
            print("Reconnecting...")
            time.sleep(1)
            retries += 1
        if wlan.isconnected():
            print("Reconnected:", wlan.ifconfig())
        else:
            print("Failed to reconnect.")

def clean_mac(mac):
    return mac.replace(':', '').replace('-', '')

def create_magic_packet(mac):
    mac = clean_mac(mac)
    mac_bytes = bytes.fromhex(mac)
    return b'\xff' * 6 + mac_bytes * 16

def send_wol():
    try:
        wol_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        wol_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        wol_socket.sendto(create_magic_packet(PC_MAC), (BROADCAST_ADDR, WOL_PORT))
        wol_socket.close()
        print("WoL packet sent.")
    except Exception as e:
        print("WoL error:", e)

def send_telegram_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    try:
        r = urequests.post(url, json=data)
        r.close()
    except Exception as e:
        print("Telegram send error:", e)

def format_uptime(start_time):
    seconds = int(time.time() - start_time)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"Uptime: {hours:02}:{minutes:02}:{secs:02}"

def flush_telegram_updates():
    """
    Flush pending updates so that any previous commands (like /reboot) are cleared.
    """
    global LAST_UPDATE_ID
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    try:
        response = urequests.get(url, timeout=5)
        data = ujson.loads(response.text)
        response.close()
        if data.get("ok") and len(data.get("result", [])) > 0:
            # Set LAST_UPDATE_ID to the latest update id
            LAST_UPDATE_ID = data["result"][-1]["update_id"]
            print("Flushed updates. LAST_UPDATE_ID set to", LAST_UPDATE_ID)
    except Exception as e:
        print("Flush updates error:", e)

def check_telegram(start_time):
    global LAST_UPDATE_ID
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=20'
    try:
        response = urequests.get(url)
        data = ujson.loads(response.text)
        response.close()
        if data.get("ok") and len(data.get("result", [])) > 0:
            for update in data["result"]:
                LAST_UPDATE_ID = update["update_id"]
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "").strip().lower()

                if not chat_id or not text:
                    continue

                print(f"Command: {text}")

                if text == "/start":
                    send_telegram_message(chat_id, "Pico W is running.")

                elif text == "/poweron":
                    send_wol()
                    send_telegram_message(chat_id, "Sent WoL packet.")
                    led.value(1)
                    time.sleep(1)
                    led.value(0)

                elif text == "/uptime":
                    send_telegram_message(chat_id, format_uptime(start_time))

                elif text == "/reboot":
                    send_telegram_message(chat_id, "Rebooting now...")
                    time.sleep(2)
                    reset()

                else:
                    print("Unknown command.")
                    # Optionally send feedback:
                    # send_telegram_message(chat_id, "Unknown command.")

    except Exception as e:
        print("Telegram check error:", e)

def check_reboot(start_time):
    if time.time() - start_time >= REBOOT_INTERVAL:
        print("Auto-reboot due to uptime.")
        time.sleep(1)
        reset()

def main():
    start_time = time.time()  # Set uptime counter at startup (resets after reboot)
    wlan = connect_wifi()
    led.value(1)
    time.sleep(2)
    led.value(0)
    print("Bot ready.")
    flush_telegram_updates()  # Clear pending updates on boot
    while True:
        try:
            ensure_wifi(wlan)
            check_telegram(start_time)
            check_reboot(start_time)
            gc.collect()
        except Exception as e:
            print("Main loop error:", e)
        time.sleep(5)

if __name__ == "__main__":
    main()
