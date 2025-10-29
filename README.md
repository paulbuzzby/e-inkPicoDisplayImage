# e-inkPicoDisplayImage

This code runs on a RPi pico W. 

Connects to an interal HTTP site to download a pre made pbm image file

The image file is already the correct width and height for the 7.5inch e-ink display that is being used. 480x800

Before downloading the image the modified date on the server is checked to see if it is newer than the image downloaded last time. Only newer images are downloaded and updated. 

This is to save power. The whole aim of this system is to try and use as little power as possible so that the time between battery charges is kept to a minimum.

This project replaces my previous RPi zero 2 W with a battery power pack.
The heavy lifting of reading my calendar and creating the image is offloaded to a local server.

## Process flow

The TPL511 is set to the max time of 2 hours. 

Once all connected. The TPL511 will wake up and enable the output on the PowerBoost board. This will boot the pi which will execute main.py.

Wifi is connected, File downloaded, e-ink display updated

At the end the pico will enable pin 19 which pulls the DONE pin on the TPL511 high and shutdowns the powerboost board. Killing power to the pico.

ChatGPT claims that on a full charge this should be able to run for over 100 days but I am yet to prove this. The full execution takes about 30 seconds from boot to shutdown. 


# Hardware

[PowerBoost 500 Charger](https://www.adafruit.com/product/1944)

[Adafruit TPL5111 Low Power Timer Breakout](https://www.adafruit.com/product/3573)

Also need a LiPo. I am using a 2000mAh one.
Check the plug when connecting to the powerBoost board as I had to switch the pins in the battery connector

Connecting up the boards is suprisingly simple.

## From the powerboost board to the TPL511 board

- Bat -> VDD
- GND -> GND
- EN -> ENout

## From the powerboost board to the Pi Pico W

- Positive  -> VSYS
- Ground -> GND (any ground will do but there is one next to the VSYS)

## From the TPL511 board to the Pi Pico W

- DONE -> GP19 - The Pico pin can be anything. Just update the code

# Config file

You need to create a secrets.json file in the following format

```json
{
  "ssid": "SSID",
  "password": "PASSWORD",
  "file_url": "<FULL HTTPS URL TO THE FILE TO DOWNLOAD>",
  "target_path": "/calendar.pbm",
  "last_modified": 0
}
```




# Pin layout for e-ink display to pico

- BUSY - 13
- RST - 12
- DC - 8
- CS - 9
- CLK - 10
- DIN - 11
- GND - GND
- VCC - 3v3 out

# Notes

You need to power cycle the TPL511 if you change the timer screw. Otherwise it will not change the time.

For reasons, I did not investigate the pico would connect to my server via a DNS name. I had to use the internal IP address. 
