#!/usr/bin/env python3
import time
import subprocess
import os
import traceback
from urllib.request import urlretrieve
from PIL import Image
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

# --- CONFIGURATION ---
MAX_BRIGHTNESS = 60
TEMP_IMAGE_PATH = "/tmp/spotify_current_art.png"

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

def extract_banner_mood_color(art_url):
    img_path = None
    if art_url.startswith("file://"):
        img_path = art_url.replace("file://", "")
    elif art_url.startswith("http"):
        try:
            urlretrieve(art_url, TEMP_IMAGE_PATH)
            img_path = TEMP_IMAGE_PATH
        except Exception:
            return (60, 20, 0)

    if not img_path or not os.path.exists(img_path):
        return (60, 20, 0)

    try:
        with Image.open(img_path) as img:
            width, height = img.size
            banner_area = img.crop((0, 0, width, int(height * 0.2)))
            banner_area = banner_area.resize((1, 1))
            r, g, b = banner_area.getpixel((0, 0))[:3]
            
            # 1. Apply Warm Bias
            r = min(255, r + 80)
            g = max(0, g - 40)
            b = max(0, b - 100)
            
            # 2. Color-Specific Capping
            # We allow Red to be bright (it's the emotional color), 
            # but we aggressively throttle Green and Blue to keep them 'dim'.
            g = int(g * 0.4) 
            b = int(b * 0.3)
            
            # 3. Calculate Luminance
            luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            
            # 4. Final Scaling
            if luminance > 0.3:
                scale = MAX_BRIGHTNESS / (luminance * 255)
                r, g, b = int(r * scale), int(g * scale), int(b * scale)
            
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    except Exception:
        return (60, 20, 0)

def main():
    print("Connecting to OpenRGB...")
    try:
        client = OpenRGBClient("127.0.0.1", 6742)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    last_url = ""
    print("Listening to Spotify (Press Ctrl+C to stop)...")

    while True:
        current_url = get_spotify_art_url()
        
        if current_url and current_url != last_url:
            last_url = current_url
            r, g, b = extract_banner_mood_color(current_url)
            print(f"Setting keyboard to Banner Mood: RGB({r}, {g}, {b})")
            
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
