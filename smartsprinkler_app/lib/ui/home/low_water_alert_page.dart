import 'package:flutter/material.dart' hide Action;
import 'package:smartsprinkler_app/data/sprinkler.dart';
import 'package:smartsprinkler_app/model/command.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';

class LowWaterAlertPage extends StatelessWidget {
  const LowWaterAlertPage({super.key});

  @override
  Widget build(BuildContext context) {
    final sprinkler = Sprinkler();
    final viewModel = HomePageViewModel();

    return Scaffold(
      appBar: AppBar(title: const Text("Low Water Alert")),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    "Water tank level is low.\nIrrigation is blocked to protect the pump.",
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            if (sprinkler.blockedAmountMl > 0) ...[
              Text(
                "Blocked amount: ${sprinkler.blockedAmountMl} ml",
                style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.red.shade700),
              ),
              const SizedBox(height: 8),
              Text(
                "This water was requested but not supplied due to low level.",
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
            ],
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  viewModel.forceIrrigation(Target.NAGA_MORICH, Action.START);
                  Navigator.pop(context);
                },
                icon: const Icon(Icons.water_drop),
                label: const Text("Force Water Anyway"),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              "The alert will remain active on the ESP even if you force water.",
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}
