import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../data/models/plant_data.dart';
import '../../../data/models/weather_data.dart';
import '../../../data/sprinkler.dart';
import '../home/low_water_alert_page.dart';
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
            _WaterAlertBanner(),
            _StatusHeader(),
            Divider(height: 1, color: Color(0xFFE0E4E8)),
            Expanded(child: _PlantGrid()),
            Divider(height: 1, color: Color(0xFFE0E4E8)),
            _WeatherFooter(),
          ],
        ),
      ),
    );
  }
}

class _WaterAlertBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Sprinkler(),
      builder: (context, _) {
        final alert = Sprinkler().waterLowAlert;
        if (!alert) return const SizedBox.shrink();
        return Material(
          color: Colors.orange.shade100,
          child: InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const LowWaterAlertPage()),
            ),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: Colors.orange.shade700, width: 1)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "⚠️ Water tank low — irrigation disabled",
                      style: TextStyle(color: Colors.orange.shade900, fontWeight: FontWeight.w600),
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.orange),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _StatusHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _ConnectivityIndicators(esp: vm.espStatus, bayesian: vm.bayesianStatus),
            ],
          ),
          const SizedBox(height: 10),
          _CisternCompact(),
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
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _ConnectionDot(label: 'ESP', status: esp),
        const SizedBox(width: 24),
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


class _CisternCompact extends StatelessWidget {
  const _CisternCompact();

  @override
  Widget build(BuildContext context) {
    final dataReceived = Sprinkler().cisternDataReceived;
    final level = Sprinkler().cisternLevelMl;
    final capacity = Sprinkler().cisternCapacityMl;
    final pct = Sprinkler().cisternLevelPct;
    final lowAlert = Sprinkler().waterLowAlert;

    final litres = (capacity > 0) ? (level / 1000).toStringAsFixed(1) : '–';
    final pctClamped = pct.clamp(0.0, 100.0);

    Color barColor;
    if (pctClamped < 15.0) {
      barColor = const Color(0xFFF44336);
    } else if (pctClamped < 35.0) {
      barColor = const Color(0xFFFF9800);
    } else {
      barColor = const Color(0xFF4CAF50);
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: lowAlert ? const Color(0xFFF44336) : const Color(0xFFE8EDF2),
          width: lowAlert ? 1.5 : 1,
        ),
      ),
        child: Row(
          children: [
            const Text('💧', style: TextStyle(fontSize: 16)),
            const SizedBox(width: 8),
            const Text(
              'Cisterna',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Color(0xFF2D3748),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: dataReceived ? pctClamped / 100.0 : 0,
                  minHeight: 6,
                  backgroundColor: const Color(0xFFE8EDF2),
                  valueColor: AlwaysStoppedAnimation<Color>(barColor),
                ),
              ),
            ),
            const SizedBox(width: 10),
            if (!dataReceived)
              const Text(
                '—',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFFA0AEC0),
                ),
              )
            else ...[
              Text(
                '$litres L',
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D3748),
                ),
              ),
              const SizedBox(width: 6),
              Text(
                '${pctClamped.toStringAsFixed(0)}%',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: barColor,
                ),
              ),
            ],
            if (lowAlert) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFF44336),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'LOW',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ],
        ),
      );
  }
}


class _PlantGrid extends StatelessWidget {
  const _PlantGrid();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();

    return LayoutBuilder(
      builder: (context, constraints) {
        const gridPadding = 12.0;
        const spacing = 12.0;
        const crossAxisCount = 2;
        final childAspectRatio = _gridChildAspectRatio(constraints.maxHeight);
        final cellWidth =
            (constraints.maxWidth - gridPadding * 2 - spacing) / crossAxisCount;
        final cellHeight = cellWidth / childAspectRatio;
        final contentHeight =
            cellHeight * crossAxisCount + spacing * (crossAxisCount - 1) + gridPadding * 2;
        final verticalPadding = contentHeight < constraints.maxHeight
            ? (constraints.maxHeight - contentHeight) / 2
            : gridPadding;

        return GridView.builder(
          padding: EdgeInsets.symmetric(
            horizontal: gridPadding,
            vertical: verticalPadding,
          ),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: spacing,
            crossAxisSpacing: spacing,
            childAspectRatio: childAspectRatio,
          ),
          itemCount: vm.plants.length,
          itemBuilder: (context, index) {
            final plant = vm.plants[index];
            return _PlantCard(plant: plant);
          },
        );
      },
    );
  }

  double _gridChildAspectRatio(double height) {
    if (height <= 380) return 0.72;
    if (height <= 480) return 0.78;
    return 0.85;
  }
}

class _PlantCard extends StatelessWidget {
  final PlantData plant;

  const _PlantCard({required this.plant});

  @override
  Widget build(BuildContext context) {
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
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              height: 92,
              child: ClipRRect(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                child: plant.imageUrl.isNotEmpty
                    ? Image.asset(
                        plant.imageUrl,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => Container(
                          color: const Color(0xFFE8EDF2),
                          child: const Icon(Icons.eco, size: 28, color: Color(0xFFA0AEC0)),
                        ),
                      )
                    : Container(
                        color: const Color(0xFFE8EDF2),
                        child: const Icon(Icons.eco, size: 32, color: Color(0xFFA0AEC0)),
                      ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          plant.displayName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF2D3748),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: needColor.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                '${(plant.probabilityOfNeed * 100).round()}% Need',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: needColor,
                                ),
                              ),
                            ),
                            if (plant.isWatering) ...[
                              const SizedBox(width: 5),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF2196F3).withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.water_drop, size: 10, color: Color(0xFF1565C0)),
                                    SizedBox(width: 3),
                                    Text(
                                      'Watering',
                                      style: TextStyle(
                                        fontSize: 11,
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
                      ],
                    ),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () => DashboardViewModel.showWaterDialog(context, plant),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF4CAF50),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 4),
                        ),
                        child: const Text('Water Now', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                      ),
                    ),
                  ],
                ),
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
            value: (w?.temperature != null)
                ? '${w!.temperature!.toStringAsFixed(1)}°C'
                : '--',
          ),
          _WeatherTile(
            icon: Icons.water_drop,
            label: 'Humidity',
            value: (w?.humidity != null)
                ? '${w!.humidity!.toStringAsFixed(0)}%'
                : '--',
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