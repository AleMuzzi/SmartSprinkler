import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/models/weather_data.dart';
import '../../data/settings.dart';
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
            onRefresh: vm.fetchEspStatus,
          ),
          if (vm.espStatus == ConnectivityStatus.connected &&
              vm.espFirmwareVersion != null)
            Padding(
              padding: const EdgeInsets.only(left: 54, top: 8),
              child: Row(
                children: [
                  const Icon(Icons.memory, size: 14, color: Color(0xFF718096)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Firmware version: ${vm.espFirmwareVersion}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF718096),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 14),
          _ConnectionRow(
            label: 'Bayesian Server',
            url: vm.settings.bayesianUrl,
            status: vm.bayesianStatus,
            onRefresh: vm.fetchBayesianStatus,
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

class _UrlsCard extends StatefulWidget {
  final DashboardViewModel vm;

  const _UrlsCard({required this.vm});

  @override
  State<_UrlsCard> createState() => _UrlsCardState();
}

class _UrlsCardState extends State<_UrlsCard> {
  late final TextEditingController _internalEspController;
  late final TextEditingController _internalBayesController;
  late final TextEditingController _externalEspController;
  late final TextEditingController _externalBayesController;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _internalEspController = TextEditingController();
    _internalBayesController = TextEditingController();
    _externalEspController = TextEditingController();
    _externalBayesController = TextEditingController();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      _initialized = true;
      final s = widget.vm.settings;
      _internalEspController.text = s.internalEspUrl;
      _internalBayesController.text = s.internalBayesianUrl;
      _externalEspController.text = s.externalEspUrl;
      _externalBayesController.text = s.externalBayesianUrl;
    }
  }

  @override
  void dispose() {
    _internalEspController.dispose();
    _internalBayesController.dispose();
    _externalEspController.dispose();
    _externalBayesController.dispose();
    super.dispose();
  }

  void _save() {
    final s = widget.vm.settings;
    s.internalEspUrl = _internalEspController.text.trim();
    s.internalBayesianUrl = _internalBayesController.text.trim();
    s.externalEspUrl = _externalEspController.text.trim();
    s.externalBayesianUrl = _externalBayesController.text.trim();
    widget.vm.fetchEspStatus();
    widget.vm.fetchBayesianStatus();
    widget.vm.fetchWeatherStatus();
    widget.vm.fetchCisternStatus();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Settings saved'), duration: Duration(seconds: 2)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.vm.settings;

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
          const SizedBox(height: 12),
          // ── Connection badge ────────────────────────────────────────────
          ListenableBuilder(
            listenable: widget.vm.settings,
            builder: (context, _) {
              final usingInternal = switch (s.urlMode) {
                UrlMode.internal => true,
                UrlMode.external => false,
                UrlMode.auto => s.internalReachable,
              };
              final modeLabel = switch (s.urlMode) {
                UrlMode.auto => 'Auto',
                UrlMode.internal => 'Forced internal',
                UrlMode.external => 'Forced external',
              };
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: usingInternal ? const Color(0xFFE8F5E9) : const Color(0xFFFFF3E0),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: usingInternal ? const Color(0xFF4CAF50) : const Color(0xFFFF9800),
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      usingInternal ? Icons.home : Icons.public,
                      size: 16,
                      color: usingInternal ? const Color(0xFF4CAF50) : const Color(0xFFFF9800),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        usingInternal
                            ? 'Internal — using home LAN URLs'
                            : 'External — using public URLs',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: usingInternal ? const Color(0xFF1B5E20) : const Color(0xFFE65100),
                        ),
                      ),
                    ),
                    Text(
                      modeLabel,
                      style: const TextStyle(fontSize: 11, color: Color(0xFF718096)),
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          // ── Routing selector ────────────────────────────────────────────
          const Text(
            'URL selection',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Color(0xFF2D3748),
            ),
          ),
          const SizedBox(height: 6),
          SegmentedButton<UrlMode>(
            segments: const [
              ButtonSegment(
                value: UrlMode.auto,
                label: Text('Auto'),
                icon: Icon(Icons.autorenew, size: 16),
              ),
              ButtonSegment(
                value: UrlMode.internal,
                label: Text('Internal'),
                icon: Icon(Icons.home, size: 16),
              ),
              ButtonSegment(
                value: UrlMode.external,
                label: Text('External'),
                icon: Icon(Icons.public, size: 16),
              ),
            ],
            selected: {s.urlMode},
            onSelectionChanged: (selection) {
              final mode = selection.first;
              widget.vm.settings.urlMode = mode;
              // Force a refresh so the badge shows the newly selected set.
              widget.vm.fetchEspStatus();
              widget.vm.fetchBayesianStatus();
              setState(() {});
            },
            showSelectedIcon: false,
          ),
          const SizedBox(height: 6),
          Text(
            'Auto tries the internal (LAN) URLs first and falls back to '
            'the external ones when they are unreachable.',
            style: const TextStyle(fontSize: 11, color: Color(0xFF718096)),
          ),
          const SizedBox(height: 16),
          // ── Internal URLs ──────────────────────────────────────────────
          const _SectionHeader(
            icon: Icons.home_outlined,
            label: 'Internal (home LAN)',
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _internalEspController,
            decoration: _urlDecoration(
              label: 'ESP Sprinkler URL',
              hint: 'http://192.168.1.10',
              icon: Icons.router,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _internalBayesController,
            decoration: _urlDecoration(
              label: 'Bayesian Server URL',
              hint: 'http://192.168.1.11:8080',
              icon: Icons.cloud,
            ),
          ),
          const SizedBox(height: 16),
          // ── External URLs ──────────────────────────────────────────────
          const _SectionHeader(
            icon: Icons.public,
            label: 'External (cellular / away)',
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _externalEspController,
            decoration: _urlDecoration(
              label: 'ESP Sprinkler URL',
              hint: 'http://my.home.server',
              icon: Icons.router,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _externalBayesController,
            decoration: _urlDecoration(
              label: 'Bayesian Server URL',
              hint: 'http://my.home.server:8080',
              icon: Icons.cloud,
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _save,
              icon: const Icon(Icons.save),
              label: const Text('Save'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4CAF50),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  InputDecoration _urlDecoration({
    required String label,
    required String hint,
    required IconData icon,
  }) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: Icon(icon, color: const Color(0xFFA0AEC0)),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String label;
  const _SectionHeader({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: const Color(0xFFA0AEC0)),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: Color(0xFF2D3748),
          ),
        ),
      ],
    );
  }
}