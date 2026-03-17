/// Notification Settings Model — تفضيلات إشعارات المستخدم
/// منطق صافي — لا يستورد Flutter
class NotificationSettingsModel {
  final bool pushEnabled;
  final bool tradeNotifications;
  final bool priceAlerts;
  final bool errorNotifications;
  final bool dailySummary;

  final bool notifyNewDeal;
  final bool notifyDealProfit;
  final bool notifyDealLoss;
  final bool notifyDailyProfit;
  final bool notifyDailyLoss;
  final bool notifyLowBalance;

  final bool notifySecurityAlerts;
  final bool notifySystemStatus;
  final bool notifyMaintenance;

  final bool quietHoursEnabled;
  final String quietHoursStart;
  final String quietHoursEnd;

  final bool notifyLargeProfit;
  final bool notifyLargeLoss;
  final double profitThreshold;
  final double lossThreshold;

  final bool weeklySummary;
  final bool monthlyReport;

  final bool cumulativeLossAlertEnabled;
  final double cumulativeLossThresholdUsd;
  final bool endOfDayReportEnabled;
  final String endOfDayReportTime;

  const NotificationSettingsModel({
    this.pushEnabled = false,
    this.tradeNotifications = false,
    this.priceAlerts = false,
    this.errorNotifications = false,
    this.dailySummary = false,
    this.notifyNewDeal = false,
    this.notifyDealProfit = false,
    this.notifyDealLoss = false,
    this.notifyDailyProfit = false,
    this.notifyDailyLoss = false,
    this.notifyLowBalance = false,
    this.notifySecurityAlerts = false,
    this.notifySystemStatus = false,
    this.notifyMaintenance = false,
    this.quietHoursEnabled = false,
    this.quietHoursStart = '22:00',
    this.quietHoursEnd = '08:00',
    this.notifyLargeProfit = false,
    this.notifyLargeLoss = false,
    this.profitThreshold = 0,
    this.lossThreshold = 0,
    this.weeklySummary = false,
    this.monthlyReport = false,
    this.cumulativeLossAlertEnabled = false,
    this.cumulativeLossThresholdUsd = 0,
    this.endOfDayReportEnabled = false,
    this.endOfDayReportTime = '23:00',
  });

  factory NotificationSettingsModel.fromJson(Map<String, dynamic> json) {
    double asDouble(dynamic v, double fallback) {
      if (v == null) return fallback;
      if (v is num) return v.toDouble();
      return double.tryParse(v.toString()) ?? fallback;
    }

    bool asBool(dynamic v, bool fallback) {
      if (v == null) return fallback;
      if (v is bool) return v;
      if (v is num) return v != 0;
      final s = v.toString().toLowerCase();
      if (s == 'true' || s == '1') return true;
      if (s == 'false' || s == '0') return false;
      return fallback;
    }

    return NotificationSettingsModel(
      pushEnabled: asBool(json['pushEnabled'], false),
      tradeNotifications: asBool(json['tradeNotifications'], false),
      priceAlerts: asBool(json['priceAlerts'], false),
      errorNotifications: asBool(json['errorNotifications'], false),
      dailySummary: asBool(json['dailySummary'], false),
      notifyNewDeal: asBool(json['notifyNewDeal'], false),
      notifyDealProfit: asBool(json['notifyDealProfit'], false),
      notifyDealLoss: asBool(json['notifyDealLoss'], false),
      notifyDailyProfit: asBool(json['notifyDailyProfit'], false),
      notifyDailyLoss: asBool(json['notifyDailyLoss'], false),
      notifyLowBalance: asBool(json['notifyLowBalance'], false),
      notifySecurityAlerts: asBool(json['notifySecurityAlerts'], false),
      notifySystemStatus: asBool(json['notifySystemStatus'], false),
      notifyMaintenance: asBool(json['notifyMaintenance'], false),
      quietHoursEnabled: asBool(json['quietHoursEnabled'], false),
      quietHoursStart: json['quietHoursStart']?.toString() ?? '22:00',
      quietHoursEnd: json['quietHoursEnd']?.toString() ?? '08:00',
      notifyLargeProfit: asBool(json['notifyLargeProfit'], false),
      notifyLargeLoss: asBool(json['notifyLargeLoss'], false),
      profitThreshold: asDouble(json['profitThreshold'], 0),
      lossThreshold: asDouble(json['lossThreshold'], 0),
      weeklySummary: asBool(json['weeklySummary'], false),
      monthlyReport: asBool(json['monthlyReport'], false),
      cumulativeLossAlertEnabled: asBool(
        json['cumulativeLossAlertEnabled'] ?? json['notifyDailyLoss'],
        false,
      ),
      cumulativeLossThresholdUsd: asDouble(
        json['cumulativeLossThresholdUsd'] ?? json['lossThreshold'],
        0,
      ),
      endOfDayReportEnabled: asBool(
        json['endOfDayReportEnabled'] ?? json['dailySummary'],
        false,
      ),
      endOfDayReportTime: json['endOfDayReportTime']?.toString() ?? '23:00',
    );
  }

  NotificationSettingsModel copyWith({
    bool? pushEnabled,
    bool? tradeNotifications,
    bool? priceAlerts,
    bool? errorNotifications,
    bool? dailySummary,
    bool? notifyNewDeal,
    bool? notifyDealProfit,
    bool? notifyDealLoss,
    bool? notifyDailyProfit,
    bool? notifyDailyLoss,
    bool? notifyLowBalance,
    bool? notifySecurityAlerts,
    bool? notifySystemStatus,
    bool? notifyMaintenance,
    bool? quietHoursEnabled,
    String? quietHoursStart,
    String? quietHoursEnd,
    bool? notifyLargeProfit,
    bool? notifyLargeLoss,
    double? profitThreshold,
    double? lossThreshold,
    bool? weeklySummary,
    bool? monthlyReport,
    bool? cumulativeLossAlertEnabled,
    double? cumulativeLossThresholdUsd,
    bool? endOfDayReportEnabled,
    String? endOfDayReportTime,
  }) {
    return NotificationSettingsModel(
      pushEnabled: pushEnabled ?? this.pushEnabled,
      tradeNotifications: tradeNotifications ?? this.tradeNotifications,
      priceAlerts: priceAlerts ?? this.priceAlerts,
      errorNotifications: errorNotifications ?? this.errorNotifications,
      dailySummary: dailySummary ?? this.dailySummary,
      notifyNewDeal: notifyNewDeal ?? this.notifyNewDeal,
      notifyDealProfit: notifyDealProfit ?? this.notifyDealProfit,
      notifyDealLoss: notifyDealLoss ?? this.notifyDealLoss,
      notifyDailyProfit: notifyDailyProfit ?? this.notifyDailyProfit,
      notifyDailyLoss: notifyDailyLoss ?? this.notifyDailyLoss,
      notifyLowBalance: notifyLowBalance ?? this.notifyLowBalance,
      notifySecurityAlerts: notifySecurityAlerts ?? this.notifySecurityAlerts,
      notifySystemStatus: notifySystemStatus ?? this.notifySystemStatus,
      notifyMaintenance: notifyMaintenance ?? this.notifyMaintenance,
      quietHoursEnabled: quietHoursEnabled ?? this.quietHoursEnabled,
      quietHoursStart: quietHoursStart ?? this.quietHoursStart,
      quietHoursEnd: quietHoursEnd ?? this.quietHoursEnd,
      notifyLargeProfit: notifyLargeProfit ?? this.notifyLargeProfit,
      notifyLargeLoss: notifyLargeLoss ?? this.notifyLargeLoss,
      profitThreshold: profitThreshold ?? this.profitThreshold,
      lossThreshold: lossThreshold ?? this.lossThreshold,
      weeklySummary: weeklySummary ?? this.weeklySummary,
      monthlyReport: monthlyReport ?? this.monthlyReport,
      cumulativeLossAlertEnabled:
          cumulativeLossAlertEnabled ?? this.cumulativeLossAlertEnabled,
      cumulativeLossThresholdUsd:
          cumulativeLossThresholdUsd ?? this.cumulativeLossThresholdUsd,
      endOfDayReportEnabled:
          endOfDayReportEnabled ?? this.endOfDayReportEnabled,
      endOfDayReportTime: endOfDayReportTime ?? this.endOfDayReportTime,
    );
  }

  Map<String, dynamic> toJson() => {
    'pushEnabled': pushEnabled,
    'tradeNotifications': tradeNotifications,
    'priceAlerts': priceAlerts,
    'errorNotifications': errorNotifications,
    'dailySummary': dailySummary,
    'notifyNewDeal': notifyNewDeal,
    'notifyDealProfit': notifyDealProfit,
    'notifyDealLoss': notifyDealLoss,
    'notifyDailyProfit': notifyDailyProfit,
    'notifyDailyLoss': notifyDailyLoss,
    'notifyLowBalance': notifyLowBalance,
    'notifySecurityAlerts': notifySecurityAlerts,
    'notifySystemStatus': notifySystemStatus,
    'notifyMaintenance': notifyMaintenance,
    'quietHoursEnabled': quietHoursEnabled,
    'quietHoursStart': quietHoursStart,
    'quietHoursEnd': quietHoursEnd,
    'notifyLargeProfit': notifyLargeProfit,
    'notifyLargeLoss': notifyLargeLoss,
    'profitThreshold': profitThreshold,
    'lossThreshold': lossThreshold,
    'weeklySummary': weeklySummary,
    'monthlyReport': monthlyReport,
    'cumulativeLossAlertEnabled': cumulativeLossAlertEnabled,
    'cumulativeLossThresholdUsd': cumulativeLossThresholdUsd,
    'endOfDayReportEnabled': endOfDayReportEnabled,
    'endOfDayReportTime': endOfDayReportTime,
  };
}
