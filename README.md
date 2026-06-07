# Spotify Mood-Sync RGB 

A lightweight, automated background daemon for **Arch Linux (Hyprland)** that dynamically adjusts your keyboard backlighting based on the actual emotional data of your currently playing Spotify track.

Instead of just guessing colors from album art, this script queries the Spotify API's computational audio analysis engine to map the **Valence** (happiness/sadness) and **Energy** (intensity) of your music directly to your LEDs via OpenRGB.

---

## The Mood Matrix

The script keeps the lighting low-intensity to prevent late-night eye strain, translating your music into four distinct emotional profiles:

| Vibe | Audio Metrics | RGB Preset | Visual Mood |
| :--- | :--- | :--- | :--- |
| **Melancholic / Sad** | Low Valence & Low Energy | `50, 15, 80` | Deep Midnight Violet |
| **Aggressive / Dark** | Low Valence & High Energy | `180, 8, 0` | Volcanic Ember |
| **Chill / Peaceful** | High Valence & Low Energy | `160, 90, 15` | Muted Warm Amber |
| **Energetic / Happy** | High Valence & High Energy | `220, 50, 5` | Warm Deep Sunset Orange |

---

## Prerequisites & Installation

### 1. Install System Dependencies
Since this runs on Arch, install the required native utilities and Python dependencies directly via `pacman` and `pip`:

```bash
sudo pacman -S playerctl openrgb python-pillow
pip install spotipy openrgb-python
