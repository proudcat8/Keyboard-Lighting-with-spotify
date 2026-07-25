#!/usr/bin/env python3
import time
import subprocess
import os
import traceback
import select
from urllib.request import urlretrieve
from PIL import Image
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

TEMP_IMAGE_PATH = "/tmp/spotify_current_art.png"

# --- HARDWARE COLOR BALANCING MULTIPLIERS (From accurate.py) ---
RED_CORRECTION   = 1.00  # Set to 1.00 for maximum red enhancement
GREEN_CORRECTION = 0.90  # Slightly dropped to let the red pop more
BLUE_CORRECTION  = 0.75  # Heavily dropped to kill cold blue LED bleed

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
    """Replaces banner extraction with accurate.py's hardware-balanced average color calculation."""
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
            
            # Apply hardware balance multipliers to correct hardware imbalance
            r = int(r * RED_CORRECTION)
            g = int(g * GREEN_CORRECTION)
            b = int(b * BLUE_CORRECTION)
            
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    except Exception:
        return (40, 40, 40)

def start_cava():
    """Starts CAVA in raw output mode with 8 bars."""
    cava_config = (
        "[general]\n"
        "bars = 8\n"
        "[output]\n"
        "method = raw\n"
        "data_format = ascii\n"
        "ascii_max_range = 100\n"
    )
    
    config_path = "/tmp/cava_openrgb.conf"
    with open(config_path, "w") as f:
        f.write(cava_config)
        
    return subprocess.Popen(["cava", "-p", config_path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

def main():
    print("Connecting to OpenRGB...")
    try:
        client = OpenRGBClient("127.0.0.1", 6742)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("Starting CAVA integration...")
    cava_proc = start_cava()

    # Default fallback color base
    base_r, base_g, base_b = 40, 40, 40
    last_url = ""
    spotify_check_interval = 2.0
    last_spotify_check = 0.0

    print("Listening to Spotify + CAVA (Press Ctrl+C to stop)...")

    try:
        while True:
            current_time = time.time()
            
            # 1. Throttled Spotify Art Check
            if current_time - last_spotify_check > spotify_check_interval:
                last_spotify_check = current_time
                current_url = get_spotify_art_url()
                
                if current_url and current_url != last_url:
                    last_url = current_url
                    base_r, base_g, base_b = extract_accurate_average_color(current_url)
                    print(f"New Album Art! Balanced RGB Base: ({base_r}, {base_g}, {base_b})")

            # 2. Real-time CAVA Audio Processing
            ready, _, _ = select.select([cava_proc.stdout], [], [], 0.01)
            if ready:
                line = cava_proc.stdout.readline().strip()
                if line:
                    try:
                        bars = [int(x) for x in line.split(';') if x.isdigit()]
                        if bars:
                            avg_intensity = sum(bars[:2]) / 2  # Responds primarily to low frequencies / bass
                            
                            # Scaling logic: Maps audio intensity to a 10% min / 100% max brightness factor
                            brightness_multiplier = 0.1 + (avg_intensity / 100.0) * 0.9
                            
                            # Multiply hardware-corrected base color by CAVA brightness multiplier
                            r = max(0, min(255, int(base_r * brightness_multiplier)))
                            g = max(0, min(255, int(base_g * brightness_multiplier)))
                            b = max(0, min(255, int(base_b * brightness_multiplier)))
                            
                            for device in client.devices:
                                try:
                                    device.set_color(RGBColor(r, g, b))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                        
    finally:
        cava_proc.terminate()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception:
        traceback.print_exc()
        input("\nScript crashed. Press Enter to exit...")
