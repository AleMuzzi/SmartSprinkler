import 'package:flutter/material.dart';
import 'package:smartsprinkler_app/data/audit_log_service.dart';

const _categoryColors = {
  'inference': Color(0xFF1976D2),
  'command': Color(0xFF388E3C),
  'alert': Color(0xFFD32F2F),
  'error': Color(0xFFB71C1C),
  'config': Color(0xFF7B1FA2),
};

class AuditLogView extends StatefulWidget {
  const AuditLogView({super.key});

  @override
  State<AuditLogView> createState() => _AuditLogViewState();
}

class _AuditLogViewState extends State<AuditLogView> {
  final AuditLogService _service = AuditLogService();
  final TextEditingController _filterController = TextEditingController();

  List<AuditLogEntry> _entries = [];
  String _category = '';
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _filterController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final entries = await _service.fetchLogEntries(
        filter: _filterController.text,
        category: _category.isEmpty ? null : _category,
      );
      if (mounted) {
        setState(() {
          _entries = entries;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Color _colorForCategory(String category) =>
      _categoryColors[category] ?? Colors.grey.shade700;

  String _formatTimestamp(String ts) {
    try {
      return DateTime.parse(ts).toLocal().toString();
    } catch (_) {
      return ts;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Text(
                '📋 Audit Log',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 8),
              Text(
                '(${_entries.length} entries)',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
              const Spacer(),
              IconButton(
                onPressed: _loading ? null : _load,
                icon: const Icon(Icons.refresh),
                tooltip: 'Refresh',
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _filterController,
                  decoration: InputDecoration(
                    hintText: 'Filter by text…',
                    isDense: true,
                    border: const OutlineInputBorder(),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.search),
                      onPressed: _load,
                    ),
                  ),
                  onSubmitted: (_) => _load(),
                ),
              ),
              const SizedBox(width: 8),
              DropdownButton<String>(
                value: _category,
                items: const [
                  DropdownMenuItem(value: '', child: Text('All')),
                  DropdownMenuItem(value: 'inference', child: Text('Inference')),
                  DropdownMenuItem(value: 'command', child: Text('Command')),
                  DropdownMenuItem(value: 'alert', child: Text('Alert')),
                  DropdownMenuItem(value: 'error', child: Text('Error')),
                  DropdownMenuItem(value: 'config', child: Text('Config')),
                ],
                onChanged: (v) {
                  setState(() => _category = v ?? '');
                  _load();
                },
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Text('⚠️ $_error', style: const TextStyle(color: Colors.red)),
            ),
          Expanded(
            child: _loading && _entries.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : _entries.isEmpty
                    ? const Center(child: Text('No log entries', style: TextStyle(color: Colors.grey)))
                    : ListView.separated(
                        itemCount: _entries.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (ctx, i) {
                          final e = _entries[i];
                          final color = _colorForCategory(e.category);
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: color.withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: Text(
                                        e.category,
                                        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        _formatTimestamp(e.timestamp),
                                        style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(e.message, style: const TextStyle(fontSize: 14)),
                                if (e.details != null && e.details!.isNotEmpty)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 2),
                                    child: Text(
                                      e.details!,
                                      style: TextStyle(fontSize: 11, color: Colors.grey.shade700, fontFamily: 'monospace'),
                                    ),
                                  ),
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}