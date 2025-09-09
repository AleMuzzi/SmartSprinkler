import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/ui/settings/settings_viewmodel.dart';

import '../page.dart';

class SettingsPage extends PageWidget {
  const SettingsPage({super.key, required this.viewModel}) : super(title: "⚙️ Settings");

  final SettingsPageViewModel viewModel;
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {

  @override
  Widget build(BuildContext context) {
    late final TextEditingController controller = TextEditingController(text: widget.viewModel.settings.apiUrl);

    return Scaffold(
      body: Center(
        // I need to add settings here, such as an edit text for the sprinkler url
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 40.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Container(
                    alignment: AlignmentDirectional.centerStart,
                    child: Text(
                      "Sprinkler settings",
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: controller,
                    decoration: InputDecoration(
                      labelText: "Sprinkler URL",
                      hintText: "http://your-sprinkler.local",
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (value) {
                      widget.viewModel.settings.apiUrl = value;
                    },
                  ),
                  const SizedBox(height: 20),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      ElevatedButton(
                        onPressed: () {
                          setState(() {
                            widget.viewModel.settings.apiUrl = "http://192.168.1.10";
                          });
                        },
                        child: const Text('🏠 Local'),
                      ),
                      const SizedBox(height: 15),
                      ElevatedButton(
                        onPressed: () {
                          setState(() {
                            widget.viewModel.settings.apiUrl = "http://sprinkler.casabrignuzzi.com.es";
                          });
                        },
                        child: const Text('🛰️ Remote'),
                      ),
                    ],
                  )
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
