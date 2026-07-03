import 'package:flutter/material.dart';

import '../../data/settings.dart';

class CameraView extends StatefulWidget {
  const CameraView({super.key});

  @override
  State<CameraView> createState() => _CameraViewState();
}

class _CameraViewState extends State<CameraView> {
  bool _enabled = false;
  String _errorMessage = '';

  String get _cameraUrl {
    final espUrl = Settings().apiUrl;
    final uri = Uri.parse(espUrl);
    return 'http://${uri.host}:81/stream';
  }

  String get _captureUrl {
    final espUrl = Settings().apiUrl;
    final uri = Uri.parse(espUrl);
    return 'http://${uri.host}:80/capture';
  }

  void _startCamera() {
    setState(() {
      _enabled = true;
      _errorMessage = '';
    });
  }

  void _stopCamera() {
    setState(() {
      _enabled = false;
      _errorMessage = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: const Text('Camera'),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF2D3748),
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(_enabled ? Icons.videocam_off : Icons.videocam),
            onPressed: _enabled ? _stopCamera : _startCamera,
            tooltip: _enabled ? 'Stop camera' : 'Start camera',
          ),
        ],
      ),
      body: _enabled
          ? _buildCameraFeed()
          : Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.videocam_outlined,
                    size: 64,
                    color: Colors.grey[400],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Camera is off',
                    style: TextStyle(
                      fontSize: 18,
                      color: Colors.grey[600],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tap the camera icon to start',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[400],
                    ),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: _startCamera,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Camera'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF4CAF50),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildCameraFeed() {
    return Column(
      children: [
        Container(
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.1),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          clipBehavior: Clip.antiAlias,
          child: _errorMessage.isNotEmpty
              ? Container(
                  height: 240,
                  color: Colors.grey[200],
                  alignment: Alignment.center,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: Colors.red),
                      const SizedBox(height: 8),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Text(
                          _errorMessage,
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                )
              : Image.network(
                  _cameraUrl,
                  fit: BoxFit.cover,
                  width: double.infinity,
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return Container(
                      height: 240,
                      color: Colors.grey[200],
                      alignment: Alignment.center,
                      child: const CircularProgressIndicator(
                        color: Color(0xFF4CAF50),
                      ),
                    );
                  },
                  errorBuilder: (context, error, stackTrace) {
                    WidgetsBinding.instance.addPostFrameCallback((_) {
                      if (mounted && _errorMessage.isEmpty) {
                        setState(() {
                          _errorMessage = 'Camera stream unreachable — check ESP IP';
                        });
                      }
                    });
                    return Container(
                      height: 240,
                      color: Colors.grey[200],
                      alignment: Alignment.center,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, size: 48, color: Colors.red),
                          const SizedBox(height: 8),
                          const Text(
                            'Failed to load camera stream',
                            style: TextStyle(color: Colors.red),
                          ),
                        ],
                      ),
                    );
                  },
                  headers: const {
                    'Access-Control-Allow-Origin': '*',
                  },
                ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              const Icon(Icons.link, size: 16, color: Colors.grey),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _cameraUrl,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                    fontFamily: 'monospace',
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Live MJPEG stream',
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[400],
          ),
        ),
      ],
    );
  }
}