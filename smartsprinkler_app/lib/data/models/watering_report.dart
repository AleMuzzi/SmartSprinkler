/// A watering proposal produced by the server while running in notification
/// mode.
///
/// Nothing was dispensed: [doses] carries the exact amounts the automatic
/// mode would have delivered, so the user can decide whether to act on them.
class WateringReport {
  const WateringReport({
    required this.id,
    required this.createdAt,
    required this.source,
    required this.title,
    required this.body,
    required this.doses,
  });

  final int id;
  final DateTime createdAt;
  final String source;
  final String title;
  final String body;

  /// `{plantId: dose_ml}`
  final Map<String, double> doses;

  /// Same names used by the web portal, so the report reads identically
  /// on both clients.
  static const Map<String, String> plantLabels = {
    'habanero': 'Habanero',
    'naga_morich': 'Naga Morich',
    'carolina_reaper': 'Carolina Reaper',
    'rosmarino': 'Rosmarino',
  };

  factory WateringReport.fromJson(Map<String, dynamic> json) {
    final rawDoses = json['doses'] as Map<String, dynamic>? ?? const {};
    return WateringReport(
      id: (json['id'] as num?)?.toInt() ?? 0,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      source: json['source'] as String? ?? 'scheduled',
      title: json['title'] as String? ?? 'Pianta da innaffiare',
      body: json['body'] as String? ?? '',
      doses: rawDoses.map(
        (key, value) => MapEntry(key, (value as num).toDouble()),
      ),
    );
  }

  /// Used as the system-notification payload: tapping it re-opens the report
  /// without needing another round-trip to the server.
  Map<String, dynamic> toJson() => {
        'id': id,
        'created_at': createdAt.toIso8601String(),
        'source': source,
        'title': title,
        'body': body,
        'doses': doses,
      };

  double get totalMl => doses.values.fold(0.0, (sum, ml) => sum + ml);

  String labelFor(String plantId) => plantLabels[plantId] ?? plantId;
}
