import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/settings.dart';
import 'package:smartsprinkler_app/ui/home/home.dart';
import 'package:smartsprinkler_app/ui/home/home_viewmodel.dart';
import 'package:smartsprinkler_app/ui/page.dart';
import 'package:smartsprinkler_app/ui/settings/settings.dart';
import 'package:smartsprinkler_app/ui/settings/settings_viewmodel.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartSprinkler',
      theme: ThemeData(
        // This is the theme of your application.
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
      ),
      home: const HomeWidget(title: 'Smart Sprinkler'),
    );
  }
}

class HomeWidget extends StatefulWidget {
  const HomeWidget({super.key, required this.title});

  // This widget is the home page of your application. It is stateful, meaning
  // that it has a State object (defined below) that contains fields that affect
  // how it looks.

  // This class is the configuration for the state. It holds the values (in this
  // case the title) provided by the parent (in this case the App widget) and
  // used by the build method of the State. Fields in a Widget subclass are
  // always marked "final".

  final String title;

  @override
  State<HomeWidget> createState() => _HomeWidgetState();
}

final List<PageWidget> _pages = [
  HomePage(viewModel: HomePageViewModel()),
  SettingsPage(viewModel: SettingsPageViewModel()),
];

int _selectedPageIndex = 0;
class _HomeWidgetState extends State<HomeWidget> {

  @override
  Widget build(BuildContext context) {
    // This method is rerun every time setState is called, for instance as done
    // by the _incrementCounter method above.
    //
    // The Flutter framework has been optimized to make rerunning build methods
    // fast, so that you can just rebuild anything that needs updating rather
    // than having to individually change instances of widgets.
    return Scaffold(
      appBar: AppBar(
        // TRY THIS: Try changing the color here to a specific color (to
        // Colors.amber, perhaps?) and trigger a hot reload to see the AppBar
        // change color while the other colors stay the same.
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        // Here we take the value from the MyHomePage object that was created by
        // the App.build method, and use it to set our appbar title.
        title: Text(_pages[_selectedPageIndex].title),
        centerTitle: true,
      ),
      body: _pages[_selectedPageIndex],
      // I want to crete a navigation menu
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: <Widget>[
            DrawerHeader(
              decoration: BoxDecoration(
                color: Colors.green,
              ),
              child: Text(
                  widget.title,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 30,
                  )
              ),
            ),
            ListTile(
              title: Text('🏠 Home', style: TextStyle(fontSize: 24)),
              onTap: () {
                setState(() {
                  _selectedPageIndex = 0;
                });
                Navigator.pop(context);
              },

            ),
            ListTile(
              title: Text('⚙️ Settings', style: TextStyle(fontSize: 24)),
              onTap: () {
                setState(() {
                  _selectedPageIndex = 1;
                });
                Navigator.pop(context);
              },
            ),
          ]),
      )
    );
  }
}
