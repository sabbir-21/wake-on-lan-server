# wake-on-lan-server on raspberry pi pico w telegram bot controlled

a tiny wake-on-lan-server hosted on raspberry pi pico w!

> a simple wake on lan server on raspberry pi pico w that hosts a telegram bot to turn on a pc connected to same wifi network via LAN port. Wake on lan service must be enabled on BIOS hardware.

![pico](pico.jpg)


## Features

- 24/7 Online via telegram bot
- controllable 40 pin pico w via bot
- auto reboot at interval time (to avoid memory leak)
- Wake On Lan Server / Switch on - off



```
wakeonlan A0-36-BC-BD-08-2B
```


## Installation

This requires micropython enabled Thonny to program and wake-on-lan enabled in PC BIOS.

### Router setup

Enable mac binding for pc in advance option.

for example: 192.168.1.101 to AA:BB:CC:DD:EE:FF

Enable DMZ server on that ip address to open all port for PC.

### PC setup
Activate wake on lan in BIOS. 

Ensure if PC has wakeonlan NIC and gather the mac address and NIC card name. (May be 2nd one is the NIC card `eth0` or `eno1`). Check if the line `Supports Wake-on: g`

```
ip address
```

```
sudo ethtool eno1
```

Install wake on PC by

```
sudo apt-get install wakeonlan -y
```

Make it persistant in ubuntu by /etc/systemd/system/wol.service file [pico](wol.service)

```
sudo nano /etc/systemd/system/wol.service
```

Paste the [pico](wol.service) code and save the file

```
sudo systemctl enable wol.service
``` 

Now your PC need to be connected to router via ethernet cable to be enabled for wake on lan.

### Telegram bot setup

Open botfather, create a new bot and get the bot token.

### PicoW setup

Install thonny on PC by

```
sudo apt install thonny
``` 

Open the code [main.py](main.py)

modify the credentials with yours

```
SSID = 'WIFI_SSID'
PASSWORD = 'PASSWORD'
BOT_TOKEN = 'TELEGRAM_BOT_TOKEN'
PC_MAC = 'A036BCBD082B'
REBOOT_INTERVAL = 1 * 60 * 60
```

Save on PicoW and restart it. Boom! Your server is running!


### Bot commands

Telegram bot is setup currently only for wake on lan service. You can add more command to extend it various services.

| Command | Actions |
| ------ | ------ |
| /start | Send a test message or welcome message |
| /poweron | Sends wake on lan command to PicoW |
| /uptime | Gives reboot time of PicoW |

