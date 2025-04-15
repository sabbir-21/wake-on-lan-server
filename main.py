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

def ensure_internet(wlan):
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
            print("Failed to reconnect Wi-Fi.")
            return False
    endpoints = ["https://www.google.com", "https://api.telegram.org"]
    for endpoint in endpoints:
        for attempt in range(3):
            try:
                r = urequests.get(endpoint, timeout=5)
                r.close()
                print(f"Internet is connected (tested {endpoint}).")
                return True
            except Exception as e:
                print(f"No internet connection to {endpoint} (attempt {attempt + 1}/3):", e)
                time.sleep(1)
    print("All internet checks failed.")
    return False

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
    retries = 3
    for attempt in range(retries):
        try:
            r = urequests.post(url, data=ujson.dumps(data), headers={'Content-Type': 'application/json'}, timeout=10)
            if r.json().get("ok"):
                print("Message sent successfully")
            else:
                print("Failed to send message:", r.json())
            r.close()
            return
        except Exception as e:
            print(f"Telegram send error (attempt {attempt + 1}/{retries}):", e)
            if attempt < retries - 1:
                time.sleep(2)
    print("Failed to send message after retries.")

def format_uptime(start_time):
    seconds = int(time.time() - start_time)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"Uptime: {hours:02}:{minutes:02}:{secs:02}"

def check_telegram(start_time):
    global LAST_UPDATE_ID
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=20'
    retries = 3
    for attempt in range(retries):
        try:
            response = urequests.get(url, timeout=10)  # Increased timeout
            data = ujson.loads(response.text)
            response.close()
            if not data.get("ok"):
                print("Error getting updates:", data)
                return
            if len(data.get("result", [])) > 0:
                print("Received updates:", len(data["result"]))
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
            else:
                print("No new updates.")
            return  # Success, exit function
        except Exception as e:
            print(f"Telegram check error (attempt {attempt + 1}/{retries}):", e)
            if attempt < retries - 1:
                time.sleep(2)  # Wait before retrying
            else:
                print("Max retries reached, skipping update check.")

def check_reboot(start_time):
    if time.time() - start_time >= REBOOT_INTERVAL:
        print("Auto-reboot due to uptime.")
        time.sleep(1)
        reset()

def main():
    start_time = time.time()
    wlan = connect_wifi()
    led.value(1)
    time.sleep(2)
    led.value(0)
    print("Bot ready.")
    while True:
        try:
            if ensure_internet(wlan):
                check_telegram(start_time)
                gc.collect()
            else:
                print("No internet, waiting...")
        except Exception as e:
            print("Main loop error:", e)
        check_reboot(start_time)
        time.sleep(5)

if __name__ == "__main__":
    main()
