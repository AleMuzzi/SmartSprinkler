import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/models/weather_data.dart';
import 'dashboard_viewmodel.dart';

class SystemControlView extends StatelessWidget {
  const SystemControlView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: const Text('System Control'),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF2D3748),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _ConnectivityCard(vm: vm),
            const SizedBox(height: 16),
            _UrlsCard(vm: vm),
          ],
        ),
      ),
    );
  }
}

class _ConnectivityCard extends StatelessWidget {
  final DashboardViewModel vm;

  const _ConnectivityCard({required this.vm});

  @override
  Widget build(BuildContext context) {
    return Container(
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
          const Row(
            children: [
              Icon(Icons.wifi, color: Color(0xFF4CAF50), size: 22),
              SizedBox(width: 8),
              Text(
                'System Connectivity',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2D3748),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          _ConnectionRow(
            label: 'ESP32 Controller',
            url: vm.settings.apiUrl,
            status: vm.espStatus,
            onRefresh: vm.checkEspConnectivity,
          ),
          const SizedBox(height: 14),
          _ConnectionRow(
            label: 'Bayesian Server',
            url: vm.settings.bayesianUrl,
            status: vm.bayesianStatus,
            onRefresh: vm.checkBayesianConnectivity,
          ),
        ],
      ),
    );
  }
}

class _ConnectionRow extends StatelessWidget {
  final String label;
  final String url;
  final ConnectivityStatus status;
  final Future<void> Function() onRefresh;

  const _ConnectionRow({
    required this.label,
    required this.url,
    required this.status,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    IconData statusIcon;
    String statusText;

    switch (status) {
      case ConnectivityStatus.connected:
        statusColor = const Color(0xFF4CAF50);
        statusIcon = Icons.check_circle;
        statusText = 'Connected';
        break;
      case ConnectivityStatus.disconnected:
        statusColor = const Color(0xFFF44336);
        statusIcon = Icons.error;
        statusText = 'Disconnected';
        break;
      case ConnectivityStatus.checking:
        statusColor = const Color(0xFFFF9800);
        statusIcon = Icons.sync;
        statusText = 'Checking...';
        break;
    }

    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(statusIcon, color: statusColor, size: 22),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D3748),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                url,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF718096),
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                statusText,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: statusColor,
                ),
              ),
            ),
            const SizedBox(height: 4),
            GestureDetector(
              onTap: onRefresh,
              child: Text(
                'Refresh',
                style: TextStyle(
                  fontSize: 11,
                  color: statusColor,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _UrlsCard extends StatelessWidget {
  final DashboardViewModel vm;

  const _UrlsCard({required this.vm});

  @override
  Widget build(BuildContext context) {
    late final TextEditingController espController = TextEditingController(text: vm.settings.apiUrl);
    late final TextEditingController bayesController = TextEditingController(text: vm.settings.bayesianUrl);

    return Container(
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
          const Row(
            children: [
              Icon(Icons.link, color: Color(0xFF4CAF50), size: 22),
              SizedBox(width: 8),
              Text(
                'Server URLs',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2D3748),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          TextField(
            controller: espController,
            decoration: InputDecoration(
              labelText: 'ESP Sprinkler URL',
              hintText: 'http://192.168.1.10',
              prefixIcon: const Icon(Icons.router, color: Color(0xFFA0AEC0)),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
            onChanged: (value) => vm.settings.apiUrl = value,
          ),
          const SizedBox(height: 14),
          TextField(
            controller: bayesController,
            decoration: InputDecoration(
              labelText: 'Bayesian Server URL',
              hintText: 'http://192.168.1.11:8080',
              prefixIcon: const Icon(Icons.cloud, color: Color(0xFFA0AEC0)),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
            onChanged: (value) => vm.settings.bayesianUrl = value,
          ),
        ],
      ),
    );
  }
}