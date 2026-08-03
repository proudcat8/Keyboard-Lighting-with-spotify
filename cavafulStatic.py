#!/usr/bin/env python3
import time
import subprocess
import traceback
import select
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

def start_cava():
    """Starts CAVA configured for fast audio output."""
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

    if not client.devices:
        print("No OpenRGB devices found!")
        return

    # Grab the current existing color from the first LED of the primary device
    # so the script never changes your base target color.
    primary_device = client.devices[0]
    initial_color = primary_device.colors[0]
    
    base_r = initial_color.red
    base_g = initial_color.green
    base_b = initial_color.blue
    
    print(f"Captured current existing base color: RGB({base_r}, {base_g}, {base_b})")

    print("Starting CAVA integration...")
    cava_proc = start_cava()

    print("Bouncing existing color to audio (Press Ctrl+C to stop)...")

    try:
        while True:
            # Real-time CAVA Audio Processing only
            ready, _, _ = select.select([cava_proc.stdout], [], [], 0.01)
            if ready:
                line = cava_proc.stdout.readline().strip()
                if line:
                    try:
                        bars = [int(x) for x in line.split(';') if x.isdigit()]
                        if bars:
                            # Primary low frequency / bass power
                            bass_power = sum(bars[:2]) / 2  # Range 0 to 100
                            
                            # Scaling factor: 10% floor during silence up to 100% full brightness on hits
                            brightness_factor = 0.10 + (bass_power / 100.0) * 0.90
                            
                            # Purely scale existing locked color brightness
                            r = max(0, min(255, int(base_r * brightness_factor)))
                            g = max(0, min(255, int(base_g * brightness_factor)))
                            b = max(0, min(255, int(base_b * brightness_factor)))
                            
                            for device in client.devices:
                                try:
                                    device.set_color(RGBColor(r, g, b))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                        
    finally:
        # Restore original static color when script stops
        try:
            for device in client.devices:
                device.set_color(RGBColor(base_r, base_g, base_b))
        except Exception:
            pass
        cava_proc.terminate()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping and restoring static color...")
    except Exception:
        traceback.print_exc()
        input("\nScript crashed. Press Enter to exit...")
