#!/usr/bin/env node

/**
 * 🔧 أداة إعداد الاتصال الذكية
 * تحل مشاكل IP والعناوين تلقائياً
 * 
 * الاستخدام: node setup-connection.js
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// ==================== الحصول على IP المحلي ====================

function getLocalIP() {
  const interfaces = os.networkInterfaces();
  
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      // تخطي الـ loopback والـ IPv6
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  
  return '127.0.0.1';
}

// ==================== تحديث الملفات ====================

function updateConnectionConfig(localIP) {
  const configPath = path.join(__dirname, 'src/config/ConnectionConfig.js');
  
  let content = fs.readFileSync(configPath, 'utf8');
  
  // استبدال IP القديم بـ IP الجديد
  content = content.replace(
    /localIP: '[\d.]+'/g,
    `localIP: '${localIP}'`
  );
  content = content.replace(
    /hostIP: '[\d.]+'/g,
    `hostIP: '${localIP}'`
  );
  
  fs.writeFileSync(configPath, content, 'utf8');
  console.log(`✅ تم تحديث ConnectionConfig.js بـ IP: ${localIP}`);
}

function updateMetroConfig(localIP) {
  const metroPath = path.join(__dirname, 'metro.config.js');
  
  let content = fs.readFileSync(metroPath, 'utf8');
  
  // استبدال IP في X-Metro-Host
  content = content.replace(
    /X-Metro-Host', '[\d.]+'/g,
    `X-Metro-Host', '${localIP}'`
  );
  
  fs.writeFileSync(metroPath, content, 'utf8');
  console.log(`✅ تم تحديث metro.config.js بـ IP: ${localIP}`);
}

function updateEnvFile(localIP) {
  const envPath = path.join(__dirname, '.env');
  
  if (fs.existsSync(envPath)) {
    let content = fs.readFileSync(envPath, 'utf8');
    
    // تحديث أو إضافة API_URL
    if (content.includes('API_URL=')) {
      content = content.replace(
        /API_URL=http:\/\/[\d.]+:\d+/g,
        `API_URL=http://${localIP}:3002`
      );
    } else {
      content += `\nAPI_URL=http://${localIP}:3002\n`;
    }
    
    fs.writeFileSync(envPath, content, 'utf8');
    console.log(`✅ تم تحديث .env بـ API_URL: http://${localIP}:3002`);
  }
}

// ==================== البرنامج الرئيسي ====================

async function main() {
  console.log('\n🔧 أداة إعداد الاتصال الذكية');
  console.log('================================\n');
  
  const localIP = getLocalIP();
  console.log(`📡 تم اكتشاف IP المحلي: ${localIP}\n`);
  
  try {
    updateConnectionConfig(localIP);
    updateMetroConfig(localIP);
    updateEnvFile(localIP);
    
    console.log('\n✅ تم إعداد الاتصال بنجاح!');
    console.log(`\n📋 الإعدادات الحالية:`);
    console.log(`   - IP المحلي: ${localIP}`);
    console.log(`   - Backend: http://${localIP}:3002`);
    console.log(`   - Metro: http://${localIP}:8081`);
    console.log('\n🚀 يمكنك الآن تشغيل التطبيق بأمان\n');
    
  } catch (error) {
    console.error('❌ خطأ:', error.message);
    process.exit(1);
  }
}

main();
