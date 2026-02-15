#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw

def create_icon(size, output_path):
    # Create a simple icon with a blue background and white "T" for Trading
    img = Image.new('RGBA', (size, size), (33, 150, 243, 255))  # Blue background
    draw = ImageDraw.Draw(img)
    
    # Draw a simple "T" letter
    font_size = size // 2
    text = "T"
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255, 255))  # White text
    
    img.save(output_path, 'PNG')
    print(f"Created icon: {output_path}")

# Create icons for different densities
base_path = "android/app/src/main/res"
icon_sizes = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192
}

for folder, size in icon_sizes.items():
    folder_path = os.path.join(base_path, folder)
    os.makedirs(folder_path, exist_ok=True)
    
    # Create both ic_launcher and ic_launcher_round
    create_icon(size, os.path.join(folder_path, "ic_launcher.png"))
    create_icon(size, os.path.join(folder_path, "ic_launcher_round.png"))

print("All icons created successfully!")
