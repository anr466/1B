/**
 * 🐪 سكريبت توليد أيقونات التطبيق
 * يولد أيقونات Android من ملف SVG
 * 
 * الاستخدام:
 * npm install sharp
 * node scripts/generate-icons.js
 */

const fs = require('fs');
const path = require('path');

// محاولة استخدام sharp إذا كان متاحاً
let sharp;
try {
    sharp = require('sharp');
} catch (e) {
    console.log('⚠️ مكتبة sharp غير مثبتة');
    console.log('');
    console.log('لتثبيتها، نفذ:');
    console.log('  npm install sharp');
    console.log('');
    console.log('أو استخدم إحدى الطرق البديلة:');
    console.log('');
    console.log('🌐 الطريقة 1: أداة أونلاين');
    console.log('   1. افتح https://appicon.co/');
    console.log('   2. ارفع ملف assets/app_icon.svg');
    console.log('   3. حمّل الأيقونات وانسخها للمجلدات');
    console.log('');
    console.log('🍺 الطريقة 2: ImageMagick');
    console.log('   brew install imagemagick');
    console.log('   convert assets/app_icon.svg -resize 192x192 android/.../ic_launcher.png');
    console.log('');
    process.exit(0);
}

const ANDROID_SIZES = [
    { name: 'mipmap-mdpi', size: 48 },
    { name: 'mipmap-hdpi', size: 72 },
    { name: 'mipmap-xhdpi', size: 96 },
    { name: 'mipmap-xxhdpi', size: 144 },
    { name: 'mipmap-xxxhdpi', size: 192 },
];

const SOURCE_SVG = path.join(__dirname, '../assets/app_icon.svg');
const ANDROID_RES = path.join(__dirname, '../android/app/src/main/res');

async function generateIcons() {
    console.log('🐪 توليد أيقونات تطبيق 1B...\n');

    if (!fs.existsSync(SOURCE_SVG)) {
        console.error('❌ ملف SVG غير موجود:', SOURCE_SVG);
        process.exit(1);
    }

    for (const { name, size } of ANDROID_SIZES) {
        const outputDir = path.join(ANDROID_RES, name);
        const outputFile = path.join(outputDir, 'ic_launcher.png');
        const outputFileRound = path.join(outputDir, 'ic_launcher_round.png');

        try {
            await sharp(SOURCE_SVG)
                .resize(size, size)
                .png()
                .toFile(outputFile);

            // نسخة دائرية
            await sharp(SOURCE_SVG)
                .resize(size, size)
                .png()
                .toFile(outputFileRound);

            console.log(`✅ ${name}: ${size}x${size}`);
        } catch (err) {
            console.error(`❌ خطأ في ${name}:`, err.message);
        }
    }

    console.log('\n✅ تم توليد جميع الأيقونات!');
    console.log('📱 أعد بناء التطبيق لرؤية الأيقونة الجديدة');
}

generateIcons();
