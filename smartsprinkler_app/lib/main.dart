import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'ui/dashboard/audit_log_view.dart';
import 'ui/dashboard/dashboard_viewmodel.dart';
import 'ui/dashboard/dashboard_view.dart';
import 'ui/dashboard/system_control_view.dart';
import 'ui/camera/camera_view.dart';
import 'data/water_alert_service.dart';
import 'data/network_monitor.dart';
import 'data/settings.dart';
import 'data/sprinkler.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await WaterAlertService.setAppForeground(true);

  final settings = Settings();
  await settings.load();

  final sprinkler = Sprinkler();
  await sprinkler.restoreWaterAlertState();

  // Start probing the LAN so apiUrl/bayesianUrl automatically use the
  // internal URLs when reachable and fall back to the external ones.
  final networkMonitor = NetworkMonitor();
  await networkMonitor.start();

  final alertService = WaterAlertService();
  await alertService.init(settings.apiUrl);
  final hasPermission = await alertService.ensureNotificationPermission();
  await alertService.start();

  runApp(SmartSprinklerApp(
    hasNotificationPermission: hasPermission,
    networkMonitor: networkMonitor,
  ));
}

class SmartSprinklerApp extends StatelessWidget {
  const SmartSprinklerApp({
    super.key,
    this.hasNotificationPermission = true,
    this.networkMonitor,
  });

  final bool hasNotificationPermission;
  final NetworkMonitor? networkMonitor;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartSprinkler',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4CAF50)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F7FA),
      ),
      home: MainNavigationPage(
        hasNotificationPermission: hasNotificationPermission,
        networkMonitor: networkMonitor,
      ),
    );
  }
}

class MainNavigationPage extends StatefulWidget {
  const MainNavigationPage({
    super.key,
    this.hasNotificationPermission = true,
    this.networkMonitor,
  });

  final bool hasNotificationPermission;
  final NetworkMonitor? networkMonitor;

  @override
  State<MainNavigationPage> createState() => _MainNavigationPageState();
}

class _MainNavigationPageState extends State<MainNavigationPage> with WidgetsBindingObserver {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!widget.hasNotificationPermission) {
        _showNotificationPermissionDialog();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    WaterAlertService.setAppForeground(state == AppLifecycleState.resumed);
  }

  void _showNotificationPermissionDialog() {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Notifications disabled'),
        content: const Text(
          'SmartSprinkler needs notification permission to alert you when the water tank is low.\n\n'
          'Enable notifications in: Settings → Apps → SmartSprinkler → Notifications',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final nm = widget.networkMonitor;
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => DashboardViewModel()),
        if (nm != null)
          ChangeNotifierProvider<NetworkMonitor>.value(value: nm),
      ],
      child: Scaffold(
        body: IndexedStack(
          index: _currentIndex,
          children: const [
            DashboardView(),
            CameraView(),
            AuditLogView(),
            SystemControlView(),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          backgroundColor: Colors.white,
          indicatorColor: const Color(0xFF4CAF50).withValues(alpha: 0.2),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard, color: Color(0xFF4CAF50)),
              label: 'Dashboard',
            ),
            NavigationDestination(
              icon: Icon(Icons.videocam_outlined),
              selectedIcon: Icon(Icons.videocam, color: Color(0xFF4CAF50)),
              label: 'Camera',
            ),
            NavigationDestination(
              icon: Icon(Icons.list_alt_outlined),
              selectedIcon: Icon(Icons.list_alt, color: Color(0xFF4CAF50)),
              label: 'Logs',
            ),
            NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon: Icon(Icons.settings, color: Color(0xFF4CAF50)),
              label: 'System',
            ),
          ],
        ),
      ),
    );
  }
}