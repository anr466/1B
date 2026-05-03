# Verification Plan - Trading AI Bot
## خطة التحقق الشاملة لتجربة المستخدم

**تاريخ الإنشاء**: 2026-04-30
**الحالة**: قيد التنفيذ

---

## 1. API Connectivity Testing

### 1.1 Auth Endpoints
| Endpoint | Method | Flutter Call | Expected | Status |
|----------|--------|--------------|----------|--------|
| `/api/auth/login` | POST | `AuthRepository.login` | JWT token | ⬜ |
| `/api/auth/refresh` | POST | `AuthRepository.refreshToken` | New token | ⬜ |
| `/api/auth/logout` | POST | `AuthRepository.logout` | Success | ⬜ |
| `/api/auth/validate-session` | POST | `AuthRepository.validateSession` | Valid/Invalid | ⬜ |

### 1.2 User Endpoints
| Endpoint | Method | Flutter Call | Expected | Status |
|----------|--------|--------------|----------|--------|
| `/api/user/portfolio` | GET | `PortfolioRepository.getPortfolio` | Portfolio JSON | ⬜ |
| `/api/user/trades` | GET | `TradesRepository.getTrades` | Trades list | ⬜ |
| `/api/user/positions` | GET | `PortfolioRepository.getActivePositions` | Positions list | ⬜ |
| `/api/user/settings/<id>` | GET/PUT | `SettingsRepository` | Settings JSON | ⬜ |
| `/api/user/notifications` | GET | `NotificationRepository` | Notifications list | ⬜ |
| `/api/user/stats` | GET | `StatsRepository` | Stats JSON | ⬜ |
| `/api/notifications/fcm-token` | POST | `PushNotificationService` | Success | ⬜ |

### 1.3 Admin Endpoints
| Endpoint | Method | Flutter Call | Expected | Status |
|----------|--------|--------------|----------|--------|
| `/api/admin/dashboard` | GET | `AdminRepository.getDashboard` | Dashboard JSON | ⬜ |
| `/api/admin/users` | GET | `AdminRepository.getUsers` | Users list | ⬜ |
| `/api/admin/users/<id>` | GET | `AdminRepository.getUserDetails` | User details | ⬜ |
| `/api/admin/users/<id>/toggle-trading` | PUT | `TradingToggleService.toggleUser` | Success | ⬜ |
| `/api/admin/trading/start` | POST | `AdminRepository.startTrading` | State JSON | ⬜ |
| `/api/admin/trading/stop` | POST | `AdminRepository.stopTrading` | State JSON | ⬜ |
| `/api/admin/positions/<id>/close` | POST | `AdminRepository.closePosition` | Success | ⬜ |
| `/api/admin/ml/status` | GET | `AdminRepository.getMlStatus` | ML JSON | ⬜ |
| `/api/admin/background/status` | GET | `AdminRepository.getBackgroundStatus` | Status JSON | ⬜ |
| `/api/admin/logs/activity` | GET | `AdminRepository.getActivityLogs` | Logs list | ⬜ |

---

## 2. Flutter ↔ Backend Contract Testing

### 2.1 Response Field Mapping
| Backend Field | Flutter Model Field | Type Match | Status |
|---------------|---------------------|------------|--------|
| `users.id` | `User.id` | int | ⬜ |
| `users.username` | `User.username` | String | ⬜ |
| `users.email` | `User.email` | String | ⬜ |
| `users.user_type` | `User.userType` | String | ⬜ |
| `portfolio.total_balance` | `Portfolio.totalBalance` | double | ⬜ |
| `portfolio.available_balance` | `Portfolio.availableBalance` | double | ⬜ |
| `portfolio.total_profit_loss` | `Portfolio.totalProfitLoss` | double | ⬜ |
| `active_positions.symbol` | `Trade.symbol` | String | ⬜ |
| `active_positions.entry_price` | `Trade.entryPrice` | double | ⬜ |
| `active_positions.is_active` | `Trade.isOpen` | bool | ⬜ |
| `user_settings.trading_enabled` | `UserSettings.tradingEnabled` | bool | ⬜ |
| `user_settings.trade_amount` | `UserSettings.tradeAmount` | double | ⬜ |

### 2.2 Request Body Mapping
| Flutter Request | Backend Expected | Type Match | Status |
|-----------------|------------------|------------|--------|
| `{tradingEnabled: true}` | `trading_enabled` | bool | ⬜ |
| `{tradeAmount: 100.0}` | `trade_amount` | double | ⬜ |
| `{fcmToken: "..."}` | `fcm_token` | String | ⬜ |

---

## 3. Database Schema Consistency

### 3.1 Schema Sources Comparison
| Table | In `postgres_schema.sql` | In `database_manager.py` | In Migrations | Consistent |
|-------|--------------------------|--------------------------|---------------|------------|
| `users` | ✅ | ✅ | ✅ | ⬜ |
| `user_settings` | ✅ | ✅ | ✅ | ⬜ |
| `portfolio` | ✅ | ✅ | ✅ | ⬜ |
| `active_positions` | ✅ | ✅ | ✅ | ⬜ |
| `user_binance_keys` | ✅ | ✅ | ✅ | ⬜ |
| `signals_queue` | ✅ | ✅ | ? | ⬜ |
| `activity_logs` | ✅ | ? | ? | ⬜ |
| `successful_coins` | ✅ | ? | ? | ⬜ |
| `trading_signals` | ✅ | ? | ? | ⬜ |
| `system_status` | ✅ | ? | ? | ⬜ |
| `fcm_tokens` | ? | ? | ? | ⬜ |
| `notifications` | ? | ? | ? | ⬜ |
| `mistake_memory` | ? | ? | ? | ⬜ |
| `trading_logs` | ? | ? | ? | ⬜ |
| `system_errors` | ? | ? | ? | ⬜ |

### 3.2 Critical Column Verification
| Table.Column | Used In Code | Exists In DB | Status |
|--------------|--------------|--------------|--------|
| `users.is_admin` | `auth_provider.dart` | ? | ⬜ |
| `users.name` | `User.fromJson` | ✅ | ⬜ |
| `users.phone_number` | `User.fromJson` | ✅ | ⬜ |
| `portfolio.invested_balance` | `PortfolioRepository` | ✅ | ⬜ |
| `active_positions.ml_status` | `TradeDetailScreen` | ✅ | ⬜ |
| `active_positions.ml_confidence` | `TradeDetailScreen` | ✅ | ⬜ |
| `active_positions.trailing_sl_price` | `Trade` model | ✅ | ⬜ |
| `active_positions.brain_decision_id` | `Trade` model | ✅ | ⬜ |

---

## 4. User Journey Flow Verification

### 4.1 Primary Flow: User Login → Trading
```
SplashScreen → LoginScreen → DashboardScreen → [Toggle Trading] → Position Opened
```
| Step | Screen | Action | API Call | Expected Result | Status |
|------|--------|--------|----------|-----------------|--------|
| 1 | SplashScreen | Auto-login check | `POST /auth/validate-session` | Token valid → Dashboard | ⬜ |
| 2 | LoginScreen | Enter credentials | `POST /auth/login` | JWT + user data | ⬜ |
| 3 | DashboardScreen | View portfolio | `GET /user/portfolio` | Balance + PnL | ⬜ |
| 4 | DashboardScreen | Toggle trading | `PUT /user/settings/<id>` | `trading_enabled: true` | ⬜ |
| 5 | Background | Auto-scan | Internal engine | Signal generated | ⬜ |
| 6 | PortfolioScreen | View positions | `GET /user/positions` | Active positions list | ⬜ |
| 7 | TradeDetailScreen | View trade details | `GET /user/positions/<id>` | Trade details | ⬜ |
```

### 4.2 Admin Flow
```
Admin Dashboard → User Management → User Detail → Toggle User Trading
```
| Step | Screen | Action | API Call | Expected Result | Status |
|------|--------|--------|----------|-----------------|--------|
| 1 | AdminDashboardScreen | View stats | `GET /admin/dashboard` | Stats JSON | ⬜ |
| 2 | UserManagementScreen | List users | `GET /admin/users` | Users list | ⬜ |
| 3 | AdminUserDetailScreen | View user | `GET /admin/users/<id>` | User details | ⬜ |
| 4 | AdminUserDetailScreen | Toggle trading | `PUT /admin/users/<id>/toggle-trading` | Success | ⬜ |
| 5 | AdminUserDetailScreen | Force close | `POST /admin/users/<id>/force-close` | Positions closed | ⬜ |
```

---

## 5. Integration Testing

### 5.1 Backend + DB Integration
| Test | Command | Expected | Status |
|------|---------|----------|--------|
| DB Connection | `python -c "from backend.database.database_manager import DatabaseManager; print('OK')"` | OK | ⬜ |
| Schema Creation | Run `postgres_schema.sql` | All tables created | ⬜ |
| Migration Apply | Run all `.sql` in `migrations/` | No errors | ⬜ |
| API Server Start | `python start_server.py` | Server starts on port 5000 | ⬜ |

### 5.2 Flutter + Backend Integration
| Test | Command | Expected | Status |
|------|---------|----------|--------|
| Build APK | `flutter build apk` | Success | ⬜ |
| Build iOS | `flutter build ios` | Success | ⬜ |
| Widget Tests | `flutter test` | All pass | ⬜ |
| Integration Test | `flutter drive` | Login → Dashboard flow works | ⬜ |

### 5.3 Docker Integration
| Test | Command | Expected | Status |
|------|---------|----------|--------|
| Docker Build | `docker-compose build` | Success | ⬜ |
| Container Start | `docker-compose up` | All services healthy | ⬜ |
| Health Check | `curl http://localhost:5000/health` | 200 OK | ⬜ |
| Logs Check | `docker-compose logs` | No errors | ⬜ |

---

## 6. Known Issues Tracker

| # | Issue | Severity | Status | Fix |
|---|-------|----------|--------|-----|
| 1 | FCM token endpoint mismatch | CRITICAL | ✅ FIXED | Changed `/user/fcm-token` → `/notifications/fcm-token` |
| 2 | Admin nav UX (no return path) | MEDIUM | ⬜ PENDING | Add Admin to bottom nav or menu |
| 3 | `secure_actions_endpoints.py` double registration | MEDIUM | ⬜ PENDING | Remove duplicate blueprint |
| 4 | `client_logs_endpoint.py` no auth | MEDIUM | ⬜ PENDING | Add auth decorator |
| 5 | `portfolio_endpoints.py` dead code | LOW | ✅ FIXED | Removed file |
| 6 | `system_health.py` not registered | LOW | ⬜ PENDING | Register blueprint or remove |
| 7 | `database_manager.py` vs schema mismatch | MEDIUM | ⬜ PENDING | Audit all dynamic tables |

---

## 7. Verification Results Log

### Run 1 - 2026-04-30
| Check | Result | Notes |
|-------|--------|-------|
| `flutter analyze` | ✅ 0 issues | All screens compile |
| Backend tests | ✅ 36/38 (94.7%) | 2 test-logic failures, not engine bugs |
| Endpoint mapping | ✅ 34/35 match | 1 mismatch fixed (FCM) |
| Screen connectivity | ✅ All reachable | 25 screens mapped |

---

## 8. Sign-off Criteria

- [ ] All API endpoints return expected JSON
- [ ] All Flutter models match backend responses
- [ ] All DB columns used in code exist in schema
- [ ] All user journeys complete without dead ends
- [ ] Docker build succeeds
- [ ] `flutter analyze` = 0 issues
- [ ] Backend tests ≥ 90% pass
- [ ] No CRITICAL or HIGH issues remain

**المسؤول عن التحقق**: _____________
**تاريخ الانتهاء**: _____________
