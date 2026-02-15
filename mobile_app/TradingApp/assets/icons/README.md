# 🐪 أيقونة تطبيق 1B

## الملفات المطلوبة

### Android (mipmap)
| الحجم | المجلد | الملف |
|-------|--------|-------|
| 48x48 | mipmap-mdpi | ic_launcher.png |
| 72x72 | mipmap-hdpi | ic_launcher.png |
| 96x96 | mipmap-xhdpi | ic_launcher.png |
| 144x144 | mipmap-xxhdpi | ic_launcher.png |
| 192x192 | mipmap-xxxhdpi | ic_launcher.png |

### iOS (AppIcon.appiconset)
| الحجم | الملف |
|-------|-------|
| 20x20 | Icon-20.png |
| 29x29 | Icon-29.png |
| 40x40 | Icon-40.png |
| 60x60 | Icon-60.png |
| 76x76 | Icon-76.png |
| 83.5x83.5 | Icon-83.5.png |
| 1024x1024 | Icon-1024.png |

## كيفية إنشاء الأيقونات

### الطريقة 1: استخدام أداة أونلاين
1. افتح [App Icon Generator](https://appicon.co/) أو [MakeAppIcon](https://makeappicon.com/)
2. ارفع ملف `app_icon.svg` أو صورة PNG بحجم 1024x1024
3. حمّل الأيقونات المولدة
4. انسخها للمجلدات المناسبة

### الطريقة 2: استخدام ImageMagick (Terminal)
```bash
# تثبيت ImageMagick
brew install imagemagick

# تحويل SVG إلى PNG بأحجام مختلفة
cd /Users/anr/Desktop/trading_ai_bot/mobile_app/TradingApp/assets

# Android
convert app_icon.svg -resize 48x48 ../android/app/src/main/res/mipmap-mdpi/ic_launcher.png
convert app_icon.svg -resize 72x72 ../android/app/src/main/res/mipmap-hdpi/ic_launcher.png
convert app_icon.svg -resize 96x96 ../android/app/src/main/res/mipmap-xhdpi/ic_launcher.png
convert app_icon.svg -resize 144x144 ../android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png
convert app_icon.svg -resize 192x192 ../android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png
```

### الطريقة 3: استخدام react-native-make
```bash
npm install -g @bam.tech/react-native-make
npx react-native set-icon --path ./assets/app_icon.png
```

## التصميم

```
┌─────────────────────────────────────┐
│                                     │
│         🐪 رأس الجمل                │
│                                     │
│            1B                       │
│          ↗    ↖                     │
│       ذهبي   بنفسجي                 │
│                                     │
│       ═══════════                   │
│        خط سماوي                     │
│                                     │
└─────────────────────────────────────┘

الألوان:
- الخلفية: تدرج بنفسجي داكن (#1a1a2e → #0f0f23)
- الرقم 1: ذهبي (#FFD700)
- الحرف B: بنفسجي (#8B5CF6)
- رأس الجمل: تدرج ذهبي-بنفسجي
- الخط الزخرفي: سماوي (#06B6D4)
```
