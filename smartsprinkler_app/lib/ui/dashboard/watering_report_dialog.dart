import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/models/watering_report.dart';
import 'package:smartsprinkler_app/data/watering_report_service.dart';

import '../../main.dart';

/// Shows the read-only report of a watering proposal.
///
/// The dialog is purely informative — same numbers the automatic mode would
/// have dispensed — and marks the report as opened server-side as soon as it
/// is on screen, which clears the unread badge on every client.
Future<void> showWateringReportDialog(WateringReport report) async {
  final context = navigatorKey.currentContext;
  if (context == null) return;

  WateringReportService().markOpened(report.id).catchError((_) {});

  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.water_drop, color: Color(0xFF4CAF50), size: 22),
          const SizedBox(width: 8),
          Expanded(child: Text(report.title)),
        ],
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _formatDate(report.createdAt),
                style: const TextStyle(fontSize: 12, color: Color(0xFF718096)),
              ),
              const SizedBox(height: 12),
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (final dose in report.doses.entries)
                      _DoseRow(
                        label: report.labelFor(dose.key),
                        ml: dose.value,
                      ),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                      decoration: const BoxDecoration(
                        color: Color(0xFFF5F7FA),
                        borderRadius: BorderRadius.only(
                          bottomLeft: Radius.circular(12),
                          bottomRight: Radius.circular(12),
                        ),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Totale',
                            style: TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                          Text(
                            '${report.totalMl.round()} ml',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Nessuna acqua è stata erogata: innaffia quando vuoi dal '
                'pannello di controllo.',
                style: TextStyle(fontSize: 12, color: Color(0xFF718096)),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Chiudi'),
        ),
      ],
    ),
  );
}

class _DoseRow extends StatelessWidget {
  const _DoseRow({required this.label, required this.ml});

  final String label;
  final double ml;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 14)),
          Text(
            '${ml.round()} ml',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Color(0xFF4CAF50),
            ),
          ),
        ],
      ),
    );
  }
}

String _formatDate(DateTime value) {
  final date = '${value.day.toString().padLeft(2, '0')}/'
      '${value.month.toString().padLeft(2, '0')}/${value.year}';
  final time = '${value.hour.toString().padLeft(2, '0')}:'
      '${value.minute.toString().padLeft(2, '0')}';
  return '$date $time';
}
