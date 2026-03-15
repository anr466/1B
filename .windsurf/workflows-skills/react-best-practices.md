---
description: React Best Practices - مهارة Vercel لأفضل ممارسات React في تطبيق التداول
---

# React Best Practices - Trading App Edition

**Source**: https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices
**Adapted for**: React Native Trading App (mobile_app/TradingApp/)

---

## 🎯 متى تُطبق هذه المهارة؟

طبّق هذه القواعد عند:
- إنشاء أو تعديل React/React Native components
- تحسين الأداء (Performance Optimization)
- إصلاح مشاكل Re-rendering
- تحسين حجم Bundle Size
- معالجة Data Fetching issues

---

## 📋 Quick Reference - الأولويات

### 1️⃣ CRITICAL - Eliminating Waterfalls
```javascript
// ❌ BAD: Sequential awaits
const user = await fetchUser();
const posts = await fetchPosts(user.id);

// ✅ GOOD: Parallel execution
const [user, posts] = await Promise.all([
  fetchUser(),
  fetchPosts()
]);
```

### 2️⃣ CRITICAL - Bundle Size Optimization
```javascript
// ❌ BAD: Barrel imports
import { Button, Modal, Card } from '@/components';

// ✅ GOOD: Direct imports
import Button from '@/components/Button';
import Modal from '@/components/Modal';
```

### 3️⃣ HIGH - Re-render Optimization
```javascript
// ❌ BAD: Object created every render
<Component config={{ theme: 'dark' }} />

// ✅ GOOD: Memoized or extracted
const CONFIG = { theme: 'dark' };
<Component config={CONFIG} />
```

### 4️⃣ MEDIUM - useEffect Dependencies
```javascript
// ❌ BAD: Missing dependencies
useEffect(() => {
  fetchData(userId);
}, []); // userId not in deps!

// ✅ GOOD: All dependencies listed
useEffect(() => {
  fetchData(userId);
}, [userId]);
```

---

## 🛡️ PROTECTED ZONES - DO NOT MODIFY

```
PROTECTED (NO TOUCH):
├── src/components/charts/*          ← ALL chart components
├── src/services/*                   ← ALL API services
├── src/context/*                    ← Context providers (unless performance issue)
├── src/navigation/*                 ← Navigation setup
└── src/theme/*                      ← Theme configuration
```

---

## 📖 Core Rules Summary

### 1. Eliminating Waterfalls (CRITICAL)
- **1.1** Defer `await` until needed
- **1.2** Parallelize independent operations with `Promise.all()`
- **1.3** Prevent waterfall chains in API routes
- **1.4** Strategic Suspense boundaries

### 2. Bundle Size Optimization (CRITICAL)
- **2.1** Avoid barrel file imports
- **2.2** Conditional module loading
- **2.3** Dynamic imports for heavy components
- **2.4** Preload based on user intent

### 3. Re-render Optimization (MEDIUM-HIGH)
- **3.1** Calculate derived state during rendering
- **3.2** Extract to memoized components
- **3.3** Use `React.memo()` wisely
- **3.4** Narrow Effect dependencies
- **3.5** Use functional `setState` updates
- **3.6** Use `useRef` for transient values

### 4. Client-Side Data Fetching (MEDIUM-HIGH)
- **4.1** Deduplicate global event listeners
- **4.2** Use passive listeners for scroll
- **4.3** Minimize localStorage data

### 5. Rendering Performance (MEDIUM)
- **5.1** Hoist static JSX elements
- **5.2** Use explicit conditional rendering
- **5.3** Optimize SVG precision
- **5.4** Use `useTransition` for non-urgent updates

### 6. JavaScript Performance (LOW-MEDIUM)
- **6.1** Cache repeated function calls
- **6.2** Use `Set/Map` for O(1) lookups
- **6.3** Early return from functions
- **6.4** Combine multiple array iterations

---

## 🔧 Trading App Specific Guidelines

### State Management
```javascript
// ✅ GOOD: Use Context for trading mode
const { tradingMode } = useTradingModeContext();

// ✅ GOOD: Use Context for portfolio
const { portfolio, fetchPortfolio } = usePortfolioContext();

// ❌ BAD: Don't duplicate state
const [localPortfolio, setLocalPortfolio] = useState(null);
```

### API Calls
```javascript
// ✅ GOOD: Debounce and cancel
const loadData = useCallback(async () => {
  const now = Date.now();
  if (now - lastRefreshRef.current < DEBOUNCE_DELAY) return;
  lastRefreshRef.current = now;
  
  const response = await DatabaseApiService.getPortfolio(userId);
  if (!isMountedRef.current) return; // ✅ Check mounted
  setData(response);
}, [userId]);
```

### Performance Optimization
```javascript
// ✅ GOOD: Memoize expensive calculations
const sortedTrades = useMemo(() => 
  trades.sort((a, b) => b.timestamp - a.timestamp),
  [trades]
);

// ✅ GOOD: Lazy initial state
const [state, setState] = useState(() => {
  return expensiveComputation();
});
```

---

## 🚨 Common Mistakes to Avoid

### 1. Re-rendering Issues
```javascript
// ❌ BAD: New object every render
function TradeCard({ trade }) {
  const style = { backgroundColor: trade.pnl > 0 ? 'green' : 'red' };
  return <View style={style}>...</View>;
}

// ✅ GOOD: Compute inline or use useMemo
function TradeCard({ trade }) {
  return (
    <View style={{ backgroundColor: trade.pnl > 0 ? 'green' : 'red' }}>
      ...
    </View>
  );
}
```

### 2. Effect Dependencies
```javascript
// ❌ BAD: Object in deps causes infinite loop
useEffect(() => {
  fetchData(config);
}, [config]); // config is new object every render!

// ✅ GOOD: Extract primitive values
const { userId, mode } = config;
useEffect(() => {
  fetchData(config);
}, [userId, mode]);
```

### 3. Unnecessary useCallback
```javascript
// ❌ BAD: useCallback for simple handler
const handlePress = useCallback(() => {
  console.log('pressed');
}, []);

// ✅ GOOD: No callback needed
const handlePress = () => {
  console.log('pressed');
};
```

---

## 📚 Resources

- **Full Documentation**: https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/AGENTS.md
- **Vercel Blog**: https://vercel.com/blog/introducing-react-best-practices
- **React Docs**: https://react.dev/learn/you-might-not-need-an-effect

---

## ✅ Checklist Before Committing

- [ ] No unnecessary re-renders (use React DevTools Profiler)
- [ ] All useEffect dependencies listed correctly
- [ ] No waterfall API calls (use Promise.all where possible)
- [ ] Direct imports instead of barrel files
- [ ] Expensive calculations memoized with useMemo
- [ ] Event handlers stable (use useCallback only when needed)
- [ ] Mounted check for async operations (`isMountedRef`)
- [ ] Debouncing for frequent API calls

---

**Note**: هذه المهارة مكمّلة لـ Frontend Design Skill. استخدمهما معاً للحصول على أفضل النتائج.
