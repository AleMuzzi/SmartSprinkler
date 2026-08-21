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
    final vm = context.read<DashboardViewModel>();
    return ChangeNotifierProvider.value(
      value: vm,
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
          _ProbabilityGauge(probability: (plant.probabilityOfNeed * 100).clamp(0, 100), threshold: (plant.threshold * 100).clamp(0, 100)),
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
        const SizedBox(height: 12),
        Stack(
          children: [
            Container(
              height: 8,
              decoration: BoxDecoration(
                color: const Color(0xFFE8EDF2),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            FractionallySizedBox(
              widthFactor: moisture / 100,
              child: Container(
                height: 8,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFF44336), Color(0xFFFFC107), Color(0xFF4CAF50)],
                    stops: [0.0, 0.5, 1.0],
                  ),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
            Positioned.fill(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  return Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Flexible(child: _barLabel('Dry', 0.0, constraints.maxWidth)),
                      Flexible(child: _barLabel('Wet', 1.0, constraints.maxWidth)),
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
  final double threshold;

  const _ProbabilityGauge({required this.probability, required this.threshold});

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

    final bool needs = probability >= threshold;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Probability of Need',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Color(0xFF4A5568),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: needs
                    ? const Color(0xFFF44336).withValues(alpha: 0.12)
                    : const Color(0xFF4CAF50).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                needs ? 'Needs water' : 'OK',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: needs ? const Color(0xFFC62828) : const Color(0xFF2E7D32),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
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
                radiusFactor: 0.9,
                axisLineStyle: const AxisLineStyle(
                  thickness: 0.15,
                  thicknessUnit: GaugeSizeUnit.factor,
                  color: Color(0xFFE8EDF2),
                ),
                pointers: <GaugePointer>[
                  RangePointer(
                    value: probability,
                    width: 0.15,
                    sizeUnit: GaugeSizeUnit.factor,
                    gradient: SweepGradient(
                      colors: const [Color(0xFF4CAF50), Color(0xFFFFC107), Color(0xFFF44336)],
                      stops: const [0.0, 0.5, 1.0],
                    ),
                  ),
                  NeedlePointer(
                    value: probability,
                    needleLength: 0.6,
                    lengthUnit: GaugeSizeUnit.factor,
                    needleStartWidth: 1,
                    needleEndWidth: 4,
                    needleColor: const Color(0xFF2D3748),
                    knobStyle: KnobStyle(
                      knobRadius: 0.08,
                      sizeUnit: GaugeSizeUnit.factor,
                      color: needs ? const Color(0xFFF44336) : const Color(0xFF4CAF50),
                    ),
                  ),
                  MarkerPointer(
                    value: threshold,
                    markerWidth: 10,
                    markerHeight: 10,
                    markerType: MarkerType.invertedTriangle,
                    color: const Color(0xFF718096),
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
                        Text(
                          'Need Water',
                          style: TextStyle(fontSize: 11, color: Color(0xFF718096)),
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
        const SizedBox(height: 8),
        _ProbabilityBarWithThreshold(probability: probability, threshold: threshold),
      ],
    );
  }
}

class _ProbabilityBarWithThreshold extends StatelessWidget {
  final double probability;
  final double threshold;
  const _ProbabilityBarWithThreshold({required this.probability, required this.threshold});

  @override
  Widget build(BuildContext context) {
    final pct = probability.round();
    final thresholdPct = threshold.round();
    final needs = probability >= threshold;

    Color barColor;
    if (pct >= 70) {
      barColor = const Color(0xFFF44336);
    } else if (pct >= 40) {
      barColor = const Color(0xFFFFC107);
    } else {
      barColor = const Color(0xFF4CAF50);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              needs ? 'Watering will trigger (>= $thresholdPct%)' : 'Below threshold (< $thresholdPct%)',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: needs ? const Color(0xFFC62828) : const Color(0xFF2E7D32),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Stack(
          children: [
            Container(
              height: 6,
              decoration: BoxDecoration(
                color: const Color(0xFFE8EDF2),
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            FractionallySizedBox(
              widthFactor: (probability / 100.0).clamp(0.0, 1.0),
              child: Container(
                height: 6,
                decoration: BoxDecoration(
                  color: barColor,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
            FractionallySizedBox(
              widthFactor: (threshold / 100.0).clamp(0.0, 1.0),
              child: Align(
                alignment: Alignment.centerRight,
                child: Container(
                  width: 2,
                  height: 12,
                  margin: const EdgeInsets.only(bottom: 3),
                  color: const Color(0xFF718096),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Align(
          alignment: Alignment.centerRight,
          child: Text(
            'Threshold: $thresholdPct%',
            style: const TextStyle(fontSize: 10, color: Color(0xFF718096)),
          ),
        ),
      ],
    );
  }
}

class _BayesianInsightsSection extends StatelessWidget {
  final PlantData plant;

  const _BayesianInsightsSection({required this.plant});

  String _contributionLabel(int score) {
    if (score >= 70) return 'strongly suggests water';
    if (score >= 40) return 'somewhat suggests water';
    if (score <= 0) return 'suggests no water';
    return 'barely relevant';
  }

  String _rawLabel(EvidenceNode node) {
    switch (node.label) {
      case 'Soil Moisture':
        if (node.score >= 70) return 'dry';
        if (node.score >= 40) return 'moist';
        return 'wet';
      case 'Temperature':
        if (node.score >= 60) return 'hot';
        if (node.score >= 20) return 'warm';
        return 'cold';
      case 'Humidity':
        if (node.score >= 45) return 'low';
        if (node.score >= 15) return 'medium';
        return 'high';
      case 'Cloud Cover':
        if (node.score >= 25) return 'clear sky';
        return 'cloudy';
      case 'Rain Forecast':
        return node.score > 0 ? 'no rain' : 'rain expected';
      default:
        return '';
    }
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

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();
    final status = vm.plantStatuses.firstWhere(
      (s) => s.plantId == plant.id || s.plantId == plant.id.replaceAll('_', ''),
      orElse: () => BayesianPlantStatus(
        plantId: plant.id,
        probabilityOfNeed: plant.probabilityOfNeed,
        threshold: plant.threshold,
        evidenceNodes: [],
      ),
    );

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        elevation: 2,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: ExpansionTile(
              tilePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
              title: Row(
                children: [
                  const Icon(Icons.insights, color: Color(0xFF4CAF50), size: 20),
                  const SizedBox(width: 8),
                  const Text(
                    'Bayesian Insights',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2D3748),
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.info_outline, size: 18, color: Color(0xFF718096)),
                    onPressed: () => _showBayesianInfoDialog(context),
                  ),
                ],
              ),
              children: [
                if (status.evidenceNodes.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: Text(
                      'No evidence data available.',
                      style: TextStyle(color: Color(0xFF718096), fontSize: 13),
                    ),
                  )
                else
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                    child: Column(
                      children: status.evidenceNodes.map((node) {
                        final contribution = _contributionLabel(node.score);
                        final raw = _rawLabel(node);
                        final barColor = node.score >= 70
                            ? const Color(0xFFEF5350)
                            : node.score >= 40
                                ? const Color(0xFFFFCA28)
                                : const Color(0xFF42A5F5);
                        final barWidth = node.score <= 0 ? 0.0 : (node.score / 100.0).clamp(0.0, 1.0);

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(_iconForNode(node.icon), size: 16, color: const Color(0xFF718096)),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      node.label,
                                      style: const TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: Color(0xFF4A5568),
                                      ),
                                    ),
                                  ),
                                  if (raw.isNotEmpty)
                                    Text(
                                      raw,
                                      style: const TextStyle(
                                        fontSize: 11,
                                        color: Color(0xFF718096),
                                      ),
                                    ),
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: node.score > 0
                                          ? const Color(0xFF4CAF50).withValues(alpha: 0.12)
                                          : node.score < 0
                                              ? const Color(0xFFF44336).withValues(alpha: 0.12)
                                              : const Color(0xFFE8EDF2),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      node.score > 0 ? '+${node.score}' : '${node.score}',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: node.score > 0
                                            ? const Color(0xFF2E7D32)
                                            : node.score < 0
                                                ? const Color(0xFFC62828)
                                                : const Color(0xFF718096),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(2),
                                child: LinearProgressIndicator(
                                  value: barWidth,
                                  minHeight: 3,
                                  backgroundColor: const Color(0xFFE8EDF2),
                                  valueColor: AlwaysStoppedAnimation<Color>(barColor),
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                contribution,
                                style: const TextStyle(fontSize: 10, color: Color(0xFFA0AEC0)),
                               ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                  ),
              ],
            ),
          ),
      ),
    );
  }

  void _showBayesianInfoDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('How Bayesian Watering Works'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Probability of Need', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              SizedBox(height: 4),
              Text('The chance your plant needs water, computed from multiple sensor factors using a Bayesian network.', style: TextStyle(fontSize: 13)),
              SizedBox(height: 12),
              Text('Watering is triggered when probability >= threshold (shown below the gauge).', style: TextStyle(fontSize: 12, color: Color(0xFF718096))),
              SizedBox(height: 16),
              Text('Evidence Factors', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              SizedBox(height: 8),
              _InfoRow(icon: Icons.water_drop, label: 'Soil Moisture', desc: 'Dry soil = higher need. Wet soil = lower need.'),
              _InfoRow(icon: Icons.thermostat, label: 'Temperature', desc: 'High temp increases evaporation risk.'),
              _InfoRow(icon: Icons.air, label: 'Humidity', desc: 'Low humidity means faster water loss.'),
              _InfoRow(icon: Icons.cloud, label: 'Cloud Cover', desc: 'Clear sky = more evaporation.'),
              _InfoRow(icon: Icons.cloudy_snowing, label: 'Rain Forecast', desc: 'Rain expected soon = watering skipped.'),
              SizedBox(height: 16),
              Text('Contribution labels:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
              SizedBox(height: 4),
              Text('Score >= 70: strongly suggests water', style: TextStyle(fontSize: 11, color: Color(0xFF718096))),
              Text('Score >= 40: somewhat suggests water', style: TextStyle(fontSize: 11, color: Color(0xFF718096))),
              Text('Score <= 0: suggests no water', style: TextStyle(fontSize: 11, color: Color(0xFF718096))),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Got it')),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String desc;
  const _InfoRow({required this.icon, required this.label, required this.desc});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: const Color(0xFF4CAF50)),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                Text(desc, style: const TextStyle(fontSize: 12, color: Color(0xFF718096))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButtonsSection extends StatefulWidget {
  final PlantData plant;
  final DashboardViewModel vm;

  const _ActionButtonsSection({required this.plant, required this.vm});

  @override
  State<_ActionButtonsSection> createState() => _ActionButtonsSectionState();
}

class _ActionButtonsSectionState extends State<_ActionButtonsSection> {
  final TextEditingController _amountController = TextEditingController();

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  void _dispenseAmount() {
    final amount = int.tryParse(_amountController.text);
    if (amount == null || amount <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid amount in ml')),
      );
      return;
    }
    widget.vm.dispenseAmount(widget.plant, amount);
    _amountController.clear();
  }

  void _showStopDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Stop Watering'),
        content: Text('Stop watering ${widget.plant.displayName}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              widget.vm.stopWatering(widget.plant);
              Navigator.pop(context);
            },
            child: const Text('Stop', style: TextStyle(color: Color(0xFFF44336))),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _amountController,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: 'Amount (ml)',
                    hintText: 'e.g. 100',
                    border: const OutlineInputBorder(),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    suffixText: 'ml',
                  ),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _dispenseAmount,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4CAF50),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                ),
                child: const Icon(Icons.water_drop),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _PresetChip(label: '50ml', onTap: () { _amountController.text = '50'; _dispenseAmount(); }),
              const SizedBox(width: 8),
              _PresetChip(label: '100ml', onTap: () { _amountController.text = '100'; _dispenseAmount(); }),
              const SizedBox(width: 8),
              _PresetChip(label: '200ml', onTap: () { _amountController.text = '200'; _dispenseAmount(); }),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () => DashboardViewModel.showWaterDialog(context, widget.plant),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2196F3),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              icon: const Icon(Icons.water_drop),
              label: const Text('Water Now', style: TextStyle(fontWeight: FontWeight.w600)),
            ),
          ),
          if (widget.plant.isWatering) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => _showStopDialog(context),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFF44336),
                  side: const BorderSide(color: Color(0xFFF44336)),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                icon: const Icon(Icons.stop),
                label: const Text('Stop Watering', style: TextStyle(fontWeight: FontWeight.w600)),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PresetChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _PresetChip({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: const Color(0xFFE3F2FD),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(label, style: const TextStyle(color: Color(0xFF1976D2), fontWeight: FontWeight.w500)),
      ),
    );
  }
}
