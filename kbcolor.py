#!/usr/bin/env python3
import time
import subprocess
import os
from urllib.request import urlretrieve
from PIL import Image
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

# --- CONFIGURATION ---
MAX_BRIGHTNESS = 90  # Caps the RGB values so it never gets too bright
MIN_BRIGHTNESS = 10  # Keeps a very faint glow even on pitch-black covers
TEMP_IMAGE_PATH = "/tmp/spotify_current_art.png"

def get_spotify_art_url():
    try:
        cmd = ["playerctl", "-p", "spotify", "metadata", "mpris:artUrl"]
        url = subprocess.check_output(cmd).decode("utf-8").strip()
        return url
    except subprocess.CalledProcessError:
        return None

def extract_mood_color(art_url):
    img_path = None

    # Handle local file paths (Common for standard Arch/AUR installation)
    if art_url.startswith("file://"):
        local_path = art_url.replace("file://", "")
        if os.path.exists(local_path):
            img_path = local_path

    # Handle web URLs (Common if using Flatpak or specific Spotify versions)
    elif art_url.startswith("http://") or art_url.startswith("https://"):
        try:
            urlretrieve(art_url, TEMP_IMAGE_PATH)
            img_path = TEMP_IMAGE_PATH
        except Exception as e:
            print(f"Failed to download web artwork: {e}")
            return None

    # If we couldn't resolve a valid image path, fallback to safety
    if not img_path or not os.path.exists(img_path):
        print(f"Artwork path not found: {art_url}. Using fallback color.")
        return (20, 0, 0) # Fallback to a very dim Volcanic Ember

    try:
        with Image.open(img_path) as img:
            img = img.resize((1, 1))
            r, g, b = img.getpixel((0, 0))[:3]
            
            # Scale brightness
            max_val = max(r, g, b, 1)
            if max_val > MAX_BRIGHTNESS:
                scale = MAX_BRIGHTNESS / max_val
                r, g, b = int(r * scale), int(g * scale), int(b * scale)
                
            if r < MIN_BRIGHTNESS and g < MIN_BRIGHTNESS and b < MIN_BRIGHTNESS:
                return (20, 0, 0)
                
            return (r, g, b)
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def main():
    try:
        client = OpenRGBClient("127.0.0.1", 6742)
    except ConnectionRefusedError:
        print("Error: Make sure the OpenRGB SDK server is running!")
        return

    last_url = ""
    print("Listening to Spotify mood... (Play a song to trigger)")

    while True:
        current_url = get_spotify_art_url()
        
        if current_url and current_url != last_url:
            last_url = current_url
            color = extract_mood_color(current_url)
            
            if color:
                r, g, b = color
                print(f"Setting keyboard to mood profile: RGB({r}, {g}, {b})")
                
                for device in client.devices:
                    device.set_color(RGBColor(r, g, b))
                    
        time.sleep(2)

if __name__ == "__main__":
    main()
