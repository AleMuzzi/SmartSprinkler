import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/sprinkler.dart';
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';
import 'package:smartsprinkler_app/ui/home/low_water_alert_page.dart';
import 'package:smartsprinkler_app/ui/home/sprinkler_data_component.dart';
import 'package:smartsprinkler_app/ui/home/sprinkler_data_component_viewmodel.dart';

import '../page.dart';

class HomePage extends PageWidget {
  const HomePage({super.key, required this.viewModel}) : super(title: "🌧️  Irrigation Control");

  final HomePageViewModel viewModel;

  @override
  State<HomePage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<HomePage> {
  Target? selectedPlant = Target.NAGA_MORICH;
  Sprinkler sprinkler = Sprinkler();
  SprinklerDataComponentViewModel sprinklerDataComponentViewModel = SprinklerDataComponentViewModel();

  @override
  void dispose() {
    sprinklerDataComponentViewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40.0, vertical: 20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              const SizedBox(height: 20),
              ListenableBuilder(
                listenable: sprinkler,
                builder: (context, _) {
                  if (!sprinkler.waterLowAlert) return const SizedBox.shrink();
                  return Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade100,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.orange.shade700),
                    ),
                    child: InkWell(
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const LowWaterAlertPage()),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                          const SizedBox(width: 8),
                          Expanded(child: Text("⚠️ Water tank low — irrigation disabled", style: TextStyle(color: Colors.orange.shade900))),
                          const Icon(Icons.chevron_right, color: Colors.orange),
                        ],
                      ),
                    ),
                  );
                },
              ),
              Container(
                alignment: Alignment.center,
                child: ListenableBuilder(
                  listenable: sprinkler,
                  builder: (BuildContext context, Widget? child) {
                    return Column(
                      children: [
                        _RotarySelectorStatus(
                          position: sprinkler.rotaryPosition,
                          activePlant: sprinkler.waterPump == 'on' ? sprinkler.activePlant : null,
                        ),
                        const SizedBox(height: 16),
                        SprinklerDataComponent(viewModel: sprinklerDataComponentViewModel),
                      ],
                    );
                  },
                ),
              ),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.only(bottom: 50.0),
                  color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.5),
                  alignment: Alignment.bottomCenter,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      DropdownButton<Target>(
                        value: selectedPlant,
                        hint: const Text('Scegli una pianta'),
                        isExpanded: true,
                      items: Target.values.map((Target target) {
                        return DropdownMenuItem<Target>(
                          value: target,
                          child: Text(target.name),
                        );
                      }).toList(),
                      onChanged: (newValue) {
                        setState(() {
                          selectedPlant = newValue!;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text("Log to Bayesian server"),
                        const SizedBox(width: 8),
                        Switch(
                          value: widget.viewModel.notifyBayesian,
                          onChanged: (value) {
                            setState(() {
                              widget.viewModel.notifyBayesian = value;
                            });
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: selectedPlant != null
                          ? () { widget.viewModel.startIrrigation(selectedPlant!); }
                          : null,
                      child: const Text('Start Irrigation'),
                    ),
                    const SizedBox(height: 15),
                    ElevatedButton(
                      onPressed: selectedPlant != null
                          ? () { widget.viewModel.stopIrrigation(selectedPlant!); }
                          : null,
                      child: const Text('Stop Irrigation'),
                    ),
                    const SizedBox(height: 60),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RotarySelectorStatus extends StatelessWidget {
  final int? position;
  final String? activePlant;

  const _RotarySelectorStatus({this.position, this.activePlant});

  @override
  Widget build(BuildContext context) {
    if (position == null) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.warning_amber, color: Colors.grey, size: 20),
            SizedBox(width: 8),
            Text("Rotary selector: uncalibrated", style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    final labels = ['Habanero', 'Naga Morich', 'Carolina Reaper', 'Rosmarino'];
    final currentLabel = activePlant != null ? _plantFromTarget(activePlant!) : 'Idle';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.rotate_right, color: Colors.blue.shade700, size: 20),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Rotary Selector", style: TextStyle(color: Colors.blue.shade900, fontSize: 12, fontWeight: FontWeight.w600)),
              Text("Pos $position · ${labels[position!.clamp(0, 3)]}", style: TextStyle(color: Colors.blue.shade700, fontSize: 14)),
            ],
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: activePlant != null ? Colors.green.shade100 : Colors.grey.shade200,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              activePlant != null ? currentLabel : 'Idle',
              style: TextStyle(
                color: activePlant != null ? Colors.green.shade800 : Colors.grey.shade600,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _plantFromTarget(String target) {
    switch (target) {
      case 'HABANERO': return 'Habanero';
      case 'NAGA_MORICH': return 'Naga Morich';
      case 'CAROLINA_REAPER': return 'Carolina Reaper';
      case 'ROSMARINO': return 'Rosmarino';
      default: return target;
    }
  }
}
