import 'package:flutter/material.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:provider/provider.dart';

import '../../data/models/weather_data.dart';
import '../../data/network_monitor.dart';
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

  Future<void> _pickHomeWifi() async {
    // Try to fetch a snapshot of nearby Wi-Fi networks. The user picks
    // the one labelled "home" — that's what the NetworkMonitor will then
    // match against the current connection.
    final monitor = context.read<NetworkMonitor>();
    final picked = await showDialog<String?>(
      context: context,
      builder: (_) => _WifiPickerDialog(monitor: monitor),
    );
    if (picked != null && mounted) {
      setState(() {
        widget.vm.settings.homeWifiSsid = picked;
      });
      // Re-evaluate the connection right away so the badge updates.
      await monitor.start();
      if (mounted) setState(() {});
    }
  }

  void _clearHomeWifi() {
    setState(() {
      widget.vm.settings.homeWifiSsid = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.vm.settings;
    final monitor = context.watch<NetworkMonitor>();
    final onHome = monitor.isHomeWifi;
    final ssid = monitor.currentSsid ?? s.homeWifiSsid ?? '—';

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
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: onHome ? const Color(0xFFE8F5E9) : const Color(0xFFFFF3E0),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: onHome ? const Color(0xFF4CAF50) : const Color(0xFFFF9800),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  onHome ? Icons.home : Icons.public,
                  size: 16,
                  color: onHome ? const Color(0xFF4CAF50) : const Color(0xFFFF9800),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    onHome
                        ? 'Internal — using home LAN URLs'
                        : 'External — using public URLs',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: onHome ? const Color(0xFF1B5E20) : const Color(0xFFE65100),
                    ),
                  ),
                ),
                Text(
                  monitor.currentSsid == null ? '' : 'Wi-Fi: $ssid',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF718096)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          // ── Home Wi-Fi selector ────────────────────────────────────────
          const Text(
            'Home Wi-Fi',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Color(0xFF2D3748),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  s.homeWifiSsid ?? 'Not set — app is always on external URLs',
                  style: TextStyle(
                    fontSize: 12,
                    color: s.homeWifiSsid == null
                        ? const Color(0xFFA0AEC0)
                        : const Color(0xFF2D3748),
                  ),
                ),
              ),
              if (s.homeWifiSsid != null)
                IconButton(
                  icon: const Icon(Icons.clear, size: 18),
                  tooltip: 'Clear',
                  onPressed: _clearHomeWifi,
                ),
              ElevatedButton.icon(
                onPressed: _pickHomeWifi,
                icon: const Icon(Icons.wifi_find, size: 16),
                label: const Text('Pick'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  textStyle: const TextStyle(fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // ── Internal URLs ──────────────────────────────────────────────
          const _SectionHeader(
            icon: Icons.home_outlined,
            label: 'Internal (home LAN)',
            active: true,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _internalEspController,
            decoration: _urlDecoration(
              label: 'ESP Sprinkler URL',
              hint: 'http://192.168.1.10',
              icon: Icons.router,
              active: onHome,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _internalBayesController,
            decoration: _urlDecoration(
              label: 'Bayesian Server URL',
              hint: 'http://192.168.1.11:8080',
              icon: Icons.cloud,
              active: onHome,
            ),
          ),
          const SizedBox(height: 16),
          // ── External URLs ──────────────────────────────────────────────
          _SectionHeader(
            icon: Icons.public,
            label: 'External (cellular / away)',
            active: !onHome,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _externalEspController,
            decoration: _urlDecoration(
              label: 'ESP Sprinkler URL',
              hint: 'http://my.home.server',
              icon: Icons.router,
              active: !onHome,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _externalBayesController,
            decoration: _urlDecoration(
              label: 'Bayesian Server URL',
              hint: 'http://my.home.server:8080',
              icon: Icons.cloud,
              active: !onHome,
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
    required bool active,
  }) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: Icon(icon, color: active ? const Color(0xFF4CAF50) : const Color(0xFFA0AEC0)),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(
          color: active ? const Color(0xFF4CAF50) : const Color(0xFFE2E8F0),
          width: active ? 1.5 : 1,
        ),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  const _SectionHeader({
    required this.icon,
    required this.label,
    required this.active,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: active ? const Color(0xFF4CAF50) : const Color(0xFFA0AEC0)),
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: active ? const Color(0xFF2D3748) : const Color(0xFF718096),
          ),
        ),
      ],
    );
  }
}

class _WifiPickerDialog extends StatefulWidget {
  final NetworkMonitor monitor;
  const _WifiPickerDialog({required this.monitor});

  @override
  State<_WifiPickerDialog> createState() => _WifiPickerDialogState();
}

class _WifiPickerDialogState extends State<_WifiPickerDialog> {
  bool _loading = true;
  List<_WifiEntry> _networks = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final info = NetworkInfo();
      final results = await info.getWifiBSSID();
      // getWifiBSSID only returns the currently connected one; for a
      // broader scan we need the list of saved networks which is
      // platform-specific. Try getWifiName as a fallback to confirm at
      // least the current network.
      final current = await info.getWifiName();
      final list = <_WifiEntry>[];
      if (current != null && current.isNotEmpty) {
        final cleaned = current.replaceAll('"', '').trim();
        list.add(_WifiEntry(cleaned, currentlyConnected: true));
      }
      // Android-only: query saved networks.
      try {
        // ignore: deprecated_member_use
        // We intentionally use the basic API — saved networks list needs
        // extra permission on modern Android. As a pragmatic fallback
        // we expose the current SSID as the default pick.
        if (results != null && results.isNotEmpty) {
          // No per-BSSID SSID, BSSID alone is opaque to the user.
        }
      } catch (_) {}
      setState(() {
        _networks = list;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Pick home Wi-Fi'),
      content: SizedBox(
        width: double.maxFinite,
        child: _loading
            ? const SizedBox(
                height: 120,
                child: Center(child: CircularProgressIndicator()),
              )
            : _error != null
                ? Text('Error scanning Wi-Fi:\n$_error')
                : _networks.isEmpty
                    ? const Text(
                        'No Wi-Fi detected. Make sure Wi-Fi is on and the app has location permission.')
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: _networks
                            .map((n) => ListTile(
                                  leading: Icon(
                                    n.currentlyConnected ? Icons.wifi : Icons.wifi_off,
                                    color: n.currentlyConnected
                                        ? const Color(0xFF4CAF50)
                                        : const Color(0xFFA0AEC0),
                                  ),
                                  title: Text(n.ssid),
                                  subtitle: n.currentlyConnected
                                      ? const Text('Currently connected')
                                      : null,
                                  onTap: () => Navigator.pop(context, n.ssid),
                                ))
                            .toList(),
                      ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, ''),
          child: const Text('Use current'),
        ),
      ],
    );
  }
}

class _WifiEntry {
  final String ssid;
  final bool currentlyConnected;
  _WifiEntry(this.ssid, {this.currentlyConnected = false});
}