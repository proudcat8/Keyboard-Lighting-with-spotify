#!/usr/bin/env python3
import time
import subprocess
import os
import traceback
from urllib.request import urlretrieve
from PIL import Image
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

TEMP_IMAGE_PATH = "/tmp/spotify_current_art.png"

# --- HARDWARE COLOR BALANCING MULTIPLIERS ---
# Range: 0.00 to 1.00
# - Lowering a value REDUCES the intensity/overpowering nature of that color.
# - Increasing a value towards 1.00 lets that color shine through at maximum power.
RED_CORRECTION   = 1.00  # Set to 1.00 for maximum red enhancement
GREEN_CORRECTION = 0.90  # Slightly dropped to let the red pop more
BLUE_CORRECTION  = 0.75  # Heavily dropped to kill the cold blue LED bleed

def get_spotify_art_url():
    try:
        status = subprocess.check_output(["playerctl", "-p", "spotify", "status"], stderr=subprocess.DEVNULL).decode().strip()
        if status != "Playing":
            return None
        cmd = ["playerctl", "-p", "spotify", "metadata", "mpris:artUrl"]
        url = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return url
    except Exception:
        return None

def extract_accurate_average_color(art_url):
    img_path = None
    if art_url.startswith("file://"):
        img_path = art_url.replace("file://", "")
    elif art_url.startswith("http"):
        try:
            urlretrieve(art_url, TEMP_IMAGE_PATH)
            img_path = TEMP_IMAGE_PATH
        except Exception:
            return (40, 40, 40)

    if not img_path or not os.path.exists(img_path):
        return (40, 40, 40)

    try:
        with Image.open(img_path) as img:
            # Resizing the full image to 1x1 extracts the true mathematical color average
            img_avg = img.resize((1, 1))
            r, g, b = img_avg.getpixel((0, 0))[:3]
            
            # Apply your hardware balance multipliers to correct hardware imbalance
            r = int(r * RED_CORRECTION)
            g = int(g * GREEN_CORRECTION)
            b = int(b * BLUE_CORRECTION)
            
            # Output raw, uncapped values directly through
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    except Exception:
        return (40, 40, 40)

def main():
    print("Connecting to OpenRGB...")
    try:
        client = OpenRGBClient("127.0.0.1", 6742)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    last_url = ""
    print("Listening to Spotify")

    while True:
        current_url = get_spotify_art_url()
        
        if current_url and current_url != last_url:
            last_url = current_url
            r, g, b = extract_accurate_average_color(current_url)
            print(f"Setting keyboard to Balanced True Average: RGB({r}, {g}, {b})")
            
            for device in client.devices:
                try:
                    device.set_color(RGBColor(r, g, b))
                except Exception:
                    pass
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception:
        traceback.print_exc()
        input("\nScript crashed. Press Enter to exit...")
