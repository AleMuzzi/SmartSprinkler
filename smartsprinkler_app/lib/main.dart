import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'ui/dashboard/dashboard_viewmodel.dart';
import 'ui/dashboard/dashboard_view.dart';
import 'ui/dashboard/system_control_view.dart';

void main() {
  runApp(const SmartSprinklerApp());
}

class SmartSprinklerApp extends StatelessWidget {
  const SmartSprinklerApp({super.key});

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
      home: const MainNavigationPage(),
    );
  }
}

class MainNavigationPage extends StatefulWidget {
  const MainNavigationPage({super.key});

  @override
  State<MainNavigationPage> createState() => _MainNavigationPageState();
}

class _MainNavigationPageState extends State<MainNavigationPage> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => DashboardViewModel(),
      child: Scaffold(
        body: IndexedStack(
          index: _currentIndex,
          children: const [
            DashboardView(),
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