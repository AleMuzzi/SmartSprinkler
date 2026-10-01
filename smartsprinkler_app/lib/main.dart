import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'ui/dashboard/audit_log_view.dart';
import 'ui/dashboard/dashboard_viewmodel.dart';
import 'ui/dashboard/dashboard_view.dart';
import 'ui/dashboard/system_control_view.dart';
import 'ui/camera/camera_view.dart';
import 'ui/splash_screen.dart';
import 'data/water_alert_service.dart';
import 'data/network_monitor.dart';
import 'data/settings.dart';
import 'data/sprinkler.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SmartSprinklerApp());
}

class SmartSprinklerApp extends StatelessWidget {
  const SmartSprinklerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartSprinkler',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4CAF50)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F7FA),
      ),
      home: const _AppLoader(),
    );
  }
}

class _AppLoader extends StatefulWidget {
  const _AppLoader();

  @override
  State<_AppLoader> createState() => _AppLoaderState();
}

class _AppLoaderState extends State<_AppLoader> {
  bool _ready = false;
  bool _hasNotificationPermission = true;
  NetworkMonitor? _monitor;

  @override
  void initState() {
    super.initState();
    // Defer init until AFTER the first frame renders.
    WidgetsBinding.instance.addPostFrameCallback((_) => _init());
  }

  @override
  void dispose() {
    _monitor?.stop();
    super.dispose();
  }

  Future<void> _init() async {
    final settings = Settings();
    final monitor = _monitor = NetworkMonitor();

    await _guard('settings.load', () => settings.load());
    await _guard('restoreWaterAlertState', () => Sprinkler().restoreWaterAlertState());
    await _guard('setAppForeground', () => WaterAlertService.setAppForeground(true));
    await _guard('networkMonitor.start', () => monitor.start());

    final alertService = WaterAlertService();
    await _guard('alertService.init', () => alertService.init(settings.apiUrl));
    try {
      final granted = await alertService.ensureNotificationPermission();
      _hasNotificationPermission = granted;
    } catch (e) {
      debugPrint('App init: ensureNotificationPermission failed: $e');
    }
    await _guard('alertService.start', () => alertService.start());

    if (!mounted) return;
    setState(() => _ready = true);
  }

  /// Runs [action], swallowing any platform/plugin failure so that a broken
  /// dependency can never leave the app stuck on the splash screen.
  Future<void> _guard(String step, Future<void> Function() action) async {
    try {
      await action();
    } catch (e) {
      debugPrint('App init: $step failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) return const SplashScreen();
    return MainNavigationPage(
      hasNotificationPermission: _hasNotificationPermission,
      networkMonitor: _monitor,
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
