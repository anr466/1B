#!/usr/bin/env python3
"""
إنشاء أيقونات التطبيق - 1B
شعار احترافي مستوحى من صقر الشاهين السعودي
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_gradient_background(size, colors):
    """إنشاء خلفية متدرجة"""
    image = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(image)
    
    # التدرج من الأعلى للأسفل
    for y in range(size):
        ratio = y / size
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    return image

def create_1b_logo(size):
    """إنشاء شعار 1B احترافي"""
    # ألوان التدرج البنفسجي (مستوحى من اللون السعودي الملكي)
    gradient_colors = [
        (139, 123, 232),  # #8B7BE8
        (74, 63, 184)     # #4A3FB8
    ]
    
    # إنشاء الصورة الأساسية
    img = create_gradient_background(size, gradient_colors)
    draw = ImageDraw.Draw(img)
    
    # إضافة زوايا دائرية
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    corner_radius = size // 5
    mask_draw.rounded_rectangle([(0, 0), (size, size)], corner_radius, fill=255)
    
    # تطبيق القناع
    output = Image.new('RGBA', (size, size))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    # رسم نص 1B
    draw = ImageDraw.Draw(output)
    
    # محاولة استخدام خط عربي أو افتراضي
    try:
        # حجم الخط بناءً على حجم الصورة
        font_size = int(size * 0.45)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = ImageFont.load_default()
    
    # رسم النص في المنتصف
    text = "1B"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - size // 15
    
    # ظل النص للعمق
    shadow_offset = max(2, size // 100)
    draw.text((x + shadow_offset, y + shadow_offset), text, 
              fill=(0, 0, 0, 80), font=font)
    
    # النص الرئيسي
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # خط سرعة انسيابي (يوحي بسرعة الصقر)
    speed_line_width = int(size * 0.35)
    speed_line_height = max(3, int(size * 0.05))
    speed_line_x = int(size * 0.55)
    speed_line_y = int(size * 0.75)
    
    # رسم خط السرعة بشفافية
    draw.ellipse([
        speed_line_x, 
        speed_line_y,
        speed_line_x + speed_line_width,
        speed_line_y + speed_line_height
    ], fill=(255, 255, 255, 100))
    
    return output

def main():
    """إنشاء جميع أحجام الأيقونات المطلوبة"""
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # الأحجام المطلوبة
    icon_sizes = {
        'android': {
            'mipmap-mdpi': 48,
            'mipmap-hdpi': 72,
            'mipmap-xhdpi': 96,
            'mipmap-xxhdpi': 144,
            'mipmap-xxxhdpi': 192,
        },
        'ios': [20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024],
        'expo': [192, 512, 1024]
    }
    
    print("🎨 بدء إنشاء أيقونات التطبيق...")
    
    # إنشاء أيقونات Android
    print("\n📱 إنشاء أيقونات Android...")
    android_base = os.path.join(base_path, 'android', 'app', 'src', 'main', 'res')
    
    for folder, size in icon_sizes['android'].items():
        folder_path = os.path.join(android_base, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        icon = create_1b_logo(size)
        icon_path = os.path.join(folder_path, 'ic_launcher.png')
        icon.save(icon_path, 'PNG')
        
        # أيقونة مستديرة
        round_icon_path = os.path.join(folder_path, 'ic_launcher_round.png')
        icon.save(round_icon_path, 'PNG')
        
        print(f"  ✅ تم إنشاء {folder}/ic_launcher.png ({size}x{size})")
    
    # إنشاء أيقونة كبيرة لـ Expo/React Native
    print("\n🚀 إنشاء أيقونة التطبيق الرئيسية...")
    assets_path = os.path.join(base_path, 'assets')
    os.makedirs(assets_path, exist_ok=True)
    
    main_icon = create_1b_logo(1024)
    main_icon.save(os.path.join(assets_path, 'icon.png'), 'PNG')
    print("  ✅ تم إنشاء assets/icon.png (1024x1024)")
    
    # أيقونة adaptive للأندرويد
    adaptive_icon = create_1b_logo(512)
    adaptive_icon.save(os.path.join(assets_path, 'adaptive-icon.png'), 'PNG')
    print("  ✅ تم إنشاء assets/adaptive-icon.png (512x512)")
    
    print("\n✅ تم إنشاء جميع الأيقونات بنجاح!")
    print("🎯 الشعار مستوحى من صقر الشاهين - يوحي بالسرعة والذكاء والقوة")

if __name__ == '__main__':
    main()
