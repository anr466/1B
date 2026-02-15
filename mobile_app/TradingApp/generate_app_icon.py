#!/usr/bin/env python3
"""
إنشاء أيقونات التطبيق بخلفية داكنة متوافقة مع Android
"""

from PIL import Image, ImageDraw
import os

# المسارات
ASSETS_DIR = "assets"
RES_DIR = "android/app/src/main/res"

# أحجام الأيقونات لكل كثافة
ICON_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

# لون الخلفية الداكن (يتناسب مع الشعار)
BG_COLOR = (18, 18, 32, 255)  # أزرق داكن جداً

def create_rounded_icon(logo_path, size, is_round=False):
    """إنشاء أيقونة مع خلفية داكنة"""
    
    # إنشاء خلفية
    icon = Image.new('RGBA', (size, size), BG_COLOR)
    
    # تحميل الشعار
    logo = Image.open(logo_path).convert('RGBA')
    
    # حساب حجم الشعار (85% من حجم الأيقونة)
    logo_size = int(size * 0.85)
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # وضع الشعار في المنتصف
    offset = (size - logo_size) // 2
    icon.paste(logo, (offset, offset), logo)
    
    if is_round:
        # إنشاء قناع دائري
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # تطبيق القناع
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(icon, (0, 0), mask)
        return output
    
    return icon

def main():
    logo_path = os.path.join(ASSETS_DIR, "icon.png")
    
    if not os.path.exists(logo_path):
        print(f"❌ الشعار غير موجود: {logo_path}")
        return
    
    print("🎨 إنشاء أيقونات التطبيق...")
    
    for folder, size in ICON_SIZES.items():
        folder_path = os.path.join(RES_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # أيقونة عادية
        icon = create_rounded_icon(logo_path, size, is_round=False)
        icon_path = os.path.join(folder_path, "ic_launcher.png")
        icon.save(icon_path, "PNG")
        print(f"  ✅ {folder}/ic_launcher.png ({size}x{size})")
        
        # أيقونة دائرية
        round_icon = create_rounded_icon(logo_path, size, is_round=True)
        round_path = os.path.join(folder_path, "ic_launcher_round.png")
        round_icon.save(round_path, "PNG")
        print(f"  ✅ {folder}/ic_launcher_round.png ({size}x{size})")
    
    print("\n🎉 تم إنشاء جميع الأيقونات بنجاح!")
    print("📱 أعد بناء التطبيق: npm run android")

if __name__ == "__main__":
    main()
