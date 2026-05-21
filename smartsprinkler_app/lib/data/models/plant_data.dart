import 'package:smartsprinkler_app/model/command.dart';

class PlantData {
  final String id;
  final String displayName;
  final String imageUrl;
  final Target target;
  double probabilityOfNeed;
  double soilMoisture;
  int rotaryPosition;
  bool isWatering;

  PlantData({
    required this.id,
    required this.displayName,
    required this.imageUrl,
    required this.target,
    this.probabilityOfNeed = 0.0,
    this.soilMoisture = 0.0,
    this.rotaryPosition = 0,
    this.isWatering = false,
  });

  factory PlantData.fromJson(Map<String, dynamic> json) {
    return PlantData(
      id: json['id'] ?? '',
      displayName: json['display_name'] ?? json['id'] ?? '',
      imageUrl: json['image_url'] ?? '',
      target: Target.values.firstWhere(
        (t) => t.name.toLowerCase() == (json['esp_target'] ?? '').toLowerCase(),
        orElse: () => Target.NAGA_MORICH,
      ),
      probabilityOfNeed: (json['probability_of_need'] ?? 0.0).toDouble(),
      soilMoisture: (json['soil_moisture'] ?? 0.0).toDouble(),
      rotaryPosition: json['rotary_position'] ?? 0,
      isWatering: json['is_watering'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'display_name': displayName,
    'image_url': imageUrl,
    'esp_target': target.name,
    'probability_of_need': probabilityOfNeed,
    'soil_moisture': soilMoisture,
    'rotary_position': rotaryPosition,
    'is_watering': isWatering,
  };
}

class EvidenceNode {
  final String label;
  final int score;
  final String icon;

  const EvidenceNode({
    required this.label,
    required this.score,
    this.icon = 'thermometer',
  });
}

class BayesianPlantStatus {
  final String plantId;
  final double probabilityOfNeed;
  final List<EvidenceNode> evidenceNodes;
  final DateTime fetchedAt;

  BayesianPlantStatus({
    required this.plantId,
    required this.probabilityOfNeed,
    required this.evidenceNodes,
    DateTime? fetchedAt,
  }) : fetchedAt = fetchedAt ?? DateTime.now();

  factory BayesianPlantStatus.fromJson(Map<String, dynamic> json) {
    final evidenceList = <EvidenceNode>[];
    if (json['evidence_nodes'] != null) {
      for (final node in json['evidence_nodes']) {
        evidenceList.add(EvidenceNode(
          label: node['label'] ?? '',
          score: node['score'] ?? 0,
          icon: node['icon'] ?? 'thermometer',
        ));
      }
    }
    return BayesianPlantStatus(
      plantId: json['plant_id'] ?? '',
      probabilityOfNeed: (json['probability_of_need'] ?? 0.0).toDouble(),
      evidenceNodes: evidenceList,
    );
  }
}