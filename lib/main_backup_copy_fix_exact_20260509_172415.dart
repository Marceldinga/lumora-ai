import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:http/http.dart' as http;

// ================================================================
// LUMORA ADVANCED COMPLETE FRONTEND - main.dart
// Flutter Web + Netlify frontend for Railway/FastAPI backend.
//
// Build example:
// flutter build web --release \
//   --dart-define=LUMORA_BACKEND_URL=https://lumora-ai-production.up.railway.app
//
// IMPORTANT: Default backend is already set to your Railway URL,
// or override using --dart-define=LUMORA_BACKEND_URL=https://lumora-ai-production.up.railway.app
//
// Backend endpoints expected:
// POST /brain-chat  { message, mode, history, verify }
// POST /image       { prompt, style, width, height }
// POST /video       { prompt, style, seconds }
// GET  /health      optional, used for status chip
// ================================================================

const String kBackendBaseUrl = String.fromEnvironment(
  'LUMORA_BACKEND_URL',
  defaultValue: 'https://lumora-ai-production.up.railway.app',
);

const String kChatPath = '/chat';
const String kChatFallbackPath = '/chat-fast';
const String kImagePath = '/image';
const String kVideoPath = '/video';
const String kHealthPath = '/health';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const LumoraAIApp());
}

// ================================================================
// THEME + UTILITIES
// ================================================================

class LumoraColors {
  static const bg = Color(0xFF070A13);
  static const panel = Color(0xFF0F172A);
  static const panel2 = Color(0xFF111A2E);
  static const card = Color(0xFF101827);
  static const border = Color(0xFF263247);
  static const borderSoft = Color(0xFF1D2738);
  static const primary = Color(0xFF7C5CFF);
  static const primary2 = Color(0xFFBBA7FF);
  static const text = Color(0xFFE5E7EB);
  static const muted = Color(0xFFCBD5E1);
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFFBBF24);
  static const danger = Color(0xFFEF4444);
}

class LumoraTheme {
  static ThemeData dark() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: LumoraColors.primary,
      brightness: Brightness.dark,
    );

    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: LumoraColors.bg,
      colorScheme: colorScheme,
      useMaterial3: true,
      fontFamily: 'Inter',
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: LumoraColors.bg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: LumoraColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: LumoraColors.primary, width: 1.4),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: LumoraColors.primary2,
          side: const BorderSide(color: LumoraColors.border),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: LumoraColors.primary2),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: LumoraColors.panel2,
        selectedColor: LumoraColors.primary.withOpacity(0.25),
        side: const BorderSide(color: LumoraColors.border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: LumoraColors.panel,
        indicatorColor: LumoraColors.primary,
        selectedIconTheme: IconThemeData(color: Colors.white),
        unselectedIconTheme: IconThemeData(color: LumoraColors.muted),
        selectedLabelTextStyle: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
        unselectedLabelTextStyle: TextStyle(color: LumoraColors.muted),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: LumoraColors.panel,
        indicatorColor: LumoraColors.primary.withOpacity(0.30),
        labelTextStyle: MaterialStateProperty.resolveWith((states) {
          final selected = states.contains(MaterialState.selected);
          return TextStyle(
            color: selected ? Colors.white : LumoraColors.muted,
            fontWeight: selected ? FontWeight.bold : FontWeight.w500,
          );
        }),
      ),
    );
  }
}

String sanitizeBaseUrl(String value) => value.trim().replaceAll(RegExp(r'/+$'), '');

List<String> backendBaseCandidates() {
  final primary = sanitizeBaseUrl(kBackendBaseUrl);
  final candidates = <String>[primary];
  final lower = primary.toLowerCase();

  if (lower.contains('127.0.0.1') || lower.contains('localhost')) {
    candidates.add('https://lumora-ai-production.up.railway.app');
    candidates.add('https://lumora-ai-production.up.railway.app');
  }

  final seen = <String>{};
  return candidates.where((url) {
    if (url.isEmpty || seen.contains(url)) return false;
    seen.add(url);
    return true;
  }).toList();
}

String cleanPlainOutput(String value) {
  return value
      .replaceAll('**', '')
      .replaceAll('###', '')
      .replaceAll('##', '')
      .replaceAll(RegExp(r'\n{3,}'), '\n\n')
      .trim();
}

String enhanceStudyPrompt(String message, String mode) {
  final lower = message.toLowerCase();

  if (mode.toLowerCase() == 'study' &&
      lower.contains('group 2') &&
      (lower.contains('quiz') || lower.contains('question'))) {
    if (!lower.contains('chemistry') && !lower.contains('alkaline earth')) {
      return '$message\n\nContext: This is O Level Chemistry. Group 2 means Group 2 elements, the alkaline earth metals, not mathematics.';
    }
  }

  return message;
}

Future<void> copyToClipboard(BuildContext context, String text, String label) async {
  if (text.trim().isEmpty) return;
  await Clipboard.setData(ClipboardData(text: text));
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(label), duration: const Duration(seconds: 2)),
  );
}

void downloadTextFile(String filename, String text) {
  final bytes = utf8.encode(text);
  final blob = html.Blob([bytes], 'text/plain;charset=utf-8');
  final url = html.Url.createObjectUrlFromBlob(blob);
  html.AnchorElement(href: url)
    ..setAttribute('download', filename)
    ..click();
  html.Url.revokeObjectUrl(url);
}

String safeFileTimestamp() {
  final now = DateTime.now();
  String two(int value) => value.toString().padLeft(2, '0');
  return '${now.year}${two(now.month)}${two(now.day)}_${two(now.hour)}${two(now.minute)}${two(now.second)}';
}

// ================================================================
// API LAYER
// ================================================================




String normalizeLumoraDisplay(String input) {
  var s = input;

  // Preserve LaTeX exactly:
  // Inline math: \( ... \)
  // Display math: \[ ... \]
  // Do NOT convert LaTeX to plain text here. LumoraSmartText renders it.

  // Clean common mojibake without touching valid LaTeX.
  final replacements = <String, String>{
    'Â²âº': '^2+',
    'Â²â»': '^2-',
    'Â³âº': '^3+',
    'Â³â»': '^3-',
    'Âº': '+',
    'Â»': '-',
    'âº': '+',
    'â»': '-',
    'Â²': '^2',
    'Â³': '^3',
    '?': '+',
    '?': '-',
    '2': '_2',
    '3': '_3',
    'Â': '',
  };

  replacements.forEach((bad, good) {
    s = s.replaceAll(bad, good);
  });

  // Remove excessive blank lines only.
  s = s.replaceAll(RegExp(r'\n{4,}'), '\n\n\n');

  return s.trim();
}

class LumoraApiException implements Exception {
  final String message;
  final int? statusCode;

  const LumoraApiException(this.message, {this.statusCode});

  @override
  String toString() {
    if (statusCode == null) return message;
    return 'HTTP $statusCode: $message';
  }
}

class LumoraApi {
  static Future<http.Response> _postJson({
    required String path,
    required Map<String, dynamic> body,
    required Duration timeout,
  }) async {
    Object? lastError;

    for (final baseUrl in backendBaseCandidates()) {
      final uri = Uri.parse('$baseUrl$path');
      try {
        return await http
            .post(
              uri,
              headers: const {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
              },
              body: jsonEncode(body),
            )
            .timeout(timeout);
      } catch (e) {
        lastError = e;
      }
    }

    throw LumoraApiException('Could not reach Lumora backend. Last error: $lastError');
  }

  static Future<bool> ping() async {
    for (final baseUrl in backendBaseCandidates()) {
      try {
        final uri = Uri.parse('$baseUrl$kHealthPath');
        final response = await http.get(uri).timeout(const Duration(seconds: 8));
        if (response.statusCode >= 200 && response.statusCode < 500) return true;
      } catch (_) {
        // Try next candidate.
      }
    }
    return false;
  }

  static Future<String> chat({
    required String message,
    required String mode,
    List<Map<String, String>> history = const [],
  }) async {
    final enhancedMessage = enhanceStudyPrompt(message, mode);

    final requestBody = {
      'message': enhancedMessage,
      'prompt': enhancedMessage,
      'mode': mode,
      'history': history,
      'stream': false,
      'verify': true,
      'long_answer': mode.toLowerCase() == 'math' ||
          mode.toLowerCase() == 'research' ||
          mode.toLowerCase() == 'data',
      'use_search': enhancedMessage.toLowerCase().contains('latest') ||
          enhancedMessage.toLowerCase().contains('current') ||
          enhancedMessage.toLowerCase().contains('search the internet'),
    };

    http.Response response;
    try {
      response = await _postJson(
        path: kChatPath,
        timeout: const Duration(seconds: 75),
        body: requestBody,
      );

      if (response.statusCode == 404 || response.statusCode == 405) {
        response = await _postJson(
          path: kChatFallbackPath,
          timeout: const Duration(seconds: 75),
          body: requestBody,
        );
      }
    } on LumoraApiException catch (e) {
      if (e.statusCode == 404 || e.statusCode == 405) {
        response = await _postJson(
          path: kChatFallbackPath,
          timeout: const Duration(seconds: 75),
          body: requestBody,
        );
      } else {
        rethrow;
      }
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw LumoraApiException(response.body, statusCode: response.statusCode);
    }

    final raw = utf8.decode(response.bodyBytes);
    dynamic data;
    try {
      data = jsonDecode(raw);
    } catch (_) {
      return normalizeLumoraDisplay(cleanPlainOutput(raw));
    }

    if (data is Map<String, dynamic>) {
      final reply = data['reply'] ??
          data['response'] ??
          data['text'] ??
          data['answer'] ??
          data['content'] ??
          data['message'];

      if (reply is Map<String, dynamic> && reply['content'] != null) {
        return normalizeLumoraDisplay(cleanPlainOutput(reply['content'].toString()));
      }

      if (data['choices'] is List && (data['choices'] as List).isNotEmpty) {
        final choice = (data['choices'] as List).first;
        if (choice is Map<String, dynamic>) {
          final msg = choice['message'];
          if (msg is Map<String, dynamic> && msg['content'] != null) {
            return normalizeLumoraDisplay(cleanPlainOutput(msg['content'].toString()));
          }
          if (choice['text'] != null) return normalizeLumoraDisplay(cleanPlainOutput(choice['text'].toString()));
        }
      }

      return normalizeLumoraDisplay(cleanPlainOutput(reply?.toString() ?? 'No reply returned from backend.'));
    }

    return normalizeLumoraDisplay(cleanPlainOutput(data.toString()));
  }

  static Future<ImageGenerationResult> image({
    required String prompt,
    required String style,
    required int width,
    required int height,
  }) async {
    final response = await _postJson(
      path: kImagePath,
      timeout: const Duration(seconds: 210),
      body: {
        'prompt': prompt,
        'style': style,
        'width': width,
        'height': height,
      },
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw LumoraApiException(response.body, statusCode: response.statusCode);
    }

    final data = jsonDecode(response.body);
    if (data is! Map<String, dynamic>) {
      throw const LumoraApiException('Image endpoint returned an unexpected response.');
    }

    if (data['ok'] == false) {
      throw LumoraApiException(data['error']?.toString() ?? 'Image generation failed.');
    }

    final imageBase64 = data['image_base64']?.toString() ?? data['image']?.toString();
    if (imageBase64 == null || imageBase64.trim().isEmpty) {
      throw const LumoraApiException('Image endpoint did not return image_base64.');
    }

    return ImageGenerationResult(
      imageBytes: base64Decode(imageBase64),
      prompt: data['prompt']?.toString() ?? prompt,
      model: data['model']?.toString() ?? 'Unknown model',
      width: data['width'] is int ? data['width'] as int : width,
      height: data['height'] is int ? data['height'] as int : height,
    );
  }

  static Future<VideoGenerationResult> video({
    required String prompt,
    required String style,
    required int seconds,
  }) async {
    final response = await _postJson(
      path: kVideoPath,
      timeout: const Duration(seconds: 420),
      body: {
        'prompt': prompt,
        'style': style,
        'seconds': seconds,
      },
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw LumoraApiException(response.body, statusCode: response.statusCode);
    }

    final data = jsonDecode(response.body);
    if (data is! Map<String, dynamic>) {
      throw const LumoraApiException('Video endpoint returned an unexpected response.');
    }

    if (data['ok'] == false) {
      throw LumoraApiException(data['error']?.toString() ?? 'Video generation failed.');
    }

    final videoBase64 = data['video_base64']?.toString() ?? data['video']?.toString();
    if (videoBase64 == null || videoBase64.trim().isEmpty) {
      throw const LumoraApiException('Video endpoint did not return video_base64.');
    }

    return VideoGenerationResult(
      videoBytes: base64Decode(videoBase64),
      prompt: data['prompt']?.toString() ?? prompt,
      model: data['model']?.toString() ?? 'Unknown model',
      provider: data['provider']?.toString() ?? 'Unknown provider',
      seconds: data['seconds'] is int ? data['seconds'] as int : seconds,
      mimeType: data['mime_type']?.toString() ?? 'video/mp4',
    );
  }
}

// Backward-compatible wrappers in case you call these names elsewhere.
Future<String> callLumoraBackend({
  required String message,
  required String mode,
  List<Map<String, String>> history = const [],
}) {
  return LumoraApi.chat(message: message, mode: mode, history: history);
}

Future<ImageGenerationResult> callLumoraImageBackend({
  required String prompt,
  required String style,
  int width = 1024,
  int height = 1024,
}) {
  return LumoraApi.image(prompt: prompt, style: style, width: width, height: height);
}

Future<VideoGenerationResult> callLumoraVideoBackend({
  required String prompt,
  required String style,
  int seconds = 4,
}) {
  return LumoraApi.video(prompt: prompt, style: style, seconds: seconds);
}

// ================================================================
// MODELS
// ================================================================

class ChatMessage {
  final String role;
  final String text;
  final DateTime createdAt;

  ChatMessage({
    required this.role,
    required this.text,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();
}

class ImageGenerationResult {
  final Uint8List imageBytes;
  final String prompt;
  final String model;
  final int width;
  final int height;

  ImageGenerationResult({
    required this.imageBytes,
    required this.prompt,
    required this.model,
    required this.width,
    required this.height,
  });
}

class VideoGenerationResult {
  final Uint8List videoBytes;
  final String prompt;
  final String model;
  final String provider;
  final int seconds;
  final String mimeType;

  VideoGenerationResult({
    required this.videoBytes,
    required this.prompt,
    required this.model,
    required this.provider,
    required this.seconds,
    required this.mimeType,
  });
}

class ImageHistoryItem {
  final ImageGenerationResult image;
  final String explanation;
  final DateTime createdAt;

  ImageHistoryItem({
    required this.image,
    required this.explanation,
    required this.createdAt,
  });
}

class VideoHistoryItem {
  final VideoGenerationResult video;
  final String explanation;
  final DateTime createdAt;

  VideoHistoryItem({
    required this.video,
    required this.explanation,
    required this.createdAt,
  });
}

class DashboardCardData {
  final int index;
  final IconData icon;
  final String title;
  final String text;
  final String badge;

  const DashboardCardData({
    required this.index,
    required this.icon,
    required this.title,
    required this.text,
    required this.badge,
  });
}

typedef PromptBuilder = String Function(Map<String, String> values);

class ToolFieldConfig {
  final String key;
  final String label;
  final String hint;
  final int maxLines;
  final String initialValue;

  const ToolFieldConfig({
    required this.key,
    required this.label,
    required this.hint,
    this.maxLines = 1,
    this.initialValue = '',
  });
}

class GeneratedTextItem {
  final String title;
  final String text;
  final DateTime createdAt;

  GeneratedTextItem({
    required this.title,
    required this.text,
    required this.createdAt,
  });
}

// ================================================================
// APP SHELL
// ================================================================

class LumoraAIApp extends StatelessWidget {
  const LumoraAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lumora AI',
      debugShowCheckedModeBanner: false,
      theme: LumoraTheme.dark(),
      home: const LumoraHomePage(),
    );
  }
}

class LumoraHomePage extends StatefulWidget {
  const LumoraHomePage({super.key});

  @override
  State<LumoraHomePage> createState() => _LumoraHomePageState();
}

class _LumoraHomePageState extends State<LumoraHomePage> {
  int selectedIndex = 0;
  bool? backendOnline;

  @override
  void initState() {
    super.initState();
    checkBackend();
  }

  Future<void> checkBackend() async {
    setState(() => backendOnline = null);
    final ok = await LumoraApi.ping();
    if (!mounted) return;
    setState(() => backendOnline = ok);
  }

  bool _isMobileWidth(double width) => width < 900;

  int get _mobileNavIndex {
    if (selectedIndex == 0) return 0;
    if (selectedIndex == 1) return 1;
    if (selectedIndex == 2) return 2;
    if (selectedIndex == 3) return 3;
    return 4;
  }

  Widget _buildPage() {
    switch (selectedIndex) {
      case 0:
        return DashboardPage(onOpen: (index) => setState(() => selectedIndex = index));
      case 1:
        return const LumoraChatPage();
      case 2:
        return AiToolPage.studyPlanner();
      case 3:
        return AiToolPage.researchAssistant();
      case 4:
        return AiToolPage.quizGenerator();
      case 5:
        return AiToolPage.flashcards();
      case 6:
        return const ImageGeneratorPage();
      case 7:
        return const VideoGeneratorPage();
      case 8:
        return MoreToolsPage(onOpen: (index) => setState(() => selectedIndex = index));
      default:
        return const LumoraChatPage();
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = _isMobileWidth(constraints.maxWidth);

        final content = Column(
          children: [
            AppHeader(
              isMobile: isMobile,
              backendOnline: backendOnline,
              onRefreshBackend: checkBackend,
            ),
            Expanded(child: _buildPage()),
          ],
        );

        if (isMobile) {
          return Scaffold(
            resizeToAvoidBottomInset: true,
            body: SafeArea(child: content),
            bottomNavigationBar: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: NavigationBar(
                    selectedIndex: _mobileNavIndex,
                    height: 62,
                    labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
                    onDestinationSelected: (index) {
                      setState(() {
                        selectedIndex = index == 4 ? 8 : index;
                      });
                    },
                    destinations: const [
                      NavigationDestination(
                        icon: Icon(Icons.dashboard_outlined),
                        selectedIcon: Icon(Icons.dashboard),
                        label: 'Home',
                      ),
                      NavigationDestination(
                        icon: Icon(Icons.auto_awesome_outlined),
                        selectedIcon: Icon(Icons.auto_awesome),
                        label: 'Chat',
                      ),
                      NavigationDestination(
                        icon: Icon(Icons.menu_book_outlined),
                        selectedIcon: Icon(Icons.menu_book),
                        label: 'Study',
                      ),
                      NavigationDestination(
                        icon: Icon(Icons.article_outlined),
                        selectedIcon: Icon(Icons.article),
                        label: 'Research',
                      ),
                      NavigationDestination(
                        icon: Icon(Icons.apps_outlined),
                        selectedIcon: Icon(Icons.apps),
                        label: 'More',
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }

        return Scaffold(
          body: Row(
            children: [
              NavigationRail(
                selectedIndex: selectedIndex > 7 ? 0 : selectedIndex,
                labelType: NavigationRailLabelType.all,
                minWidth: 90,
                onDestinationSelected: (index) => setState(() => selectedIndex = index),
                destinations: const [
                  NavigationRailDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: Text('Home')),
                  NavigationRailDestination(icon: Icon(Icons.auto_awesome_outlined), selectedIcon: Icon(Icons.auto_awesome), label: Text('Chat')),
                  NavigationRailDestination(icon: Icon(Icons.menu_book_outlined), selectedIcon: Icon(Icons.menu_book), label: Text('Study')),
                  NavigationRailDestination(icon: Icon(Icons.article_outlined), selectedIcon: Icon(Icons.article), label: Text('Research')),
                  NavigationRailDestination(icon: Icon(Icons.quiz_outlined), selectedIcon: Icon(Icons.quiz), label: Text('Quiz')),
                  NavigationRailDestination(icon: Icon(Icons.style_outlined), selectedIcon: Icon(Icons.style), label: Text('Cards')),
                  NavigationRailDestination(icon: Icon(Icons.image_outlined), selectedIcon: Icon(Icons.image), label: Text('Image')),
                  NavigationRailDestination(icon: Icon(Icons.movie_creation_outlined), selectedIcon: Icon(Icons.movie_creation), label: Text('Video')),
                ],
              ),
              Expanded(child: content),
            ],
          ),
        );
      },
    );
  }
}

class AppHeader extends StatelessWidget {
  final bool isMobile;
  final bool? backendOnline;
  final VoidCallback onRefreshBackend;

  const AppHeader({
    super.key,
    required this.isMobile,
    required this.backendOnline,
    required this.onRefreshBackend,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: isMobile ? 58 : 78,
      padding: EdgeInsets.symmetric(horizontal: isMobile ? 14 : 24),
      decoration: const BoxDecoration(
        color: LumoraColors.panel,
        border: Border(bottom: BorderSide(color: LumoraColors.border)),
      ),
      child: Row(
        children: [
          Container(
            height: isMobile ? 36 : 44,
            width: isMobile ? 36 : 44,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [LumoraColors.primary, Color(0xFF38BDF8)],
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.lightbulb, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Lumora',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: isMobile ? 22 : 28,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          if (!isMobile)
            BackendStatusChip(status: backendOnline, onRefresh: onRefreshBackend)
          else
            IconButton(
              tooltip: 'Check backend',
              onPressed: onRefreshBackend,
              icon: Icon(
                backendOnline == true ? Icons.cloud_done : Icons.cloud_sync,
                color: backendOnline == false ? LumoraColors.danger : LumoraColors.primary2,
              ),
            ),
        ],
      ),
    );
  }
}

class BackendStatusChip extends StatelessWidget {
  final bool? status;
  final VoidCallback onRefresh;

  const BackendStatusChip({super.key, required this.status, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    final icon = status == null
        ? Icons.sync
        : status == true
            ? Icons.cloud_done
            : Icons.cloud_off;
    final label = status == null
        ? 'Checking'
        : status == true
            ? 'Backend online'
            : 'Backend offline';
    final color = status == null
        ? LumoraColors.warning
        : status == true
            ? LumoraColors.success
            : LumoraColors.danger;

    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onRefresh,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withOpacity(0.45)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 17, color: color),
            const SizedBox(width: 8),
            Text(label, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}

// ================================================================
// DASHBOARD
// ================================================================

class DashboardPage extends StatelessWidget {
  final void Function(int index) onOpen;

  const DashboardPage({super.key, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    final cards = const [
      DashboardCardData(index: 2, icon: Icons.menu_book, title: 'Study Planner', badge: 'Planning', text: 'Create personalized daily or weekly study plans by student level, goal, and schedule.'),
      DashboardCardData(index: 3, icon: Icons.article, title: 'Research Helper', badge: 'Academic', text: 'Generate summaries, thesis statements, outlines, research questions, and draft introductions.'),
      DashboardCardData(index: 4, icon: Icons.quiz, title: 'Quiz Generator', badge: 'Practice', text: 'Create quizzes with answers and explanations across levels and difficulty ranges.'),
      DashboardCardData(index: 5, icon: Icons.style, title: 'Flashcards', badge: 'Review', text: 'Turn notes into clean flashcards with Q/A formatting for fast revision.'),
      DashboardCardData(index: 6, icon: Icons.image, title: 'Image Generator', badge: 'Visual', text: 'Generate educational images, explanations, copyable prompts, and downloadable results.'),
      DashboardCardData(index: 7, icon: Icons.movie_creation, title: 'Video Generator', badge: 'Media', text: 'Generate short educational videos with notes, preview, download, and history.'),
    ];

    return SingleChildScrollView(
      padding: EdgeInsets.all(MediaQuery.of(context).size.width < 900 ? 14 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HeroPanel(onStart: () => onOpen(1)),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) {
              int columns = 3;
              if (constraints.maxWidth < 760) columns = 1;
              if (constraints.maxWidth >= 760 && constraints.maxWidth < 1180) columns = 2;

              return GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: columns,
                crossAxisSpacing: 18,
                mainAxisSpacing: 18,
                childAspectRatio: constraints.maxWidth < 760 ? 1.95 : 1.35,
                children: cards.map((card) => DashboardCard(data: card, onTap: () => onOpen(card.index))).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}


class MoreToolsPage extends StatelessWidget {
  final void Function(int index) onOpen;

  const MoreToolsPage({super.key, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    final tools = const [
      DashboardCardData(
        index: 4,
        icon: Icons.quiz,
        title: 'Quiz Generator',
        badge: 'Practice',
        text: 'Create quizzes with answers and explanations across levels and difficulty ranges.',
      ),
      DashboardCardData(
        index: 5,
        icon: Icons.style,
        title: 'Flashcards',
        badge: 'Review',
        text: 'Turn notes into clean flashcards with Q/A formatting for fast revision.',
      ),
      DashboardCardData(
        index: 6,
        icon: Icons.image,
        title: 'Image Generator',
        badge: 'Visual',
        text: 'Generate educational images, explanations, copyable prompts, and downloadable results.',
      ),
      DashboardCardData(
        index: 7,
        icon: Icons.movie_creation,
        title: 'Video Generator',
        badge: 'Media',
        text: 'Generate short educational videos with notes, preview, download, and history.',
      ),
    ];

    return ListView(
      padding: const EdgeInsets.all(14),
      children: [
        const Text(
          'More Tools',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 8),
        const Text(
          'Open quiz, flashcards, image, and video tools.',
          style: TextStyle(color: LumoraColors.muted),
        ),
        const SizedBox(height: 14),
        for (final tool in tools) ...[
          DashboardMobileToolTile(
            data: tool,
            onTap: () => onOpen(tool.index),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class DashboardMobileToolTile extends StatelessWidget {
  final DashboardCardData data;
  final VoidCallback onTap;

  const DashboardMobileToolTile({
    super.key,
    required this.data,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: onTap,
      child: GlassCard(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: LumoraColors.primary.withOpacity(0.18),
              child: Icon(data.icon, color: LumoraColors.primary2),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(data.title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text(
                    data.text,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: LumoraColors.muted, height: 1.35),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: LumoraColors.primary2),
          ],
        ),
      ),
    );
  }
}


class HeroPanel extends StatelessWidget {
  final VoidCallback onStart;

  const HeroPanel({super.key, required this.onStart});

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.of(context).size.width < 900;

    return GlassCard(
      padding: EdgeInsets.all(isMobile ? 18 : 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: LumoraColors.primary.withOpacity(0.16),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: LumoraColors.primary.withOpacity(0.35)),
            ),
            child: const Text(
              'Advanced AI learning suite',
              style: TextStyle(color: LumoraColors.primary2, fontWeight: FontWeight.bold),
            ),
          ),
          SizedBox(height: isMobile ? 14 : 18),
          Text(
            'Learn faster with Lumora.',
            style: TextStyle(
              fontSize: isMobile ? 26 : 34,
              fontWeight: FontWeight.w900,
              height: 1.1,
            ),
          ),
          SizedBox(height: isMobile ? 10 : 14),
          const Text(
            'Chat, study planning, research tools, quizzes, flashcards, images, and video in one clean learning workspace.',
            style: TextStyle(color: LumoraColors.muted, height: 1.5, fontSize: 15),
          ),
          SizedBox(height: isMobile ? 16 : 22),
          FilledButton.icon(
            onPressed: onStart,
            icon: const Icon(Icons.chat_bubble),
            label: const Text('Open AI Chat'),
          ),
        ],
      ),
    );
  }
}

class StatPill extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const StatPill({super.key, required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 185,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: LumoraColors.bg.withOpacity(0.58),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: LumoraColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(backgroundColor: LumoraColors.primary.withOpacity(0.18), child: Icon(icon, color: LumoraColors.primary2)),
          const SizedBox(height: 14),
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: LumoraColors.muted)),
        ],
      ),
    );
  }
}

class DashboardCard extends StatelessWidget {
  final DashboardCardData data;
  final VoidCallback onTap;

  const DashboardCard({super.key, required this.data, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: GlassCard(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(backgroundColor: LumoraColors.primary.withOpacity(0.18), child: Icon(data.icon, color: LumoraColors.primary2)),
                const Spacer(),
                Chip(label: Text(data.badge), visualDensity: VisualDensity.compact),
              ],
            ),
            const SizedBox(height: 18),
            Text(data.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            Expanded(
              child: Text(data.text, style: const TextStyle(color: LumoraColors.muted, height: 1.45)),
            ),
            const SizedBox(height: 8),
            const Row(
              children: [
                Text('Open', style: TextStyle(color: LumoraColors.primary2, fontWeight: FontWeight.bold)),
                SizedBox(width: 6),
                Icon(Icons.arrow_forward, size: 18, color: LumoraColors.primary2),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ================================================================
// CHAT PAGE
// ================================================================

class LumoraChatPage extends StatefulWidget {
  const LumoraChatPage({super.key});

  @override
  State<LumoraChatPage> createState() => _LumoraChatPageState();
}

class _LumoraChatPageState extends State<LumoraChatPage> {
  final TextEditingController controller = TextEditingController();
  final ScrollController scrollController = ScrollController();

  final List<ChatMessage> messages = [
    ChatMessage(
      role: 'assistant',
      text: 'Hello, I am Lumora â€” your advanced study, research, math, data, image, and video assistant. Ask me anything or choose a quick prompt below.',
    ),
  ];

  bool loading = false;
  String selectedMode = 'study';

  final quickPrompts = const [
    'Explain linear regression with a simple example.',
    'Create a 10-question O Level Chemistry quiz on Group 2 elements.',
    'Summarize my notes into flashcards.',
    'Give me a research outline for machine learning in healthcare.',
  ];

  Future<void> sendMessage([String? overrideText]) async {
    final text = (overrideText ?? controller.text).trim();
    if (text.isEmpty || loading) return;

    setState(() {
      messages.add(ChatMessage(role: 'user', text: text));
      controller.clear();
      loading = true;
    });
    _scrollToBottom();

    try {
      final history = messages
          .where((m) => m.text.trim().isNotEmpty)
          .take(messages.length - 1)
          .map((m) => {'role': m.role, 'content': m.text})
          .toList();

      final reply = await LumoraApi.chat(message: text, mode: selectedMode, history: history);
      if (!mounted) return;
      setState(() {
        messages.add(ChatMessage(role: 'assistant', text: reply));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        messages.add(
          ChatMessage(
            role: 'assistant',
            text: 'Lumora could not connect to the backend. Check your Railway URL, CORS settings, and /brain-chat endpoint.\n\nError: $e',
          ),
        );
      });
    } finally {
      if (mounted) setState(() => loading = false);
      _scrollToBottom();
    }
  }

  void clearChat() {
    setState(() {
      messages
        ..clear()
        ..add(ChatMessage(role: 'assistant', text: 'Chat cleared. What would you like to learn next?'));
    });
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 120), () {
      if (!scrollController.hasClients) return;
      scrollController.animateTo(
        scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  void dispose() {
    controller.dispose();
    scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ChatToolbar(
          selectedMode: selectedMode,
          onModeChanged: (mode) => setState(() => selectedMode = mode),
          onClear: clearChat,
        ),
        Expanded(
          child: ListView.builder(
            controller: scrollController,
            padding: EdgeInsets.fromLTRB(
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              220,
            ),
            itemCount: messages.length + (loading ? 1 : 0),
            itemBuilder: (context, index) {
              if (loading && index == messages.length) {
                return const ChatBubble(role: 'assistant', text: 'Thinking...');
              }
              final message = messages[index];
              return ChatBubble(role: message.role, text: message.text, createdAt: message.createdAt);
            },
          ),
        ),
        if (messages.length <= 2)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: quickPrompts.map((p) => ActionChip(label: Text(p), onPressed: () => sendMessage(p))).toList(),
              ),
            ),
          ),
        ChatComposer(controller: controller, loading: loading, onSend: () => sendMessage()),
      ],
    );
  }
}

class ChatToolbar extends StatelessWidget {
  final String selectedMode;
  final ValueChanged<String> onModeChanged;
  final VoidCallback onClear;

  const ChatToolbar({super.key, required this.selectedMode, required this.onModeChanged, required this.onClear});

  @override
  Widget build(BuildContext context) {
    const modes = ['study', 'math', 'research', 'writing', 'data', 'image', 'video'];

    return Container(
      padding: EdgeInsets.symmetric(horizontal: MediaQuery.of(context).size.width < 900 ? 10 : 16, vertical: MediaQuery.of(context).size.width < 900 ? 8 : 12),
      decoration: const BoxDecoration(
        color: LumoraColors.panel,
        border: Border(bottom: BorderSide(color: LumoraColors.border)),
      ),
      child: Row(
        children: [
          const Icon(Icons.tune, size: 20, color: LumoraColors.primary2),
          const SizedBox(width: 10),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: modes.map((mode) {
                  final selected = mode == selectedMode;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(mode[0].toUpperCase() + mode.substring(1)),
                      selected: selected,
                      onSelected: (_) => onModeChanged(mode),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          IconButton(tooltip: 'Clear chat', onPressed: onClear, icon: const Icon(Icons.delete_sweep_outlined)),
        ],
      ),
    );
  }
}

class ChatComposer extends StatelessWidget {
  final TextEditingController controller;
  final bool loading;
  final VoidCallback onSend;

  const ChatComposer({super.key, required this.controller, required this.loading, required this.onSend});

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.of(context).size.width < 900;

    return Container(
      padding: EdgeInsets.fromLTRB(isMobile ? 10 : 16, 10, isMobile ? 10 : 16, 10),
      decoration: const BoxDecoration(
        color: LumoraColors.panel,
        border: Border(top: BorderSide(color: LumoraColors.border)),
      ),
      child: isMobile
          ? Container(
              padding: const EdgeInsets.only(left: 14, right: 4),
              decoration: BoxDecoration(
                color: LumoraColors.bg,
                borderRadius: BorderRadius.circular(28),
                border: Border.all(color: LumoraColors.border),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller,
                      minLines: 1,
                      maxLines: 3,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => onSend(),
                      decoration: const InputDecoration(
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        filled: false,
                        hintText: 'Ask Lumora...',
                        contentPadding: EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                  IconButton.filled(
                    onPressed: loading ? null : onSend,
                    icon: loading
                        ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.send_rounded),
                  ),
                ],
              ),
            )
          : Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    minLines: 1,
                    maxLines: 5,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => onSend(),
                    decoration: const InputDecoration(
                      hintText: 'Ask Lumora. Example: Create a study plan for Python data analytics...',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: loading ? null : onSend,
                  icon: loading
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send),
                  label: Text(loading ? 'Wait' : 'Send'),
                ),
              ],
            ),
    );
  }
}

class ChatBubble extends StatelessWidget {
  final String role;
  final String text;
  final DateTime? createdAt;

  const ChatBubble({super.key, required this.role, required this.text, this.createdAt});

  @override
  Widget build(BuildContext context) {
    final isUser = role == 'user';
    final maxWidth = MediaQuery.of(context).size.width < 900 ? MediaQuery.of(context).size.width * 0.82 : 820.0;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: maxWidth),
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: EdgeInsets.symmetric(
          horizontal: MediaQuery.of(context).size.width < 900 ? 14 : 16,
          vertical: MediaQuery.of(context).size.width < 900 ? 10 : 16,
        ),
        decoration: BoxDecoration(
          color: isUser ? LumoraColors.primary : LumoraColors.card,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(20),
            topRight: const Radius.circular(20),
            bottomLeft: Radius.circular(isUser ? 20 : 6),
            bottomRight: Radius.circular(isUser ? 6 : 20),
          ),
          border: Border.all(color: isUser ? LumoraColors.primary2.withOpacity(0.35) : LumoraColors.border),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.14), blurRadius: 16, offset: const Offset(0, 8))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LumoraSmartText(
              text: text,
              style: TextStyle(height: 1.5, fontSize: 15, color: isUser ? Colors.white : LumoraColors.text),
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: () => copyToClipboard(context, text, 'Message copied'),
                  icon: const Icon(Icons.copy_rounded, size: 17),
                  label: const Text('Copy'),
                  style: TextButton.styleFrom(foregroundColor: isUser ? Colors.white70 : LumoraColors.primary2),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ================================================================
// GENERIC AI TOOL PAGE
// ================================================================

class AiToolPage extends StatefulWidget {
  final IconData icon;
  final String title;
  final String description;
  final String mode;
  final String buttonText;
  final List<ToolFieldConfig> fields;
  final PromptBuilder promptBuilder;

  const AiToolPage({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    required this.mode,
    required this.buttonText,
    required this.fields,
    required this.promptBuilder,
  });

  factory AiToolPage.studyPlanner() {
    return AiToolPage(
      icon: Icons.menu_book,
      title: 'Study Planner',
      description: 'Create personalized study plans for any learner level, goal, and available schedule.',
      mode: 'study',
      buttonText: 'Generate Study Plan',
      fields: const [
        ToolFieldConfig(key: 'student_name', label: 'Student name', hint: 'Example: Marcel Dinga'),
        ToolFieldConfig(key: 'topic', label: 'What do you want to study?', hint: 'Example: Python for Data Analytics'),
        ToolFieldConfig(key: 'goal', label: 'Goal', hint: 'Example: Prepare for an exam, finish a project, learn basics'),
        ToolFieldConfig(key: 'days', label: 'Number of days', hint: 'Example: 7 days'),
        ToolFieldConfig(key: 'education_level', label: 'Educational level', hint: 'Example: high school, college, masterâ€™s, certification, or all levels', initialValue: 'All educational levels'),
        ToolFieldConfig(key: 'skill_level', label: 'Skill level', hint: 'Example: beginner, intermediate, advanced, or all levels', initialValue: 'All skill levels'),
        ToolFieldConfig(key: 'time', label: 'Daily study time', hint: 'Example: 1 hour per day'),
      ],
      promptBuilder: (values) => '''
Create a complete personalized study plan.

Student name: ${values['student_name']}
Topic: ${values['topic']}
Goal: ${values['goal']}
Number of days: ${values['days']}
Educational level: ${values['education_level']}
Skill level: ${values['skill_level']}
Daily study time: ${values['time']}

Rules:
1. Start with the student name.
2. If educational level is "All educational levels", include Elementary, Middle School, High School, College, Graduate, and Certification sections.
3. If skill level is "All skill levels", include beginner, intermediate, and advanced progression.
4. Include daily topics, practice activities, review tasks, checkpoints, and final review.
5. Use clean plain text only.
6. Do not use Markdown bold symbols.
''',
    );
  }

  factory AiToolPage.researchAssistant() {
    return AiToolPage(
      icon: Icons.article,
      title: 'Research Assistant',
      description: 'Create structured research help: summaries, thesis statements, outlines, key points, and introductions.',
      mode: 'research',
      buttonText: 'Generate Research Help',
      fields: const [
        ToolFieldConfig(key: 'student_name', label: 'Student name', hint: 'Example: Marcel Dinga'),
        ToolFieldConfig(key: 'education_level', label: 'Educational level', hint: 'Example: college, masterâ€™s, doctoral, professional', initialValue: 'College / University Level'),
        ToolFieldConfig(key: 'topic', label: 'Research topic', hint: 'Example: The role of machine learning in healthcare'),
        ToolFieldConfig(key: 'purpose', label: 'Purpose', hint: 'Example: Academic paper, class assignment, proposal'),
        ToolFieldConfig(key: 'requirements', label: 'Requirements', hint: 'Example: APA style, 5 paragraphs, include introduction and conclusion', maxLines: 3),
        ToolFieldConfig(key: 'notes', label: 'Paste notes or ideas', hint: 'Paste your notes here. You can leave this blank.', maxLines: 6),
      ],
      promptBuilder: (values) => '''
Act as an academic research assistant.

Student name: ${values['student_name']}
Educational level: ${values['education_level']}
Research topic: ${values['topic']}
Purpose: ${values['purpose']}
Requirements: ${values['requirements']}
Notes: ${values['notes']}

Return:
1. Clear research summary
2. Strong thesis statement
3. Structured outline
4. Key discussion points
5. Possible research questions
6. Short draft introduction
7. Suggested search keywords

Rules:
- Match the writing to the selected educational level.
- Use academic but clear language.
- Use clean plain text only.
- Do not use Markdown bold symbols.
''',
    );
  }

  factory AiToolPage.quizGenerator() {
    return AiToolPage(
      icon: Icons.quiz,
      title: 'Quiz Generator',
      description: 'Generate personalized quizzes with answers and explanations from topics, notes, and difficulty levels.',
      mode: 'study',
      buttonText: 'Generate Quiz',
      fields: const [
        ToolFieldConfig(key: 'student_name', label: 'Student name', hint: 'Example: Marcel Dinga'),
        ToolFieldConfig(key: 'topic', label: 'Quiz topic', hint: 'Example: Linear regression or Group 2 elements'),
        ToolFieldConfig(key: 'count', label: 'Number of questions', hint: 'Example: 15'),
        ToolFieldConfig(key: 'education_level', label: 'Educational level', hint: 'Example: O Level, high school, college, masterâ€™s, all levels', initialValue: 'All educational levels'),
        ToolFieldConfig(key: 'difficulty', label: 'Difficulty level', hint: 'Example: beginner, intermediate, advanced, all levels', initialValue: 'All difficulty levels'),
        ToolFieldConfig(key: 'type', label: 'Question type', hint: 'Example: multiple choice, short answer, mixed'),
        ToolFieldConfig(key: 'notes', label: 'Paste notes', hint: 'Paste notes here if you want the quiz based on your notes.', maxLines: 6),
      ],
      promptBuilder: (values) => '''
Create a personalized quiz.

Student name: ${values['student_name']}
Topic: ${values['topic']}
Number of questions: ${values['count']}
Educational level: ${values['education_level']}
Difficulty level: ${values['difficulty']}
Question type: ${values['type']}
Notes: ${values['notes']}

Rules:
1. Start with the student name.
2. Include numbered questions.
3. Include answer choices if multiple choice.
4. Include the correct answer.
5. Include a short explanation for each answer.
6. If educational level is all levels, divide by level.
7. If difficulty is all levels, include beginner, intermediate, and advanced.
8. If the topic says Group 2 Elements, treat it as O Level Chemistry alkaline earth metals, not mathematics.
9. Use clean plain text only.
10. Do not use Markdown bold symbols.
''',
    );
  }

  factory AiToolPage.flashcards() {
    return AiToolPage(
      icon: Icons.style,
      title: 'Flashcards',
      description: 'Turn notes, topics, and definitions into clear question-and-answer flashcards.',
      mode: 'study',
      buttonText: 'Generate Flashcards',
      fields: const [
        ToolFieldConfig(key: 'student_name', label: 'Student name', hint: 'Example: Marcel Dinga'),
        ToolFieldConfig(key: 'topic', label: 'Flashcard topic', hint: 'Example: SQL joins'),
        ToolFieldConfig(key: 'count', label: 'Number of flashcards', hint: 'Example: 15'),
        ToolFieldConfig(key: 'education_level', label: 'Educational level', hint: 'Example: elementary, high school, college, all levels', initialValue: 'All educational levels'),
        ToolFieldConfig(key: 'difficulty', label: 'Difficulty level', hint: 'Example: beginner, intermediate, advanced, all levels', initialValue: 'All difficulty levels'),
        ToolFieldConfig(key: 'notes', label: 'Paste notes', hint: 'Paste notes or study material here.', maxLines: 8),
      ],
      promptBuilder: (values) => '''
Create personalized flashcards.

Student name: ${values['student_name']}
Topic: ${values['topic']}
Number of flashcards: ${values['count']}
Educational level: ${values['education_level']}
Difficulty level: ${values['difficulty']}
Notes: ${values['notes']}

Rules:
1. Return exactly the requested number of flashcards.
2. Start with the student name.
3. Match the selected education level and difficulty.
4. Do not add introduction or closing comments.
5. Do not use Markdown bold symbols.
6. Use clean plain text only.

Use this format:
Student: ${values['student_name']}

Flashcard 1
Q: question here
A: answer here

Flashcard 2
Q: question here
A: answer here
''',
    );
  }

  @override
  State<AiToolPage> createState() => _AiToolPageState();
}

class _AiToolPageState extends State<AiToolPage> {
  late final Map<String, TextEditingController> controllers;
  bool loading = false;
  String? result;
  String? error;
  final List<GeneratedTextItem> history = [];

  @override
  void initState() {
    super.initState();
    controllers = {for (final field in widget.fields) field.key: TextEditingController(text: field.initialValue)};
  }

  @override
  void dispose() {
    for (final c in controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> generate() async {
    final values = {for (final entry in controllers.entries) entry.key: entry.value.text.trim()};
    final prompt = widget.promptBuilder(values).trim();
    if (prompt.isEmpty || loading) return;

    setState(() {
      loading = true;
      result = null;
      error = null;
    });

    try {
      final reply = await LumoraApi.chat(message: prompt, mode: widget.mode);
      if (!mounted) return;
      setState(() {
        result = reply;
        history.insert(0, GeneratedTextItem(title: widget.title, text: reply, createdAt: DateTime.now()));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = 'Lumora could not generate the result. Check your Railway backend URL and /brain-chat endpoint.\n\nError: $e';
      });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void resetFields() {
    for (final field in widget.fields) {
      controllers[field.key]?.text = field.initialValue;
    }
    setState(() {
      result = null;
      error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1080),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              PageIntroCard(icon: widget.icon, title: widget.title, description: widget.description),
              const SizedBox(height: 20),
              GlassCard(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final field in widget.fields) ...[
                      FieldLabel(field.label),
                      const SizedBox(height: 8),
                      TextField(
                        controller: controllers[field.key],
                        maxLines: field.maxLines,
                        decoration: InputDecoration(hintText: field.hint),
                      ),
                      const SizedBox(height: 16),
                    ],
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: [
                        FilledButton.icon(
                          onPressed: loading ? null : generate,
                          icon: loading
                              ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.auto_awesome),
                          label: Text(loading ? 'Generating...' : widget.buttonText),
                        ),
                        OutlinedButton.icon(onPressed: loading ? null : resetFields, icon: const Icon(Icons.refresh), label: const Text('Reset')),
                      ],
                    ),
                  ],
                ),
              ),
              if (error != null || result != null) ...[
                const SizedBox(height: 20),
                ResultCard(title: 'Lumora Result', text: result, error: error),
              ],
              if (history.length > 1) ...[
                const SizedBox(height: 20),
                HistoryTextPanel(history: history, onRestore: (item) => setState(() => result = item.text)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ================================================================
// IMAGE GENERATOR
// ================================================================

class ImageGeneratorPage extends StatefulWidget {
  const ImageGeneratorPage({super.key});

  @override
  State<ImageGeneratorPage> createState() => _ImageGeneratorPageState();
}

class _ImageGeneratorPageState extends State<ImageGeneratorPage> {
  final TextEditingController promptController = TextEditingController(
    text: 'A clean 3D educational diagram of an atom with a glowing nucleus, red protons, blue neutrons, and three electrons orbiting around the nucleus in smooth circular paths. No text labels inside the image.',
  );
  final TextEditingController styleController = TextEditingController(
    text: 'clean 3D science illustration, educational diagram, no text, no labels, sharp and large',
  );

  int imageSize = 1024;
  bool loading = false;
  String? error;
  String? generatedText;
  ImageGenerationResult? result;
  final List<ImageHistoryItem> imageHistory = [];

  Future<void> generateImage() async {
    final prompt = promptController.text.trim();
    final style = styleController.text.trim();
    if (prompt.isEmpty || loading) return;

    setState(() {
      loading = true;
      error = null;
      generatedText = null;
      result = null;
    });

    try {
      final imageResult = await LumoraApi.image(
        prompt: prompt,
        style: style.isEmpty ? 'professional educational image' : style,
        width: imageSize,
        height: imageSize,
      );

      final explanationPrompt = '''
Create clean educational labels and a beginner-friendly explanation for this generated image.

Image topic/prompt:
$prompt

Style:
$style

Return:
1. Clean title
2. Main labels
3. Short explanation for each label
4. Beginner-friendly summary
5. Study questions

Rules:
- Use clean plain text only.
- Do not use Markdown bold symbols.
- Do not invent details unrelated to the image topic.
''';

      final textResult = await LumoraApi.chat(message: explanationPrompt, mode: 'study');
      if (!mounted) return;
      setState(() {
        result = imageResult;
        generatedText = textResult;
        imageHistory.insert(0, ImageHistoryItem(image: imageResult, explanation: textResult, createdAt: DateTime.now()));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = 'Lumora could not generate the image or explanation. Check your Railway backend and /image endpoint.\n\nError: $e';
      });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void downloadGeneratedImage([ImageGenerationResult? image]) {
    final imageToDownload = image ?? result;
    if (imageToDownload == null) return;
    final blob = html.Blob([imageToDownload.imageBytes], 'image/png');
    final url = html.Url.createObjectUrlFromBlob(blob);
    html.AnchorElement(href: url)
      ..setAttribute('download', 'lumora_image_${safeFileTimestamp()}.png')
      ..click();
    html.Url.revokeObjectUrl(url);
  }

  void restoreHistoryItem(ImageHistoryItem item) {
    setState(() {
      result = item.image;
      generatedText = item.explanation;
      promptController.text = item.image.prompt;
    });
  }

  @override
  void dispose() {
    promptController.dispose();
    styleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const PageIntroCard(
                icon: Icons.image,
                title: 'Image Generator',
                description: 'Generate educational images, create clean labels, copy prompts, download images, and keep history while the app is open.',
              ),
              const SizedBox(height: 20),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 980;
                  final form = ImageFormCard(
                    promptController: promptController,
                    styleController: styleController,
                    imageSize: imageSize,
                    loading: loading,
                    onSizeChanged: (v) => setState(() => imageSize = v),
                    onGenerate: generateImage,
                  );
                  final output = ImageResultCard(
                    result: result,
                    error: error,
                    generatedText: generatedText,
                    onDownload: () => downloadGeneratedImage(),
                  );

                  if (!wide) return Column(children: [form, const SizedBox(height: 20), output]);
                  return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: form), const SizedBox(width: 20), Expanded(child: output)]);
                },
              ),
              if (imageHistory.isNotEmpty) ...[
                const SizedBox(height: 20),
                ImageHistoryPanel(items: imageHistory, onRestore: restoreHistoryItem, onDownload: downloadGeneratedImage),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class ImageFormCard extends StatelessWidget {
  final TextEditingController promptController;
  final TextEditingController styleController;
  final int imageSize;
  final bool loading;
  final ValueChanged<int> onSizeChanged;
  final VoidCallback onGenerate;

  const ImageFormCard({
    super.key,
    required this.promptController,
    required this.styleController,
    required this.imageSize,
    required this.loading,
    required this.onSizeChanged,
    required this.onGenerate,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const FieldLabel('Image prompt'),
          const SizedBox(height: 8),
          TextField(controller: promptController, maxLines: 6, decoration: const InputDecoration(hintText: 'Describe the image you want Lumora to create.')),
          const SizedBox(height: 16),
          const FieldLabel('Style'),
          const SizedBox(height: 8),
          TextField(controller: styleController, maxLines: 3, decoration: const InputDecoration(hintText: 'Example: clean 3D science illustration, no text, sharp and large')),
          const SizedBox(height: 16),
          const FieldLabel('Image size'),
          const SizedBox(height: 8),
          DropdownButtonFormField<int>(
            value: imageSize,
            decoration: const InputDecoration(),
            items: const [512, 768, 1024].map((size) => DropdownMenuItem(value: size, child: Text('$size x $size'))).toList(),
            onChanged: loading ? null : (value) {
              if (value != null) onSizeChanged(value);
            },
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ActionChip(label: const Text('Science diagram'), onPressed: () => styleController.text = 'clean 3D science illustration, educational diagram, no text, no labels'),
              ActionChip(label: const Text('Realistic'), onPressed: () => styleController.text = 'realistic educational image, cinematic lighting, sharp details'),
              ActionChip(label: const Text('Cartoon'), onPressed: () => styleController.text = 'friendly cartoon educational illustration, bright colors, no text'),
            ],
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: loading ? null : onGenerate,
            icon: loading ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.image),
            label: Text(loading ? 'Generating Image + Text...' : 'Generate Image + Text'),
          ),
        ],
      ),
    );
  }
}

class ImageResultCard extends StatelessWidget {
  final ImageGenerationResult? result;
  final String? error;
  final String? generatedText;
  final VoidCallback onDownload;

  const ImageResultCard({super.key, required this.result, required this.error, required this.generatedText, required this.onDownload});

  @override
  Widget build(BuildContext context) {
    if (error != null) return ErrorCard(error!);

    if (result == null) {
      return const EmptyStateCard(title: 'Generated Image', message: 'Your generated image, educational labels, prompt, copy buttons, and download button will appear here.');
    }

    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Generated Image', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          ClipRRect(borderRadius: BorderRadius.circular(20), child: Image.memory(result!.imageBytes, fit: BoxFit.contain)),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(onPressed: onDownload, icon: const Icon(Icons.download), label: const Text('Download Image')),
              OutlinedButton.icon(onPressed: () => copyToClipboard(context, result!.prompt, 'Prompt copied'), icon: const Icon(Icons.copy), label: const Text('Copy Prompt')),
              OutlinedButton.icon(onPressed: () => copyToClipboard(context, generatedText ?? '', 'Explanation copied'), icon: const Icon(Icons.copy_all), label: const Text('Copy Text')),
            ],
          ),
          const SizedBox(height: 16),
          Text('Model: ${result!.model}', style: const TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 4),
          Text('Size: ${result!.width} x ${result!.height}', style: const TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 16),
          CopyBox(label: 'Prompt', text: result!.prompt),
          const SizedBox(height: 18),
          CopyBox(label: 'Clean Text Labels', text: generatedText ?? 'Generating explanation...', multiline: true),
        ],
      ),
    );
  }
}

class ImageHistoryPanel extends StatelessWidget {
  final List<ImageHistoryItem> items;
  final ValueChanged<ImageHistoryItem> onRestore;
  final void Function(ImageGenerationResult image) onDownload;

  const ImageHistoryPanel({super.key, required this.items, required this.onRestore, required this.onDownload});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Image History', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          const Text('History is stored while the app is open. Use Download Image to save permanently.', style: TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 16),
          for (final item in items.take(12))
            HistoryTile(
              leading: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(item.image.imageBytes, width: 92, height: 92, fit: BoxFit.cover),
              ),
              title: item.createdAt.toLocal().toString().split('.').first,
              subtitle: item.image.prompt,
              actions: [
                OutlinedButton.icon(onPressed: () => onRestore(item), icon: const Icon(Icons.visibility), label: const Text('View')),
                OutlinedButton.icon(onPressed: () => onDownload(item.image), icon: const Icon(Icons.download), label: const Text('Download')),
              ],
            ),
        ],
      ),
    );
  }
}

// ================================================================
// VIDEO GENERATOR
// ================================================================

class VideoGeneratorPage extends StatefulWidget {
  const VideoGeneratorPage({super.key});

  @override
  State<VideoGeneratorPage> createState() => _VideoGeneratorPageState();
}

class _VideoGeneratorPageState extends State<VideoGeneratorPage> {
  final TextEditingController promptController = TextEditingController(
    text: 'A short educational animation showing an atom with electrons smoothly orbiting around a glowing nucleus. No readable text inside the video.',
  );
  final TextEditingController styleController = TextEditingController(
    text: 'educational science animation, clean 3D style, smooth motion, no text, no labels',
  );

  int seconds = 4;
  bool loading = false;
  String? error;
  String? generatedText;
  VideoGenerationResult? result;
  String? videoUrl;
  String? videoViewType;
  final List<VideoHistoryItem> videoHistory = [];

  Future<void> generateVideo() async {
    final prompt = promptController.text.trim();
    final style = styleController.text.trim();
    if (prompt.isEmpty || loading) return;

    setState(() {
      loading = true;
      error = null;
      generatedText = null;
      result = null;
    });

    try {
      final videoResult = await LumoraApi.video(
        prompt: prompt,
        style: style.isEmpty ? 'professional educational video' : style,
        seconds: seconds,
      );
      _prepareVideoPreview(videoResult);

      final explanationPrompt = '''
Create clean educational notes and a beginner-friendly explanation for this generated video.

Video topic/prompt:
$prompt

Style:
$style

Return:
1. Clean title
2. What the viewer should notice
3. Short explanation of the main parts
4. Beginner-friendly summary
5. Three study questions

Rules:
- Use clean plain text only.
- Do not use Markdown bold symbols.
- Do not invent details unrelated to the video topic.
''';

      final textResult = await LumoraApi.chat(message: explanationPrompt, mode: 'study');
      if (!mounted) return;
      setState(() {
        result = videoResult;
        generatedText = textResult;
        videoHistory.insert(0, VideoHistoryItem(video: videoResult, explanation: textResult, createdAt: DateTime.now()));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = 'Lumora could not generate the video or explanation. Video generation can take longer and may require Hugging Face provider access.\n\nError: $e';
      });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _prepareVideoPreview(VideoGenerationResult video) {
    if (videoUrl != null) html.Url.revokeObjectUrl(videoUrl!);

    final blob = html.Blob([video.videoBytes], video.mimeType);
    final url = html.Url.createObjectUrlFromBlob(blob);
    final viewType = 'lumora-video-${DateTime.now().microsecondsSinceEpoch}';

    final videoElement = html.VideoElement()
      ..src = url
      ..controls = true
      ..autoplay = false
      ..loop = true
      ..muted = true
      ..style.width = '100%'
      ..style.height = '100%'
      ..style.borderRadius = '20px'
      ..style.backgroundColor = '#000000';

    ui_web.platformViewRegistry.registerViewFactory(viewType, (int viewId) => videoElement);
    videoUrl = url;
    videoViewType = viewType;
  }

  void downloadGeneratedVideo([VideoGenerationResult? video]) {
    final videoToDownload = video ?? result;
    if (videoToDownload == null) return;
    final blob = html.Blob([videoToDownload.videoBytes], videoToDownload.mimeType);
    final url = html.Url.createObjectUrlFromBlob(blob);
    html.AnchorElement(href: url)
      ..setAttribute('download', 'lumora_video_${safeFileTimestamp()}.mp4')
      ..click();
    html.Url.revokeObjectUrl(url);
  }

  void restoreHistoryItem(VideoHistoryItem item) {
    setState(() {
      result = item.video;
      generatedText = item.explanation;
      promptController.text = item.video.prompt;
      seconds = item.video.seconds;
      _prepareVideoPreview(item.video);
    });
  }

  @override
  void dispose() {
    if (videoUrl != null) html.Url.revokeObjectUrl(videoUrl!);
    promptController.dispose();
    styleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1180),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const PageIntroCard(
                icon: Icons.movie_creation,
                title: 'Video Generator',
                description: 'Generate short educational videos, preview them inside Flutter Web, create clean notes, download video files, and keep session history.',
              ),
              const SizedBox(height: 20),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 980;
                  final form = VideoFormCard(
                    promptController: promptController,
                    styleController: styleController,
                    seconds: seconds,
                    loading: loading,
                    onSecondsChanged: (v) => setState(() => seconds = v),
                    onGenerate: generateVideo,
                  );
                  final output = VideoResultCard(
                    result: result,
                    error: error,
                    generatedText: generatedText,
                    videoViewType: videoViewType,
                    onDownload: () => downloadGeneratedVideo(),
                  );

                  if (!wide) return Column(children: [form, const SizedBox(height: 20), output]);
                  return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: form), const SizedBox(width: 20), Expanded(child: output)]);
                },
              ),
              if (videoHistory.isNotEmpty) ...[
                const SizedBox(height: 20),
                VideoHistoryPanel(items: videoHistory, onRestore: restoreHistoryItem, onDownload: downloadGeneratedVideo),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class VideoFormCard extends StatelessWidget {
  final TextEditingController promptController;
  final TextEditingController styleController;
  final int seconds;
  final bool loading;
  final ValueChanged<int> onSecondsChanged;
  final VoidCallback onGenerate;

  const VideoFormCard({
    super.key,
    required this.promptController,
    required this.styleController,
    required this.seconds,
    required this.loading,
    required this.onSecondsChanged,
    required this.onGenerate,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const FieldLabel('Video prompt'),
          const SizedBox(height: 8),
          TextField(controller: promptController, maxLines: 6, decoration: const InputDecoration(hintText: 'Describe the educational video you want Lumora to create.')),
          const SizedBox(height: 16),
          const FieldLabel('Style'),
          const SizedBox(height: 8),
          TextField(controller: styleController, maxLines: 3, decoration: const InputDecoration(hintText: 'Example: educational science animation, clean 3D style, smooth motion')),
          const SizedBox(height: 16),
          const FieldLabel('Duration'),
          const SizedBox(height: 8),
          DropdownButtonFormField<int>(
            value: seconds,
            decoration: const InputDecoration(),
            items: const [3, 4, 5, 6, 8].map((s) => DropdownMenuItem(value: s, child: Text('$s seconds'))).toList(),
            onChanged: loading ? null : (value) {
              if (value != null) onSecondsChanged(value);
            },
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: loading ? null : onGenerate,
            icon: loading ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.movie_creation),
            label: Text(loading ? 'Generating Video...' : 'Generate Video'),
          ),
        ],
      ),
    );
  }
}

class VideoResultCard extends StatelessWidget {
  final VideoGenerationResult? result;
  final String? error;
  final String? generatedText;
  final String? videoViewType;
  final VoidCallback onDownload;

  const VideoResultCard({super.key, required this.result, required this.error, required this.generatedText, required this.videoViewType, required this.onDownload});

  @override
  Widget build(BuildContext context) {
    if (error != null) return ErrorCard(error!);
    if (result == null || videoViewType == null) {
      return const EmptyStateCard(title: 'Generated Video', message: 'Your generated video preview, notes, copy buttons, download button, and history will appear here.');
    }

    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Generated Video', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          SizedBox(
            height: 360,
            child: ClipRRect(borderRadius: BorderRadius.circular(20), child: HtmlElementView(viewType: videoViewType!)),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(onPressed: onDownload, icon: const Icon(Icons.download), label: const Text('Download Video')),
              OutlinedButton.icon(onPressed: () => copyToClipboard(context, result!.prompt, 'Video prompt copied'), icon: const Icon(Icons.copy), label: const Text('Copy Prompt')),
              OutlinedButton.icon(onPressed: () => copyToClipboard(context, generatedText ?? '', 'Video notes copied'), icon: const Icon(Icons.copy_all), label: const Text('Copy Text')),
            ],
          ),
          const SizedBox(height: 16),
          Text('Model: ${result!.model}', style: const TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 4),
          Text('Provider: ${result!.provider}', style: const TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 4),
          Text('Duration: about ${result!.seconds} seconds', style: const TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 16),
          CopyBox(label: 'Prompt', text: result!.prompt),
          const SizedBox(height: 18),
          CopyBox(label: 'Clean Video Notes', text: generatedText ?? 'Generating explanation...', multiline: true),
        ],
      ),
    );
  }
}

class VideoHistoryPanel extends StatelessWidget {
  final List<VideoHistoryItem> items;
  final ValueChanged<VideoHistoryItem> onRestore;
  final void Function(VideoGenerationResult video) onDownload;

  const VideoHistoryPanel({super.key, required this.items, required this.onRestore, required this.onDownload});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Video History', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          const Text('History is stored while the app is open. Use Download Video to save permanently.', style: TextStyle(color: LumoraColors.muted)),
          const SizedBox(height: 16),
          for (final item in items.take(12))
            HistoryTile(
              leading: const CircleAvatar(radius: 34, backgroundColor: Color(0xFF211A4A), child: Icon(Icons.movie_creation, color: LumoraColors.primary2)),
              title: item.createdAt.toLocal().toString().split('.').first,
              subtitle: item.video.prompt,
              actions: [
                OutlinedButton.icon(onPressed: () => onRestore(item), icon: const Icon(Icons.visibility), label: const Text('View')),
                OutlinedButton.icon(onPressed: () => onDownload(item.video), icon: const Icon(Icons.download), label: const Text('Download')),
              ],
            ),
        ],
      ),
    );
  }
}

// ================================================================
// SMART TEXT + COMMON WIDGETS
// ================================================================


class LumoraSmartText extends StatelessWidget {
  final String text;
  final bool selectable;
  final TextStyle? style;

  const LumoraSmartText({
    super.key,
    required this.text,
    this.selectable = false,
    this.style,
  });

  TextStyle get _baseStyle =>
      style ??
      const TextStyle(
        height: 1.5,
        fontSize: 15,
        color: LumoraColors.text,
      );

  @override
  Widget build(BuildContext context) {
    final normalized = _normalizeForRendering(text);

    final blocks = _splitDisplayMath(normalized);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final block in blocks)
          if (block.isDisplayMath)
            _DisplayMathBlock(latex: block.content, style: _baseStyle)
          else
            ..._buildTextBlocks(block.content),
      ],
    );
  }

  String _normalizeForRendering(String input) {
    var s = input;

    // Normalize Windows/escaped newlines.
    s = s.replaceAll('\r\n', '\n');

    // Convert $$...$$ to \[...\] equivalent internally by display splitter.
    // Keep \( ... \) and \[ ... \) untouched.
    s = s.replaceAll(RegExp(r'\n{4,}'), '\n\n\n');

    return s.trim();
  }

  List<_LatexBlock> _splitDisplayMath(String input) {
    final blocks = <_LatexBlock>[];

    final pattern = RegExp(
      r'(\\\[(.*?)\\\]|\$\$(.*?)\$\$)',
      dotAll: true,
    );

    var last = 0;

    for (final match in pattern.allMatches(input)) {
      if (match.start > last) {
        blocks.add(_LatexBlock.text(input.substring(last, match.start)));
      }

      final latex = (match.group(2) ?? match.group(3) ?? '').trim();
      blocks.add(_LatexBlock.math(latex));

      last = match.end;
    }

    if (last < input.length) {
      blocks.add(_LatexBlock.text(input.substring(last)));
    }

    return blocks;
  }

  List<Widget> _buildTextBlocks(String content) {
    final widgets = <Widget>[];
    final lines = content.split('\n');

    var i = 0;
    while (i < lines.length) {
      final line = lines[i];

      if (line.trim().isEmpty) {
        widgets.add(const SizedBox(height: 10));
        i++;
        continue;
      }

      if (_isMarkdownTableStart(lines, i)) {
        final tableLines = <String>[];
        tableLines.add(lines[i]);
        i++;

        // Skip separator row.
        if (i < lines.length && _isTableSeparator(lines[i])) {
          i++;
        }

        while (i < lines.length && _isTableRow(lines[i])) {
          tableLines.add(lines[i]);
          i++;
        }

        widgets.add(_MarkdownTable(lines: tableLines, style: _baseStyle));
        widgets.add(const SizedBox(height: 12));
        continue;
      }

      if (_isHeading(line)) {
        widgets.add(
          Padding(
            padding: const EdgeInsets.only(top: 10, bottom: 6),
            child: _InlineLatexText(
              text: line.replaceFirst(RegExp(r'^#{1,6}\s*'), '').trim(),
              style: _baseStyle.copyWith(
                fontSize: (_baseStyle.fontSize ?? 15) + 2,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        );
        i++;
        continue;
      }

      if (_isBullet(line)) {
        final bulletLines = <String>[];
        while (i < lines.length && _isBullet(lines[i])) {
          bulletLines.add(lines[i]);
          i++;
        }

        widgets.add(
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final bullet in bulletLines)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('• ', style: _baseStyle),
                        Expanded(
                          child: _InlineLatexText(
                            text: bullet.replaceFirst(RegExp(r'^\s*[-*]\s+'), ''),
                            style: _baseStyle,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        );
        continue;
      }

      // Normal paragraph: collect until blank, display math, table, heading, or bullet.
      final paragraphLines = <String>[line.trim()];
      i++;

      while (i < lines.length &&
          lines[i].trim().isNotEmpty &&
          !_isMarkdownTableStart(lines, i) &&
          !_isHeading(lines[i]) &&
          !_isBullet(lines[i])) {
        paragraphLines.add(lines[i].trim());
        i++;
      }

      widgets.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _InlineLatexText(
            text: paragraphLines.join(' '),
            style: _baseStyle,
          ),
        ),
      );
    }

    return widgets;
  }

  bool _isHeading(String line) => RegExp(r'^\s*#{1,6}\s+').hasMatch(line);

  bool _isBullet(String line) => RegExp(r'^\s*[-*]\s+').hasMatch(line);

  bool _isTableRow(String line) {
    final t = line.trim();
    return t.startsWith('|') && t.endsWith('|') && t.split('|').length >= 3;
  }

  bool _isTableSeparator(String line) {
    return RegExp(r'^\s*\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|\s*$')
        .hasMatch(line);
  }

  bool _isMarkdownTableStart(List<String> lines, int index) {
    if (index >= lines.length) return false;
    if (!_isTableRow(lines[index])) return false;
    if (index + 1 >= lines.length) return false;
    return _isTableSeparator(lines[index + 1]);
  }
}

class _LatexBlock {
  final bool isDisplayMath;
  final String content;

  const _LatexBlock._(this.isDisplayMath, this.content);

  factory _LatexBlock.text(String content) => _LatexBlock._(false, content);
  factory _LatexBlock.math(String content) => _LatexBlock._(true, content);
}

class _InlineLatexText extends StatelessWidget {
  final String text;
  final TextStyle style;

  const _InlineLatexText({
    required this.text,
    required this.style,
  });

  @override
  Widget build(BuildContext context) {
    final spans = <InlineSpan>[];

    final pattern = RegExp(r'\\\((.*?)\\\)', dotAll: true);
    var last = 0;

    for (final match in pattern.allMatches(text)) {
      if (match.start > last) {
        spans.add(TextSpan(text: _cleanMarkdown(text.substring(last, match.start)), style: style));
      }

      final latex = match.group(1)?.trim() ?? '';

      spans.add(
        WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: Math.tex(
              latex,
              textStyle: style.copyWith(
                fontSize: (style.fontSize ?? 15) + 1,
                color: style.color ?? LumoraColors.text,
              ),
              mathStyle: MathStyle.text,
              onErrorFallback: (error) => Text(latex, style: style),
            ),
          ),
        ),
      );

      last = match.end;
    }

    if (last < text.length) {
      spans.add(TextSpan(text: _cleanMarkdown(text.substring(last)), style: style));
    }

    return RichText(
      text: TextSpan(children: spans),
      softWrap: true,
    );
  }

  String _cleanMarkdown(String value) {
    var s = value;

    // Basic inline markdown cleanup.
    s = s.replaceAll(RegExp(r'\*\*(.*?)\*\*'), r'$1');
    s = s.replaceAll(RegExp(r'__(.*?)__'), r'$1');
    s = s.replaceAll(RegExp(r'`([^`]+)`'), r'$1');

    return s;
  }
}

class _DisplayMathBlock extends StatelessWidget {
  final String latex;
  final TextStyle style;

  const _DisplayMathBlock({
    required this.latex,
    required this.style,
  });

  @override
  Widget build(BuildContext context) {
    if (latex.trim().isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: LumoraColors.bg.withOpacity(0.65),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: LumoraColors.borderSoft),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Math.tex(
          latex.trim(),
          textStyle: style.copyWith(
            fontSize: (style.fontSize ?? 15) + 5,
            color: style.color ?? LumoraColors.text,
          ),
          mathStyle: MathStyle.display,
          onErrorFallback: (error) => Text(
            latex.trim(),
            style: style.copyWith(fontFamily: 'monospace'),
          ),
        ),
      ),
    );
  }
}

class _MarkdownTable extends StatelessWidget {
  final List<String> lines;
  final TextStyle style;

  const _MarkdownTable({
    required this.lines,
    required this.style,
  });

  @override
  Widget build(BuildContext context) {
    final rows = lines
        .map((line) => line
            .trim()
            .split('|')
            .map((cell) => cell.trim())
            .where((cell) => cell.isNotEmpty)
            .toList())
        .where((row) => row.isNotEmpty)
        .toList();

    if (rows.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: LumoraColors.bg.withOpacity(0.50),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: LumoraColors.borderSoft),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: Table(
          border: TableBorder.symmetric(
            inside: BorderSide(color: LumoraColors.borderSoft.withOpacity(0.55)),
          ),
          defaultVerticalAlignment: TableCellVerticalAlignment.middle,
          children: [
            for (var r = 0; r < rows.length; r++)
              TableRow(
                decoration: BoxDecoration(
                  color: r == 0
                      ? LumoraColors.primary.withOpacity(0.14)
                      : Colors.transparent,
                ),
                children: [
                  for (final cell in rows[r])
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                      child: _InlineLatexText(
                        text: cell,
                        style: style.copyWith(
                          fontWeight: r == 0 ? FontWeight.w700 : FontWeight.w400,
                        ),
                      ),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}


class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const GlassCard({super.key, required this.child, this.padding = const EdgeInsets.all(20)});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: LumoraColors.card,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: LumoraColors.border),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.18), blurRadius: 24, offset: const Offset(0, 12))],
      ),
      child: child,
    );
  }
}

class PageIntroCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const PageIntroCard({super.key, required this.icon, required this.title, required this.description});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(24),
      child: Row(
        children: [
          CircleAvatar(radius: 31, backgroundColor: LumoraColors.primary.withOpacity(0.18), child: Icon(icon, size: 30, color: LumoraColors.primary2)),
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
                const SizedBox(height: 8),
                Text(description, style: const TextStyle(color: LumoraColors.muted, height: 1.45)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class FieldLabel extends StatelessWidget {
  final String text;

  const FieldLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(text, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15));
  }
}

class ResultCard extends StatelessWidget {
  final String title;
  final String? text;
  final String? error;

  const ResultCard({super.key, required this.title, this.text, this.error});

  @override
  Widget build(BuildContext context) {
    if (error != null) return ErrorCard(error!);
    final resultText = text ?? '';
    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          LumoraSmartText(text: resultText),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(onPressed: () => copyToClipboard(context, resultText, 'Result copied'), icon: const Icon(Icons.copy), label: const Text('Copy')),
              OutlinedButton.icon(
                onPressed: () => downloadTextFile('lumora_result_${safeFileTimestamp()}.txt', resultText),
                icon: const Icon(Icons.download),
                label: const Text('Download Text'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class ErrorCard extends StatelessWidget {
  final String message;

  const ErrorCard(this.message, {super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF3B1020),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF7F1D1D)),
      ),
      child: LumoraSmartText(text: message, style: const TextStyle(color: Color(0xFFFFD5D5), height: 1.45)),
    );
  }
}

class EmptyStateCard extends StatelessWidget {
  final String title;
  final String message;

  const EmptyStateCard({super.key, required this.title, required this.message});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          Text(message, style: const TextStyle(color: LumoraColors.muted, height: 1.45)),
        ],
      ),
    );
  }
}

class CopyBox extends StatelessWidget {
  final String text;
  final String? label;
  final bool multiline;

  const CopyBox({super.key, required this.text, this.label, this.multiline = false});

  @override
  Widget build(BuildContext context) {
    final displayText = text.trim().isEmpty ? 'Nothing to copy yet.' : text;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(label!, style: const TextStyle(color: LumoraColors.muted, fontWeight: FontWeight.w800, fontSize: 14)),
          const SizedBox(height: 8),
        ],
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: LumoraColors.bg.withOpacity(0.72),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: LumoraColors.border),
          ),
          child: Row(
            crossAxisAlignment: multiline ? CrossAxisAlignment.start : CrossAxisAlignment.center,
            children: [
              Expanded(
                child: LumoraSmartText(
                  text: displayText,
                  style: TextStyle(fontFamily: multiline ? null : 'monospace', fontSize: 15, height: multiline ? 1.5 : 1.25, color: LumoraColors.text),
                ),
              ),
              const SizedBox(width: 10),
              IconButton(tooltip: 'Copy', onPressed: () => copyToClipboard(context, displayText, 'Copied to clipboard'), icon: const Icon(Icons.copy_rounded)),
            ],
          ),
        ),
      ],
    );
  }
}

class HistoryTextPanel extends StatelessWidget {
  final List<GeneratedTextItem> history;
  final ValueChanged<GeneratedTextItem> onRestore;

  const HistoryTextPanel({super.key, required this.history, required this.onRestore});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Recent Results', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          for (final item in history.take(8))
            HistoryTile(
              leading: const CircleAvatar(backgroundColor: Color(0xFF211A4A), child: Icon(Icons.article, color: LumoraColors.primary2)),
              title: item.createdAt.toLocal().toString().split('.').first,
              subtitle: item.text,
              actions: [
                OutlinedButton.icon(onPressed: () => onRestore(item), icon: const Icon(Icons.visibility), label: const Text('View')),
                OutlinedButton.icon(onPressed: () => copyToClipboard(context, item.text, 'History result copied'), icon: const Icon(Icons.copy), label: const Text('Copy')),
              ],
            ),
        ],
      ),
    );
  }
}

class HistoryTile extends StatelessWidget {
  final Widget leading;
  final String title;
  final String subtitle;
  final List<Widget> actions;

  const HistoryTile({super.key, required this.leading, required this.title, required this.subtitle, required this.actions});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: LumoraColors.bg.withOpacity(0.72),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: LumoraColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          leading,
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: LumoraColors.primary2, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(subtitle, maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: LumoraColors.text, height: 1.35)),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: actions),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

