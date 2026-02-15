# 📦 دليل المكونات الموحدة - Trading AI Bot

**التاريخ:** 10 يناير 2026  
**الحالة:** ✅ مكونات جاهزة للاستخدام

---

## 🎯 الهدف

توحيد عرض البيانات عبر التطبيق لتحقيق:
- ✅ **الوضوح**: البيانات واضحة وسهلة القراءة
- ✅ **الاتساق**: نفس الأسلوب في جميع الشاشات
- ✅ **الدقة**: تنسيق صحيح للأرقام والعملات
- ✅ **التجربة**: تفاعل سلس ومريح

---

## 📚 المكونات المتاحة

### 1. ProfitLossIndicator
**الوصف:** مكون موحد لعرض الأرباح والخسائر

**الاستخدام:**
```javascript
import ProfitLossIndicator from '../components/ProfitLossIndicator';

<ProfitLossIndicator
    value={150.50}              // القيمة (موجبة = ربح، سالبة = خسارة)
    percentage={5.25}           // النسبة المئوية
    showIcon={true}             // عرض أيقونة الاتجاه
    showPercentage={true}       // عرض النسبة المئوية
    size="medium"               // small, medium, large
/>
```

**مثال الإخراج:**
```
🔼 +$150.50 ↑ 5.25%
```

**الميزات:**
- ✅ لون ديناميكي (أخضر للربح، أحمر للخسارة)
- ✅ أيقونة اتجاه
- ✅ تنسيق تلقائي (K, M للأرقام الكبيرة)
- ✅ 3 أحجام متاحة

---

### 2. StatCard
**الوصف:** بطاقة موحدة لعرض الإحصائيات

**الاستخدام:**
```javascript
import StatCard from '../components/StatCard';

<StatCard
    title="إجمالي الأرباح"
    value={1250.75}
    subtitle="من 45 صفقة"
    icon="trending-up"
    iconColor={theme.colors.success}
    trend="up"                  // up, down, neutral
    trendValue="+12.5%"
    loading={false}
/>
```

**مثال الإخراج:**
```
┌─────────────────────┐
│ 📈 إجمالي الأرباح  │ ↑ +12.5%
│                     │
│    1,250.75         │
│                     │
│ من 45 صفقة          │
└─────────────────────┘
```

**الميزات:**
- ✅ أيقونة قابلة للتخصيص
- ✅ مؤشر الاتجاه
- ✅ حالة تحميل
- ✅ تنسيق تلقائي

---

### 3. TradeCard
**الوصف:** بطاقة موحدة لعرض الصفقة

**الاستخدام:**
```javascript
import TradeCard from '../components/TradeCard';

<TradeCard
    trade={{
        symbol: 'BTCUSDT',
        side: 'BUY',
        entry_price: 45000,
        exit_price: 47250,
        quantity: 0.05,
        profit_loss: 112.50,
        profit_loss_percent: 5.0,
        timestamp: '2026-01-10T10:30:00Z',
        status: 'CLOSED',
        strategy: 'Trend Following'
    }}
    onPress={() => console.log('تفاصيل الصفقة')}
    compact={false}
/>
```

**مثال الإخراج:**
```
┌────────────────────────────┐
│ 🪙 BTC        [شراء] [مُغلق]│
│ Trend Following            │
│                            │
│ سعر الدخول    $45,000.00  │
│ سعر الخروج    $47,250.00  │
│ الكمية        0.05 BTC     │
│ الإجمالي      $2,250.00    │
│ ─────────────────────────  │
│ الربح/الخسارة              │
│         +$112.50 ↑ 5.00%   │
│                            │
│ 🕐 10 يناير 2026، 10:30 ص  │
└────────────────────────────┘
```

**الميزات:**
- ✅ عرض كامل أو مضغوط
- ✅ شارات للنوع والحالة
- ✅ تفاصيل شاملة
- ✅ قابل للنقر

---

### 4. AssetCard
**الوصف:** بطاقة موحدة لعرض الأصول

**الاستخدام:**
```javascript
import AssetCard from '../components/AssetCard';

<AssetCard
    asset={{
        symbol: 'BTCUSDT',
        amount: 0.05,
        value_usd: 2250.00,
        current_price: 45000,
        entry_price: 42000,
        profit_loss: 150.00,
        profit_loss_percent: 7.14,
        allocation_percent: 25.5
    }}
    onPress={() => console.log('تفاصيل الأصل')}
    showChart={false}
/>
```

**مثال الإخراج:**
```
┌────────────────────────────┐
│ 🪙 BTC           [25.5%]   │
│ 0.05 BTC                   │
│                            │
│ القيمة الحالية             │
│         $2,250.00          │
│ السعر         $45,000.00   │
│ سعر الدخول    $42,000.00   │
│ ─────────────────────────  │
│     +$150.00 ↑ 7.14%       │
└────────────────────────────┘
```

**الميزات:**
- ✅ أيقونة العملة
- ✅ نسبة التخصيص
- ✅ الربح/الخسارة
- ✅ خيار عرض مخطط

---

### 5. BalanceCard
**الوصف:** بطاقة موحدة لعرض الرصيد

**الاستخدام:**
```javascript
import BalanceCard from '../components/BalanceCard';

<BalanceCard
    balance={10250.75}
    todayChange={125.50}
    todayChangePercent={1.24}
    totalProfit={1250.75}
    totalProfitPercent={13.89}
    currency="USDT"
    loading={false}
/>
```

**مثال الإخراج:**
```
┌────────────────────────────┐
│ الرصيد الإجمالي            │
│                            │
│   10,250.75  USDT          │
│ ────────────────────────── │
│ 📅 اليوم                   │
│   +$125.50 ↑ 1.24%         │
│                            │
│ 📈 الإجمالي                │
│   +$1,250.75 ↑ 13.89%      │
└────────────────────────────┘
```

**الميزات:**
- ✅ رصيد بحجم كبير
- ✅ التغيير اليومي
- ✅ الربح الإجمالي
- ✅ حالة تحميل

---

## 🛠️ دوال التنسيق الموحدة

### formatters.js
**الموقع:** `src/utils/formatters.js`

#### 1. formatNumber
```javascript
import { formatNumber } from '../utils/formatters';

formatNumber(1234567.89, 2)  // "1.23M"
formatNumber(12345.67, 2)    // "12.35K"
formatNumber(123.45, 2)      // "123.45"
```

#### 2. formatCurrency
```javascript
import { formatCurrency } from '../utils/formatters';

formatCurrency(1234.56)           // "$1,234.56"
formatCurrency(1234.56, true)     // "+$1,234.56"
formatCurrency(-1234.56)          // "-$1,234.56"
```

#### 3. formatPercentage
```javascript
import { formatPercentage } from '../utils/formatters';

formatPercentage(12.345)          // "12.35%"
formatPercentage(12.345, true)    // "+12.35%"
formatPercentage(-12.345)         // "-12.35%"
```

#### 4. formatDate
```javascript
import { formatDate } from '../utils/formatters';

formatDate('2026-01-10T10:30:00Z', 'short')   // "2026-01-10"
formatDate('2026-01-10T10:30:00Z', 'medium')  // "10 يناير 2026، 10:30"
formatDate('2026-01-10T10:30:00Z', 'long')    // "10 يناير 2026، 10:30:00 ص"
```

#### 5. formatTimeAgo
```javascript
import { formatTimeAgo } from '../utils/formatters';

formatTimeAgo('2026-01-10T10:25:00Z')  // "منذ 5 دقيقة"
formatTimeAgo('2026-01-10T08:00:00Z')  // "منذ 2 ساعة"
formatTimeAgo('2026-01-09T10:30:00Z')  // "منذ يوم واحد"
```

#### 6. formatCoinSymbol
```javascript
import { formatCoinSymbol } from '../utils/formatters';

formatCoinSymbol('BTCUSDT')  // "BTC"
formatCoinSymbol('ETHUSDT')  // "ETH"
```

#### 7. formatQuantity
```javascript
import { formatQuantity } from '../utils/formatters';

formatQuantity(0.00012345, 8)  // "0.00012345"
formatQuantity(1.00000000, 8)  // "1"
formatQuantity(0.50000000, 8)  // "0.5"
```

---

## 🎨 إرشادات الاستخدام

### متى تستخدم كل مكون؟

#### ProfitLossIndicator
استخدمه عندما تريد عرض:
- ✅ الربح/الخسارة في بطاقة
- ✅ التغيير اليومي
- ✅ أداء الصفقة
- ✅ أداء الأصل

#### StatCard
استخدمه عندما تريد عرض:
- ✅ إحصائية رئيسية
- ✅ KPI (مؤشر أداء رئيسي)
- ✅ ملخص سريع
- ✅ بطاقة Dashboard

#### TradeCard
استخدمه عندما تريد عرض:
- ✅ صفقة في القائمة
- ✅ تفاصيل الصفقة
- ✅ سجل الصفقات
- ✅ المراكز النشطة

#### AssetCard
استخدمه عندما تريد عرض:
- ✅ أصل في المحفظة
- ✅ عملة مملوكة
- ✅ توزيع الأصول
- ✅ قيمة الحيازة

#### BalanceCard
استخدمه عندما تريد عرض:
- ✅ الرصيد الرئيسي
- ✅ Dashboard الرئيسي
- ✅ ملخص المحفظة
- ✅ نظرة عامة سريعة

---

## 🔧 أمثلة عملية

### Dashboard Screen
```javascript
import BalanceCard from '../components/BalanceCard';
import StatCard from '../components/StatCard';

<ScrollView>
    <BalanceCard
        balance={portfolio.balance}
        todayChange={portfolio.todayChange}
        todayChangePercent={portfolio.todayChangePercent}
    />
    
    <View style={styles.statsRow}>
        <StatCard
            title="إجمالي الصفقات"
            value={stats.totalTrades}
            icon="activity"
            trend="up"
        />
        <StatCard
            title="معدل النجاح"
            value={`${stats.winRate}%`}
            icon="target"
            valueColor={theme.colors.success}
        />
    </View>
</ScrollView>
```

### Portfolio Screen
```javascript
import AssetCard from '../components/AssetCard';

<FlatList
    data={assets}
    renderItem={({ item }) => (
        <AssetCard
            asset={item}
            onPress={() => navigateToAssetDetails(item)}
        />
    )}
    keyExtractor={(item) => item.symbol}
/>
```

### Trade History Screen
```javascript
import TradeCard from '../components/TradeCard';

<FlatList
    data={trades}
    renderItem={({ item }) => (
        <TradeCard
            trade={item}
            onPress={() => navigateToTradeDetails(item)}
        />
    )}
    keyExtractor={(item) => item.id}
/>
```

---

## ✅ قائمة التحقق

عند استخدام المكونات، تأكد من:

- [ ] استخدام `formatCurrency` لجميع المبالغ
- [ ] استخدام `formatPercentage` لجميع النسب
- [ ] استخدام `formatDate` لجميع التواريخ
- [ ] استخدام `ProfitLossIndicator` للأرباح/الخسائر
- [ ] توحيد الألوان من `theme.colors`
- [ ] اختبار على أحجام شاشات مختلفة
- [ ] التأكد من قابلية القراءة

---

## 🎯 أفضل الممارسات

### 1. الاتساق
```javascript
// ✅ جيد - استخدام المكونات الموحدة
<ProfitLossIndicator value={profit} percentage={profitPercent} />

// ❌ سيء - كود مخصص
<Text style={{ color: profit > 0 ? 'green' : 'red' }}>
    {profit > 0 ? '+' : ''}{profit}$
</Text>
```

### 2. التنسيق
```javascript
// ✅ جيد - استخدام دوال التنسيق
<Text>{formatCurrency(value)}</Text>

// ❌ سيء - تنسيق يدوي
<Text>${value.toFixed(2)}</Text>
```

### 3. إعادة الاستخدام
```javascript
// ✅ جيد - مكون واحد لعرض جميع الصفقات
<TradeCard trade={trade} />

// ❌ سيء - كود مكرر لكل صفقة
<View>
    <Text>{trade.symbol}</Text>
    <Text>{trade.side}</Text>
    ...
</View>
```

---

## 📊 التأثير

### قبل التوحيد
- ❌ تنسيقات مختلفة
- ❌ ألوان غير متسقة
- ❌ كود مكرر
- ❌ صعوبة الصيانة

### بعد التوحيد
- ✅ تنسيق موحد
- ✅ ألوان متسقة
- ✅ مكونات قابلة لإعادة الاستخدام
- ✅ سهولة الصيانة

---

## 🔄 التحديثات المستقبلية

### المخطط لها
- 🔄 CircularProgress لمعدل النجاح
- 🔄 MiniChart للأصول
- 🔄 FilterBar لسجل الصفقات
- 🔄 SearchBar للمحفظة
- 🔄 TimeframeSwitcher للرسوم البيانية

---

**آخر تحديث:** 10 يناير 2026  
**الحالة:** ✅ جاهز للاستخدام الكامل
