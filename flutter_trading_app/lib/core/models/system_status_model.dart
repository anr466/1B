/// System Status Model — حالة النظام
/// منطق صافي — لا يستورد Flutter
class SystemStatusModel {
  static const int _heartbeatFreshThresholdSec = 15;

  final String state;
  final bool tradingActive;
  final String tradingMode;
  final int errorCount;
  final String? lastError;
  final String? lastUpdated;
  final int uptimeSeconds;
  final String? uptimeFormatted;
  final int heartbeatSecondsAgo;
  final String heartbeatStatus;
  final int totalCycles;
  final Map<String, dynamic>? subsystems;

  // حالة الاتصال بـ Binance
  final bool binanceConnected;
  final double? binanceLatencyMs;
  final String? binanceError;
  final String? binanceErrorDetail;

  // دورة التداول الحية (group_b)
  final int activePositions;
  final int groupBSecondsAgo;
  final String groupBStatus;

  const SystemStatusModel({
    this.state = 'STOPPED',
    this.tradingActive = false,
    this.tradingMode = 'demo',
    this.errorCount = 0,
    this.lastError,
    this.lastUpdated,
    this.uptimeSeconds = 0,
    this.uptimeFormatted,
    this.heartbeatSecondsAgo = -1,
    this.heartbeatStatus = 'unknown',
    this.totalCycles = 0,
    this.subsystems,
    this.binanceConnected = true,
    this.binanceLatencyMs,
    this.binanceError,
    this.binanceErrorDetail,
    this.activePositions = 0,
    this.groupBSecondsAgo = -1,
    this.groupBStatus = 'unknown',
  });

  bool get isRunning => state == 'RUNNING';
  bool get isStopped => state == 'STOPPED';
  bool get isError => state == 'ERROR_STOPPED' || state == 'ERROR';
  bool get isReal => tradingMode == 'real';
  bool get hasHeartbeat => heartbeatSecondsAgo >= 0;

  bool get isHeartbeatFresh =>
      hasHeartbeat && heartbeatSecondsAgo <= _heartbeatFreshThresholdSec;

  bool get isHeartbeatAlive {
    final normalized = heartbeatStatus.toLowerCase();
    return normalized == 'healthy' || normalized == 'warning';
  }

  /// تشغيل فعلي = حالة RUNNING + نبضات حديثة + حالة نبض غير ميتة + اتصال Binance نشط
  bool get isEffectivelyRunning =>
      isRunning && isHeartbeatFresh && isHeartbeatAlive && binanceConnected;

  /// هل دورة التداول نشطة (آخر نشاط < 120 ثانية)
  bool get isCycleActive =>
      isRunning && groupBSecondsAgo >= 0 && groupBSecondsAgo < 120;

  /// تسمية آخر دورة
  String get lastCycleLabel {
    if (groupBSecondsAgo < 0) return 'غير متاح';
    if (groupBSecondsAgo == 0) return 'الآن';
    if (groupBSecondsAgo < 60) return 'منذ $groupBSecondsAgoث';
    final m = groupBSecondsAgo ~/ 60;
    return 'منذ ${m}د'; // ignore: unnecessary_brace_in_string_interps
  }

  /// رسالة حالة الاتصال الحقيقية
  String get connectionStatusMessage {
    if (!binanceConnected) {
      return binanceErrorDetail ?? 'فشل الاتصال بـ Binance';
    }
    if (isEffectivelyRunning) return 'النظام يعمل';
    if (isRunning && !isHeartbeatFresh) return 'النظام يعمل - تأخر في البيانات';
    if (isRunning) return 'النظام يعمل';
    return 'النظام متوقف';
  }

  /// هل يوجد مشكلة في الاتصال
  bool get hasConnectionIssue => !binanceConnected || binanceError != null;

  String get runtimeVerificationLabel {
    if (isEffectivelyRunning) return 'مؤكد';
    if (isRunning && !hasHeartbeat) return 'جارٍ التفعيل';
    if (isRunning && !isHeartbeatFresh) return 'تأخر';
    if (isRunning && !isHeartbeatAlive) return 'فحص...';
    return 'متوقف';
  }

  String get uptimeLabel {
    if ((uptimeFormatted ?? '').isNotEmpty) return uptimeFormatted!;
    if (uptimeSeconds <= 0) return '0ث';

    final d = uptimeSeconds ~/ 86400;
    final h = (uptimeSeconds % 86400) ~/ 3600;
    final m = (uptimeSeconds % 3600) ~/ 60;

    if (d > 0) return '$dي $hس';
    if (h > 0) return '$hس $mد';
    return '$mد';
  }

  String get heartbeatLabel {
    if (heartbeatSecondsAgo < 0) return 'غير متاح';
    return '$heartbeatSecondsAgoث';
  }

  String get heartbeatStatusLabel {
    switch (heartbeatStatus.toLowerCase()) {
      case 'healthy':
        return 'جيد';
      case 'warning':
        return 'تحذير';
      case 'critical':
        return 'حرج';
      default:
        return 'غير معروف';
    }
  }

  factory SystemStatusModel.fromJson(Map<String, dynamic> json) {
    int asInt(dynamic value, {int fallback = 0}) {
      if (value is num) return value.toInt();
      if (value is String) return int.tryParse(value) ?? fallback;
      return fallback;
    }

    double? asDouble(dynamic value) {
      if (value == null) return null;
      if (value is num) return value.toDouble();
      return double.tryParse(value.toString());
    }

    bool asBool(dynamic value, {bool fallback = false}) {
      if (value == null) return fallback;
      if (value is bool) return value;
      if (value is num) return value != 0;
      final normalized = value.toString().toLowerCase();
      if (normalized == 'true' || normalized == '1') return true;
      if (normalized == 'false' || normalized == '0') return false;
      return fallback;
    }

    final rawSubsystems = json['subsystems'];
    final subsystems = rawSubsystems is Map
        ? Map<String, dynamic>.from(rawSubsystems)
        : <String, dynamic>{};

    final hb = subsystems['heartbeat'] ?? json['heartbeat'];
    final heartbeat = hb is Map
        ? Map<String, dynamic>.from(hb)
        : <String, dynamic>{};

    final rawActivity = json['activity_status'];
    final activityStatus = rawActivity is Map
        ? Map<String, dynamic>.from(rawActivity)
        : <String, dynamic>{};

    final gb =
        subsystems['group_b'] ?? activityStatus['group_b'] ?? json['group_b'];
    final groupB = gb is Map
        ? Map<String, dynamic>.from(gb)
        : <String, dynamic>{};

    final gbSecondsAgo = groupB['seconds_ago'] ?? json['group_b_seconds_ago'];
    final gbStatus = groupB['status']?.toString() ?? 'unknown';
    final gbActiveTrades =
        groupB['active_trades'] ?? json['open_positions'] ?? 0;

    final rawMode = (json['trading_mode'] ?? json['mode'] ?? '')
        .toString()
        .toLowerCase();
    final normalizedMode = switch (rawMode) {
      'live' || 'real' => 'real',
      'paper' || 'demo' => 'demo',
      _ => rawMode,
    };

    final heartbeatSecondsAgo =
        heartbeat['seconds_ago'] ?? json['heartbeat_seconds_ago'];
    final heartbeatStatus = heartbeat['status'] ?? json['heartbeat_status'];
    final totalCycles = groupB['total_cycles'] ?? json['total_cycles'];

    return SystemStatusModel(
      state: (json['state'] ?? json['trading_state'] ?? 'STOPPED').toString(),
      tradingActive: asBool(json['trading_active'] ?? json['tradingActive']),
      tradingMode: normalizedMode,
      errorCount: asInt(json['error_count']),
      lastError: (json['last_error'] ?? json['lastError'])?.toString(),
      lastUpdated: (json['last_updated'] ?? json['last_update'])?.toString(),
      uptimeSeconds: asInt(json['uptime']),
      uptimeFormatted: json['uptime_formatted']?.toString(),
      heartbeatSecondsAgo: asInt(heartbeatSecondsAgo, fallback: -1),
      heartbeatStatus: heartbeatStatus?.toString() ?? 'unknown',
      totalCycles: asInt(totalCycles),
      subsystems: subsystems,
      binanceConnected: asBool(
        json['binance_connected'] ?? json['binanceConnected'],
        fallback: false,
      ),
      binanceLatencyMs: asDouble(
        json['binance_latency_ms'] ?? json['binanceLatencyMs'],
      ),
      binanceError: json['binance_error']?.toString(),
      binanceErrorDetail: json['binance_error_detail']?.toString(),
      activePositions: asInt(gbActiveTrades),
      groupBSecondsAgo: asInt(gbSecondsAgo ?? -1, fallback: -1),
      groupBStatus: gbStatus,
    );
  }

  Map<String, dynamic> toJson() => {
    'state': state,
    'trading_active': tradingActive,
    'trading_mode': tradingMode,
    'error_count': errorCount,
    'last_error': lastError,
    'last_updated': lastUpdated,
    'uptime': uptimeSeconds,
    'uptime_formatted': uptimeFormatted,
    'heartbeat_seconds_ago': heartbeatSecondsAgo,
    'heartbeat_status': heartbeatStatus,
    'total_cycles': totalCycles,
    'subsystems': subsystems,
    'binance_connected': binanceConnected,
    'binance_latency_ms': binanceLatencyMs,
    'binance_error': binanceError,
    'binance_error_detail': binanceErrorDetail,
    'active_positions': activePositions,
    'group_b_seconds_ago': groupBSecondsAgo,
    'group_b_status': groupBStatus,
  };
}
