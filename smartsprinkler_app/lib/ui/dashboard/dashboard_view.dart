import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:syncfusion_flutter_gauges/gauges.dart';

import '../../../data/models/plant_data.dart';
import '../../../data/models/weather_data.dart';
import 'dashboard_viewmodel.dart';
import 'plant_detail_view.dart';

class DashboardView extends StatelessWidget {
  const DashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: SafeArea(
        child: Column(
          children: [
            _TopGaugeSection(),
            Divider(height: 1, color: Color(0xFFE0E4E8)),
            Expanded(child: _PlantCarousel()),
            Divider(height: 1, color: Color(0xFFE0E4E8)),
            _WeatherFooter(),
          ],
        ),
      ),
    );
  }
}

class _TopGaugeSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: 180,
                height: 180,
                child: SfRadialGauge(
                  axes: <RadialAxis>[
                    RadialAxis(
                      minimum: 0,
                      maximum: 100,
                      startAngle: 135,
                      endAngle: 45,
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
                          value: (vm.averageProbabilityOfNeed * 100).clamp(0, 100),
                          width: 0.15,
                          sizeUnit: GaugeSizeUnit.factor,
                          gradient: const SweepGradient(
                            colors: [Color(0xFF4CAF50), Color(0xFFFFC107), Color(0xFFF44336)],
                            stops: [0.0, 0.5, 1.0],
                          ),
                        ),
                        NeedlePointer(
                          value: (vm.averageProbabilityOfNeed * 100).clamp(0, 100),
                          needleLength: 0.6,
                          lengthUnit: GaugeSizeUnit.factor,
                          needleStartWidth: 1,
                          needleEndWidth: 4,
                          needleColor: Color(0xFF2D3748),
                          knobStyle: const KnobStyle(
                            knobRadius: 0.08,
                            sizeUnit: GaugeSizeUnit.factor,
                            color: Color(0xFF2D3748),
                          ),
                        ),
                      ],
                      annotations: <GaugeAnnotation>[
                        GaugeAnnotation(
                          widget: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                '${(vm.averageProbabilityOfNeed * 100).round()}%',
                                style: const TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF2D3748),
                                ),
                              ),
                              const Text(
                                'Avg Need',
                                style: TextStyle(
                                  fontSize: 12,
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
              const SizedBox(width: 24),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _ConnectivityIndicators(esp: vm.espStatus, bayesian: vm.bayesianStatus),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ConnectivityIndicators extends StatelessWidget {
  final ConnectivityStatus esp;
  final ConnectivityStatus bayesian;

  const _ConnectivityIndicators({required this.esp, required this.bayesian});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ConnectionDot(label: 'ESP', status: esp),
        const SizedBox(height: 6),
        _ConnectionDot(label: 'Bayesian', status: bayesian),
      ],
    );
  }
}

class _ConnectionDot extends StatelessWidget {
  final String label;
  final ConnectivityStatus status;

  const _ConnectionDot({required this.label, required this.status});

  @override
  Widget build(BuildContext context) {
    Color dotColor;
    String statusText;

    switch (status) {
      case ConnectivityStatus.connected:
        dotColor = const Color(0xFF4CAF50);
        statusText = 'Online';
        break;
      case ConnectivityStatus.disconnected:
        dotColor = const Color(0xFFF44336);
        statusText = 'Offline';
        break;
      case ConnectivityStatus.checking:
        dotColor = const Color(0xFFFF9800);
        statusText = 'Checking...';
        break;
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: dotColor,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          '$label: $statusText',
          style: TextStyle(
            fontSize: 12,
            color: dotColor,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

class _PlantCarousel extends StatelessWidget {
  const _PlantCarousel();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();
    final pageController = PageController(viewportFraction: 0.85, keepPage: true);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 16, 20, 12),
          child: Text(
            'Plants',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF2D3748),
            ),
          ),
        ),
        Expanded(
          child: PageView.builder(
            controller: pageController,
            itemCount: vm.plants.length,
            itemBuilder: (context, index) {
              final plant = vm.plants[index];
              return _PlantCard(plant: plant);
            },
          ),
        ),
      ],
    );
  }
}

class _PlantCard extends StatelessWidget {
  final PlantData plant;

  const _PlantCard({required this.plant});

  @override
  Widget build(BuildContext context) {
    final vm = context.read<DashboardViewModel>();

    Color needColor;
    if (plant.probabilityOfNeed >= 0.70) {
      needColor = const Color(0xFFF44336);
    } else if (plant.probabilityOfNeed >= 0.40) {
      needColor = const Color(0xFFFFC107);
    } else {
      needColor = const Color(0xFF4CAF50);
    }

    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ChangeNotifierProvider.value(
              value: context.read<DashboardViewModel>(),
              child: PlantDetailView(plant: plant),
            ),
          ),
        );
      },
      child: Container(
        height: 320,
        margin: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 140,
              child: ClipRRect(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
                child: plant.imageUrl.isNotEmpty
                    ? Image.asset(
                        plant.imageUrl,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          color: const Color(0xFFE8EDF2),
                          child: const Icon(Icons.eco, size: 48, color: Color(0xFFA0AEC0)),
                        ),
                      )
                    : Container(
                        color: const Color(0xFFE8EDF2),
                        child: const Icon(Icons.eco, size: 48, color: Color(0xFFA0AEC0)),
                      ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    plant.displayName,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2D3748),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: needColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '${(plant.probabilityOfNeed * 100).round()}% Need',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: needColor,
                          ),
                        ),
                      ),
                      if (plant.isWatering) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFF2196F3).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.water_drop, size: 12, color: Color(0xFF1565C0)),
                              SizedBox(width: 3),
                              Text(
                                'Watering',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF1565C0),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () => DashboardViewModel.showWaterDialog(context, plant),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4CAF50),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                      ),
                      child: const Text('Water Now', style: TextStyle(fontWeight: FontWeight.w600)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

}

class _WeatherFooter extends StatelessWidget {
  const _WeatherFooter();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();
    final w = vm.weather;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      color: Colors.white,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _WeatherTile(
            icon: Icons.thermostat,
            label: 'Temp',
            value: w != null ? '${w.temperature.toStringAsFixed(1)}°C' : '--',
          ),
          _WeatherTile(
            icon: Icons.water_drop,
            label: 'Humidity',
            value: w != null ? '${w.humidity.toStringAsFixed(0)}%' : '--',
          ),
          _WeatherTile(
            icon: Icons.cloudy_snowing,
            label: 'Rain',
            value: w?.rainForecast ?? '--',
          ),
          _WeatherTile(
            icon: Icons.cloud,
            label: 'Clouds',
            value: w?.cloudCover ?? '--',
          ),
        ],
      ),
    );
  }
}

class _WeatherTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _WeatherTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, size: 18, color: const Color(0xFF718096)),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: Color(0xFF2D3748),
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: Color(0xFF718096),
          ),
        ),
      ],
    );
  }
}