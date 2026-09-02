import 'dart:io';

/// Helper to persist raw exception details to a file so the real cause
/// of user-facing "unexpected error" messages can be diagnosed.
class ErrorLogger {
  static final File _file =
      File('${Directory.systemTemp.path}/yaseeno_errors.log');

  static Future<void> log(String screen, dynamic error,
      [StackTrace? stack]) async {
    try {
      final sink = _file.openSync(mode: FileMode.append);
      sink.writeStringSync(
          '[${DateTime.now().toIso8601String()}] $screen\n  $error\n');
      if (stack != null) {
        final lines = stack.toString().split('\n').take(8).join('\n');
        sink.writeStringSync('  $lines\n');
      }
      sink.writeStringSync('\n');
      sink.closeSync();
    } catch (_) {}
  }
}
