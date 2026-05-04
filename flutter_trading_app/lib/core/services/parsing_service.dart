class ParsingService {
  const ParsingService._();

  static Map<String, dynamic> asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return Map<String, dynamic>.from(value);
    return <String, dynamic>{};
  }

  static int asInt(dynamic value, {int fallback = 0}) {
    if (value == null) return fallback;
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value.toString()) ?? fallback;
  }

  static double asDouble(dynamic value, {double fallback = 0}) {
    if (value == null) return fallback;
    if (value is num) return value.toDouble();
    final parsed = double.tryParse(
      value.toString().replaceAll('%', '').replaceAll(',', '').trim(),
    );
    return parsed ?? fallback;
  }

  static double? asNullableDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(
      value.toString().replaceAll(',', '').replaceAll('%', '').trim(),
    );
  }
}
