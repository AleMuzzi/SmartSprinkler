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
  bool _downloading = false;
  bool _deleting = false;
  String? _error;
  DateTime? _selectedDate;
  final Set<int> _expandedDetails = {};

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
      final dateStr = _selectedDate != null ? _fmtDate(_selectedDate!) : null;
      final entries = await _service.fetchLogEntries(
        filter: _filterController.text,
        category: _category.isEmpty ? null : _category,
        startDate: dateStr,
        endDate: dateStr,
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

  Future<void> _downloadCsv() async {
    setState(() {
      _downloading = true;
      _error = null;
    });
    try {
      final result = await _service.downloadCsv(
        filter: _filterController.text,
        category: _category.isEmpty ? null : _category,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Salvato: ${result.path}')),
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _downloading = false;
        });
      }
    }
  }

  Color _colorForCategory(String category) =>
      _categoryColors[category] ?? Colors.grey.shade700;

  String _fmtDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? now,
      firstDate: DateTime(now.year - 5),
      lastDate: now,
    );
    if (picked == null) return;
    setState(() => _selectedDate = DateTime(picked.year, picked.month, picked.day));
    _load();
  }

  bool get _hasActiveFilters =>
      _filterController.text.isNotEmpty ||
      _category.isNotEmpty ||
      _selectedDate != null;

  void _clearFilters() {
    _filterController.clear();
    setState(() {
      _category = '';
      _selectedDate = null;
    });
    _load();
  }

  Future<void> _confirmDelete() async {
    final dateStr = _selectedDate != null ? _fmtDate(_selectedDate!) : null;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminare i log?'),
        content: Text(
          dateStr != null
              ? 'Eliminare tutti i log del $dateStr?\nQuesta azione è irreversibile.'
              : 'Vuoi eliminare TUTTI i log audit?\nQuesta azione è irreversibile.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annulla'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text(
              'Elimina',
              style: TextStyle(color: Color(0xFFD32F2F)),
            ),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() {
      _deleting = true;
      _error = null;
    });
    try {
      final deleted = await _service.deleteLogEntries(
        startDate: dateStr,
        endDate: dateStr,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eliminati $deleted log')),
      );
      _load();
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString());
      }
    } finally {
      if (mounted) {
        setState(() => _deleting = false);
      }
    }
  }

  int get _errorCount =>
      _entries.where((e) => e.category == 'error').length;

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
          const SizedBox(height: 16),
          Row(
            children: [
              const Text(
                '📋 Audit Log',
                style: TextStyle(fontSize: 22),
              ),
              const SizedBox(width: 8),
              Text(
                '(${_entries.length} entries)',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
              const Spacer(),
              IconButton(
                onPressed: _downloading ? null : _downloadCsv,
                icon: _downloading
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.download),
                tooltip: 'Download CSV',
              ),
              IconButton(
                onPressed: _deleting ? null : _confirmDelete,
                icon: _deleting
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.delete_outline, color: Color(0xFFB71C1C)),
                tooltip: 'Elimina log',
              ),
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
              const SizedBox(width: 4),
              IconButton(
                onPressed: _pickDate,
                icon: const Icon(Icons.calendar_month, color: Color(0xFF1976D2)),
                tooltip: 'Filtra per data',
              ),
              const SizedBox(width: 4),
              IconButton(
                onPressed: _clearFilters,
                icon: Icon(
                  Icons.filter_alt_off,
                  color: _hasActiveFilters ? const Color(0xFFB71C1C) : Colors.grey.shade400,
                ),
                tooltip: 'Rimuovi tutti i filtri',
              ),
            ],
          ),
          if (_selectedDate != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE3F2FD),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.calendar_today, size: 14, color: Color(0xFF1976D2)),
                      const SizedBox(width: 6),
                      Text(
                        _fmtDate(_selectedDate!),
                        style: const TextStyle(
                          fontSize: 13,
                          color: Color(0xFF1565C0),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          const SizedBox(height: 12),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Text('⚠️ $_error', style: const TextStyle(color: Colors.red)),
            ),
          if (_errorCount > 0)
            Padding(
              padding: const EdgeInsets.only(bottom: 10.0),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFEBEE),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFF44336)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Color(0xFFB71C1C), size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '$_errorCount error${_errorCount == 1 ? '' : 's'} in this view',
                        style: const TextStyle(
                          color: Color(0xFFB71C1C),
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    ElevatedButton(
                      onPressed: () {
                        setState(() {
                          _category = _category == 'error' ? '' : 'error';
                        });
                        _load();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _category == 'error'
                            ? const Color(0xFF1976D2)
                            : const Color(0xFFB71C1C),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        minimumSize: const Size(0, 32),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: Text(_category == 'error' ? 'See all' : 'Show errors'),
                    ),
                  ],
                ),
              ),
            ),
          Expanded(
            child: _loading && _entries.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : _entries.isEmpty
                    ? const Center(child: Text('No log entries', style: TextStyle(color: Colors.grey)))
                    : ListView.separated(
                        itemCount: _entries.length,
                        separatorBuilder: (_, _) => const Divider(height: 1),
                        itemBuilder: (ctx, i) {
                          final e = _entries[i];
                          final color = _colorForCategory(e.category);
                          final isError = e.category == 'error';
                          final details = e.details ?? '';
                          final long = details.length > 120;
                          // Errors always show their full details (traceback)
                          // instead of a truncated preview.
                          final expanded = isError || _expandedDetails.contains(e.id);
                          return Container(
                            color: isError ? const Color(0x14F44336) : null,
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
                                if (details.isNotEmpty)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 2),
                                    child: InkWell(
                                      onTap: long
                                          ? () => setState(() {
                                                if (expanded) {
                                                  _expandedDetails.remove(e.id);
                                                } else {
                                                  _expandedDetails.add(e.id);
                                                }
                                              })
                                          : null,
                                      child: Text(
                                        long && !expanded ? '${details.substring(0, 120)}…' : details,
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: isError ? const Color(0xFF8B0000) : Colors.grey.shade700,
                                          fontFamily: 'monospace',
                                        ),
                                      ),
                                    ),
                                  ),
                                if (long)
                                  GestureDetector(
                                    onTap: () => setState(() {
                                      if (expanded) {
                                        _expandedDetails.remove(e.id);
                                      } else {
                                        _expandedDetails.add(e.id);
                                      }
                                    }),
                                    child: Padding(
                                      padding: const EdgeInsets.only(top: 2),
                                      child: Text(
                                        expanded ? '▲ collapse' : '▼ expand',
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: Colors.blue.shade700,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
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