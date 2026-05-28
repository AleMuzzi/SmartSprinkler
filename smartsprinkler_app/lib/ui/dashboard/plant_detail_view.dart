import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:syncfusion_flutter_gauges/gauges.dart';

import '../../data/models/plant_data.dart';
import 'dashboard_viewmodel.dart';

class PlantDetailView extends StatelessWidget {
  final PlantData plant;

  const PlantDetailView({super.key, required this.plant});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => DashboardViewModel(),
      child: _PlantDetailContent(plant: plant),
    );
  }
}

class _PlantDetailContent extends StatelessWidget {
  final PlantData plant;

  const _PlantDetailContent({required this.plant});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();
    final livePlant = vm.plants.firstWhere(
      (p) => p.id == plant.id,
      orElse: () => plant,
    );

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: Text(livePlant.displayName),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF2D3748),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            _SensorAndProbabilitySection(plant: livePlant),
            _BayesianInsightsSection(plant: livePlant),
            _ActionButtonsSection(plant: livePlant, vm: vm),
          ],
        ),
      ),
    );
  }
}

class _SensorAndProbabilitySection extends StatelessWidget {
  final PlantData plant;

  const _SensorAndProbabilitySection({required this.plant});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Sensor Data',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFF2D3748),
            ),
          ),
          const SizedBox(height: 20),
          _SoilMoistureBar(moisture: plant.soilMoisture.clamp(0, 100)),
          const SizedBox(height: 24),
          _ProbabilityGauge(probability: (plant.probabilityOfNeed * 100).clamp(0, 100)),
        ],
      ),
    );
  }
}

class _SoilMoistureBar extends StatelessWidget {
  final double moisture;

  const _SoilMoistureBar({required this.moisture});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Soil Moisture',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Color(0xFF4A5568),
              ),
            ),
            Text(
              '${moisture.toInt()}%',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2D3748),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Stack(
          children: [
            Container(
              height: 12,
              decoration: BoxDecoration(
                color: const Color(0xFFE8EDF2),
                borderRadius: BorderRadius.circular(6),
              ),
            ),
            FractionallySizedBox(
              widthFactor: (moisture / 100).clamp(0.0, 1.0),
              child: Container(
                height: 12,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [
                      Color(0xFFEF4444),
                      Color(0xFFFFC107),
                      Color(0xFF4CAF50),
                    ],
                    stops: [0.0, 0.5, 1.0],
                  ),
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
            ),
            Positioned.fill(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  return Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Flexible(
                        child: _barLabel('Dry', 0.0, constraints.maxWidth),
                      ),
                      Flexible(
                        child: _barLabel('Wet', 1.0, constraints.maxWidth),
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _barLabel(String text, double factor, double maxWidth) {
    return Padding(
      padding: EdgeInsets.only(left: factor * maxWidth.clamp(0, maxWidth - 20)),
      child: Text(
        text,
        style: const TextStyle(fontSize: 10, color: Color(0xFFA0AEC0)),
      ),
    );
  }
}

class _ProbabilityGauge extends StatelessWidget {
  final double probability;

  const _ProbabilityGauge({required this.probability});

  @override
  Widget build(BuildContext context) {
    Color needleColor;
    if (probability >= 70) {
      needleColor = const Color(0xFFF44336);
    } else if (probability >= 40) {
      needleColor = const Color(0xFFFFC107);
    } else {
      needleColor = const Color(0xFF4CAF50);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Probability of Need',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: Color(0xFF4A5568),
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 160,
          child: SfRadialGauge(
            axes: <RadialAxis>[
              RadialAxis(
                minimum: 0,
                maximum: 100,
                startAngle: 180,
                endAngle: 0,
                showLabels: false,
                showTicks: false,
                radiusFactor: 0.85,
                axisLineStyle: const AxisLineStyle(
                  thickness: 0.2,
                  thicknessUnit: GaugeSizeUnit.factor,
                  color: Color(0xFFE8EDF2),
                ),
                pointers: <GaugePointer>[
                  RangePointer(
                    value: probability,
                    width: 0.2,
                    sizeUnit: GaugeSizeUnit.factor,
                    gradient: SweepGradient(
                      colors: [
                        const Color(0xFF4CAF50),
                        const Color(0xFFFFC107),
                        const Color(0xFFF44336),
                      ],
                      stops: const [0.0, 0.5, 1.0],
                    ),
                  ),
                  NeedlePointer(
                    value: probability,
                    needleLength: 0.6,
                    lengthUnit: GaugeSizeUnit.factor,
                    needleStartWidth: 1,
                    needleEndWidth: 5,
                    needleColor: needleColor,
                    knobStyle: KnobStyle(
                      knobRadius: 0.1,
                      sizeUnit: GaugeSizeUnit.factor,
                      color: needleColor,
                    ),
                  ),
                ],
                annotations: <GaugeAnnotation>[
                  GaugeAnnotation(
                    widget: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${probability.toInt()}%',
                          style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            color: needleColor,
                          ),
                        ),
                        const Text(
                          'Need Water',
                          style: TextStyle(
                            fontSize: 11,
                            color: Color(0xFF718096),
                          ),
                        ),
                      ],
                    ),
                    angle: 90,
                    positionFactor: 0.0,
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _BayesianInsightsSection extends StatelessWidget {
  final PlantData plant;

  const _BayesianInsightsSection({required this.plant});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();
    final status = vm.plantStatuses.firstWhere(
      (s) => s.plantId == plant.id || s.plantId == plant.id.replaceAll('_', ''),
      orElse: () => BayesianPlantStatus(
        plantId: plant.id,
        probabilityOfNeed: plant.probabilityOfNeed,
        evidenceNodes: [],
      ),
    );

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
          title: const Row(
            children: [
              Icon(Icons.insights, color: Color(0xFF4CAF50), size: 20),
              SizedBox(width: 8),
              Text(
                'Bayesian Insights',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2D3748),
                ),
              ),
            ],
          ),
          children: [
            if (status.evidenceNodes.isEmpty)
              const Padding(
                padding: EdgeInsets.all(20),
                child: Text(
                  'No evidence data available.\nServer must return evidence_nodes breakdown.',
                  style: TextStyle(color: Color(0xFF718096), fontSize: 13),
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                itemCount: status.evidenceNodes.length,
                separatorBuilder: (_, __) =>
                    const Divider(height: 1, color: Color(0xFFE8EDF2)),
                itemBuilder: (context, index) {
                  final node = status.evidenceNodes[index];
                  final isPositive = node.score > 0;
                  final isNegative = node.score < 0;

                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: Row(
                      children: [
                        Icon(
                          _iconForNode(node.icon),
                          size: 16,
                          color: isPositive
                              ? const Color(0xFF4CAF50)
                              : isNegative
                              ? const Color(0xFFF44336)
                              : const Color(0xFFA0AEC0),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            node.label,
                            style: const TextStyle(
                              fontSize: 14,
                              color: Color(0xFF4A5568),
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: isPositive
                                ? const Color(
                                    0xFF4CAF50,
                                  ).withValues(alpha: 0.15)
                                : isNegative
                                ? const Color(
                                    0xFFF44336,
                                  ).withValues(alpha: 0.15)
                                : const Color(0xFFE8EDF2),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            isPositive ? '+${node.score}' : '${node.score}',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: isPositive
                                  ? const Color(0xFF2E7D32)
                                  : isNegative
                                  ? const Color(0xFFC62828)
                                  : const Color(0xFF718096),
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  IconData _iconForNode(String icon) {
    switch (icon) {
      case 'thermometer':
        return Icons.thermostat;
      case 'sun':
        return Icons.wb_sunny;
      case 'cloud-rain':
        return Icons.cloudy_snowing;
      case 'droplet':
        return Icons.water_drop;
      case 'wind':
        return Icons.air;
      default:
        return Icons.info;
    }
  }
}

class _ActionButtonsSection extends StatelessWidget {
  final PlantData plant;
  final DashboardViewModel vm;

  const _ActionButtonsSection({required this.plant, required this.vm});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      child: Column(
        children: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () => vm.waterPlantNow(plant),
              icon: const Icon(Icons.water_drop),
              label: const Text('Manual Override & Water'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2196F3),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                textStyle: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          if (plant.isWatering) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => vm.stopWatering(plant),
                icon: const Icon(Icons.stop_circle),
                label: const Text('Stop Watering'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFF44336),
                  side: const BorderSide(color: Color(0xFFF44336)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
