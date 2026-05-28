import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/settings.dart';
import 'package:smartsprinkler_app/ui/settings/settings_viewmodel.dart';

import '../page.dart';

class SettingsPage extends PageWidget {
  const SettingsPage({super.key, required this.viewModel}) : super(title: "⚙️ Settings");

  final SettingsPageViewModel viewModel;
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late final TextEditingController _espController;
  late final TextEditingController _bayesController;
  bool _espChanged = false;
  bool _bayesChanged = false;

  @override
  void initState() {
    super.initState();
    _espController = TextEditingController(text: widget.viewModel.settings.apiUrl);
    _bayesController = TextEditingController(text: widget.viewModel.settings.bayesianUrl);
  }

  @override
  void dispose() {
    _espController.dispose();
    _bayesController.dispose();
    super.dispose();
  }

  void _save() {
    widget.viewModel.settings.apiUrl = _espController.text;
    widget.viewModel.settings.bayesianUrl = _bayesController.text;
    setState(() {
      _espChanged = false;
      _bayesChanged = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 40.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(
                  "Sprinkler settings",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _espController,
                  decoration: InputDecoration(
                    labelText: "ESP Sprinkler URL",
                    hintText: "http://your-sprinkler.local",
                    border: const OutlineInputBorder(),
                    suffixIcon: _espChanged
                        ? const Icon(Icons.edit, color: Colors.orange, size: 16)
                        : null,
                  ),
                  onChanged: (_) {
                    setState(() {
                      _espChanged = _espController.text != widget.viewModel.settings.apiUrl;
                    });
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _bayesController,
                  decoration: InputDecoration(
                    labelText: "Bayesian Server URL",
                    hintText: "http://your-server.local:8080",
                    border: const OutlineInputBorder(),
                    suffixIcon: _bayesChanged
                        ? const Icon(Icons.edit, color: Colors.orange, size: 16)
                        : null,
                  ),
                  onChanged: (_) {
                    setState(() {
                      _bayesChanged = _bayesController.text != widget.viewModel.settings.bayesianUrl;
                    });
                  },
                ),
                if (_espChanged || _bayesChanged) ...[
                  const SizedBox(height: 12),
                  ElevatedButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text('Save'),
                  ),
                ],
                const SizedBox(height: 20),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        setState(() {
                          _espController.text = "http://192.168.1.10";
                          _espChanged = _espController.text != Settings().apiUrl;
                        });
                      },
                      child: const Text('🏠 Local ESP'),
                    ),
                    const SizedBox(height: 15),
                    ElevatedButton(
                      onPressed: () {
                        setState(() {
                          _espController.text = "http://sprinkler.casabrignuzzi.com.es";
                          _espChanged = _espController.text != Settings().apiUrl;
                        });
                      },
                      child: const Text('🛰️ Remote ESP'),
                    ),
                  ],
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}
