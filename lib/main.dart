import 'dart:convert';
import 'dart:typed_data';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const String kApiUrl = 'http://127.0.0.1:8000/chat';
const String kImageApiUrl = 'http://127.0.0.1:8000/image';
const String kVideoApiUrl = 'http://127.0.0.1:8000/video';

void main() {
  runApp(const LumoraAIApp());
}

Future<String> callLumoraBackend({
  required String message,
  required String mode,
  List<Map<String, String>> history = const [],
}) async {
  final response = await http
      .post(
        Uri.parse(kApiUrl),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'message': message,
          'mode': mode,
          'history': history,
        }),
      )
      .timeout(const Duration(seconds: 90));

  if (response.statusCode >= 200 && response.statusCode < 300) {
    final data = jsonDecode(response.body);

    if (data is Map<String, dynamic>) {
      return data['reply']?.toString() ?? 'No reply returned from backend.';
    }

    return 'Backend returned an unexpected response.';
  }

  throw Exception('Backend error ${response.statusCode}: ${response.body}');
}


Future<ImageGenerationResult> callLumoraImageBackend({
  required String prompt,
  required String style,
  int width = 1024,
  int height = 1024,
}) async {
  final response = await http
      .post(
        Uri.parse(kImageApiUrl),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'prompt': prompt,
          'style': style,
          'width': width,
          'height': height,
        }),
      )
      .timeout(const Duration(seconds: 180));

  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw Exception('Backend error ${response.statusCode}: ${response.body}');
  }

  final data = jsonDecode(response.body);

  if (data is! Map<String, dynamic>) {
    throw Exception('Image backend returned an unexpected response.');
  }

  if (data['ok'] != true) {
    throw Exception(data['error']?.toString() ?? 'Image generation failed.');
  }

  final imageBase64 = data['image_base64']?.toString();

  if (imageBase64 == null || imageBase64.isEmpty) {
    throw Exception('Image backend did not return image_base64.');
  }

  return ImageGenerationResult(
    imageBytes: base64Decode(imageBase64),
    prompt: data['prompt']?.toString() ?? prompt,
    model: data['model']?.toString() ?? 'Unknown model',
    width: data['width'] is int ? data['width'] as int : width,
    height: data['height'] is int ? data['height'] as int : height,
  );
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


Future<VideoGenerationResult> callLumoraVideoBackend({
  required String prompt,
  required String style,
  int seconds = 4,
}) async {
  final response = await http
      .post(
        Uri.parse(kVideoApiUrl),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'prompt': prompt,
          'style': style,
          'seconds': seconds,
        }),
      )
      .timeout(const Duration(seconds: 360));

  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw Exception('Backend error ${response.statusCode}: ${response.body}');
  }

  final data = jsonDecode(response.body);

  if (data is! Map<String, dynamic>) {
    throw Exception('Video backend returned an unexpected response.');
  }

  if (data['ok'] != true) {
    throw Exception(data['error']?.toString() ?? 'Video generation failed.');
  }

  final videoBase64 = data['video_base64']?.toString();

  if (videoBase64 == null || videoBase64.isEmpty) {
    throw Exception('Video backend did not return video_base64.');
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

class LumoraAIApp extends StatelessWidget {
  const LumoraAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lumora',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF080B14),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF7C5CFF),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
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

  Widget _buildPage() {
    switch (selectedIndex) {
      case 0:
        return DashboardPage(
          onOpen: (index) {
            setState(() {
              selectedIndex = index;
            });
          },
        );

      case 1:
        return const LumoraChatPage();

      case 2:
        return AiToolPage(
          icon: Icons.menu_book,
          title: 'Study Planner',
          description:
              'Create daily or weekly study plans for students at different educational levels.',
          mode: 'study',
          buttonText: 'Generate Study Plan',
          fields: const [
            ToolFieldConfig(
              key: 'student_name',
              label: 'Student name',
              hint: 'Example: Marcel Dinga',
            ),
            ToolFieldConfig(
              key: 'topic',
              label: 'What do you want to study?',
              hint: 'Example: Python for Data Analytics',
            ),
            ToolFieldConfig(
              key: 'goal',
              label: 'What is your goal?',
              hint:
                  'Example: Prepare for an exam, finish a project, learn basics',
            ),
            ToolFieldConfig(
              key: 'days',
              label: 'How many days do you have?',
              hint: 'Example: 7 days',
            ),
            ToolFieldConfig(
              key: 'education_level',
              label: 'Educational level',
              hint:
                  'Example: Elementary, middle school, high school, college, master’s, professional certification, or all levels',
              initialValue: 'All educational levels',
            ),
            ToolFieldConfig(
              key: 'skill_level',
              label: 'Skill level',
              hint: 'Example: Beginner, intermediate, advanced, or all levels',
              initialValue: 'All skill levels',
            ),
            ToolFieldConfig(
              key: 'time',
              label: 'Daily study time',
              hint: 'Example: 1 hour per day',
            ),
          ],
          promptBuilder: (values) {
            return '''
Create a complete personalized study plan.

Student name: ${values['student_name']}
Topic: ${values['topic']}
Goal: ${values['goal']}
Number of days: ${values['days']}
Educational level: ${values['education_level']}
Skill level: ${values['skill_level']}
Daily study time: ${values['time']}

Important rules:
1. Start with the student name.
2. If educational level is "All educational levels", create sections for:
   - Elementary / Basic Level
   - Middle School Level
   - High School Level
   - College / University Level
   - Graduate / Master’s Level
   - Professional / Certification Level
3. If skill level is "All skill levels", include beginner, intermediate, and advanced progression.
4. For each section, include:
   - Daily topics
   - Practice activities
   - Review tasks
   - Mini project or final review
5. Make the plan practical and easy to follow.
6. Do not add unnecessary introduction.
7. Use clean plain text only.
8. Do not use Markdown bold symbols like **.

Make it useful for the selected student and educational level.
''';
          },
        );

      case 3:
        return AiToolPage(
          icon: Icons.article,
          title: 'Research Assistant',
          description:
              'Summarize topics, create outlines, organize ideas, and build research drafts.',
          mode: 'research',
          buttonText: 'Generate Research Help',
          fields: const [
            ToolFieldConfig(
              key: 'student_name',
              label: 'Student name',
              hint: 'Example: Marcel Dinga',
            ),
            ToolFieldConfig(
              key: 'education_level',
              label: 'Educational level',
              hint:
                  'Example: High school, college, master’s, doctoral, professional, or all levels',
              initialValue: 'College / University Level',
            ),
            ToolFieldConfig(
              key: 'topic',
              label: 'Research topic',
              hint: 'Example: The role of machine learning in healthcare',
            ),
            ToolFieldConfig(
              key: 'purpose',
              label: 'Purpose',
              hint: 'Example: Academic paper, class assignment, proposal',
            ),
            ToolFieldConfig(
              key: 'requirements',
              label: 'Requirements',
              hint:
                  'Example: APA style, 5 paragraphs, include introduction and conclusion',
              maxLines: 3,
            ),
            ToolFieldConfig(
              key: 'notes',
              label: 'Paste notes or ideas',
              hint: 'Paste your notes here. You can leave this blank.',
              maxLines: 5,
            ),
          ],
          promptBuilder: (values) {
            return '''
Act as a research assistant.

Student name: ${values['student_name']}
Educational level: ${values['education_level']}
Research topic: ${values['topic']}
Purpose: ${values['purpose']}
Requirements: ${values['requirements']}
My notes: ${values['notes']}

Please provide:
1. A clear research summary
2. A strong thesis statement
3. A structured outline
4. Key points to discuss
5. Possible research questions
6. A short draft introduction

Important rules:
1. Match the writing to the selected educational level.
2. Use academic but simple language.
3. Do not add unnecessary introduction.
4. Use clean plain text only.
5. Do not use Markdown bold symbols like **.
''';
          },
        );

      case 4:
        return AiToolPage(
          icon: Icons.quiz,
          title: 'Quiz Generator',
          description:
              'Generate practice questions by student name, educational level, difficulty, topic, or notes.',
          mode: 'study',
          buttonText: 'Generate Quiz',
          fields: const [
            ToolFieldConfig(
              key: 'student_name',
              label: 'Student name',
              hint: 'Example: Marcel Dinga',
            ),
            ToolFieldConfig(
              key: 'topic',
              label: 'Quiz topic',
              hint: 'Example: Linear regression',
            ),
            ToolFieldConfig(
              key: 'count',
              label: 'Number of questions',
              hint: 'Example: 15',
            ),
            ToolFieldConfig(
              key: 'education_level',
              label: 'Educational level',
              hint:
                  'Example: Elementary, middle school, high school, college, master’s, professional certification, or all levels',
              initialValue: 'All educational levels',
            ),
            ToolFieldConfig(
              key: 'difficulty',
              label: 'Difficulty level',
              hint: 'Example: Beginner, intermediate, advanced, or all levels',
              initialValue: 'All difficulty levels',
            ),
            ToolFieldConfig(
              key: 'type',
              label: 'Question type',
              hint: 'Example: Multiple choice, short answer, mixed',
            ),
            ToolFieldConfig(
              key: 'notes',
              label: 'Paste notes',
              hint: 'Paste notes here if you want the quiz based on your notes.',
              maxLines: 5,
            ),
          ],
          promptBuilder: (values) {
            return '''
Create a personalized quiz.

Student name: ${values['student_name']}
Topic: ${values['topic']}
Number of questions: ${values['count']}
Educational level: ${values['education_level']}
Difficulty level: ${values['difficulty']}
Question type: ${values['type']}
Notes to use: ${values['notes']}

Important rules:
1. Start with the student name.
2. If educational level is "All educational levels", divide the quiz into:
   - Elementary / Basic Level
   - Middle School Level
   - High School Level
   - College / University Level
   - Graduate / Master’s Level
   - Professional / Certification Level
3. If difficulty level is "All difficulty levels", include:
   - Beginner questions
   - Intermediate questions
   - Advanced questions
4. Include numbered questions.
5. Include answer choices if multiple choice.
6. Include the correct answer.
7. Include a short explanation for each answer.
8. Do not add unnecessary introduction.
9. Use clean plain text only.
10. Do not use Markdown bold symbols like **.

Make the quiz useful for the selected student and educational level.
''';
          },
        );

      case 5:
        return AiToolPage(
          icon: Icons.style,
          title: 'Flashcards',
          description:
              'Turn notes, topics, or definitions into personalized question-and-answer flashcards.',
          mode: 'study',
          buttonText: 'Generate Flashcards',
          fields: const [
            ToolFieldConfig(
              key: 'student_name',
              label: 'Student name',
              hint: 'Example: Marcel Dinga',
            ),
            ToolFieldConfig(
              key: 'topic',
              label: 'Flashcard topic',
              hint: 'Example: SQL joins',
            ),
            ToolFieldConfig(
              key: 'count',
              label: 'Number of flashcards',
              hint: 'Example: 15',
            ),
            ToolFieldConfig(
              key: 'education_level',
              label: 'Educational level',
              hint:
                  'Example: Elementary, middle school, high school, college, master’s, professional certification, or all levels',
              initialValue: 'All educational levels',
            ),
            ToolFieldConfig(
              key: 'difficulty',
              label: 'Difficulty level',
              hint: 'Example: Beginner, intermediate, advanced, or all levels',
              initialValue: 'All difficulty levels',
            ),
            ToolFieldConfig(
              key: 'notes',
              label: 'Paste notes',
              hint: 'Paste notes or study material here.',
              maxLines: 7,
            ),
          ],
          promptBuilder: (values) {
            return '''
Create personalized flashcards.

Student name: ${values['student_name']}
Topic: ${values['topic']}
Number of flashcards: ${values['count']}
Educational level: ${values['education_level']}
Difficulty level: ${values['difficulty']}
Notes: ${values['notes']}

Important rules:
1. Return exactly the number of flashcards requested.
2. Start with the student name.
3. Match the flashcards to the selected educational level.
4. If educational level is "All educational levels", include flashcards suitable for multiple educational levels.
5. If difficulty level is "All difficulty levels", include beginner, intermediate, and advanced flashcards.
6. Do not add introduction.
7. Do not add closing comments.
8. Do not say “let’s add more.”
9. Do not use Markdown bold symbols like **.
10. Use clean plain text only.

Use this exact format:

Student: ${values['student_name']}

Flashcard 1
Q: question here
A: answer here

Flashcard 2
Q: question here
A: answer here
''';
          },
        );

      case 6:
        return const ImageGeneratorPage();

      case 7:
        return const VideoGeneratorPage();

      default:
        return const LumoraChatPage();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: selectedIndex,
            backgroundColor: const Color(0xFF101827),
            indicatorColor: const Color(0xFF7C5CFF),
            labelType: NavigationRailLabelType.all,
            onDestinationSelected: (index) {
              setState(() {
                selectedIndex = index;
              });
            },
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.dashboard_outlined),
                selectedIcon: Icon(Icons.dashboard),
                label: Text('Home'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.auto_awesome_outlined),
                selectedIcon: Icon(Icons.auto_awesome),
                label: Text('Chat'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.menu_book_outlined),
                selectedIcon: Icon(Icons.menu_book),
                label: Text('Study'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.article_outlined),
                selectedIcon: Icon(Icons.article),
                label: Text('Research'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.quiz_outlined),
                selectedIcon: Icon(Icons.quiz),
                label: Text('Quiz'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.style_outlined),
                selectedIcon: Icon(Icons.style),
                label: Text('Cards'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.image_outlined),
                selectedIcon: Icon(Icons.image),
                label: Text('Image'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.movie_creation_outlined),
                selectedIcon: Icon(Icons.movie_creation),
                label: Text('Video'),
              ),
            ],
          ),
          Expanded(
            child: Column(
              children: [
                Container(
                  height: 74,
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  decoration: const BoxDecoration(
                    color: Color(0xFF101827),
                    border: Border(
                      bottom: BorderSide(color: Color(0xFF253044)),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        height: 42,
                        width: 42,
                        decoration: BoxDecoration(
                          color: const Color(0xFF211A4A),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(
                          Icons.lightbulb,
                          color: Color(0xFFBBA7FF),
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text(
                        'Lumora',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Spacer(),
                      const Chip(
                        label: Text('Research • Study • Image • Video Assistant'),
                      ),
                    ],
                  ),
                ),
                Expanded(child: _buildPage()),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class DashboardPage extends StatelessWidget {
  final void Function(int index) onOpen;

  const DashboardPage({
    super.key,
    required this.onOpen,
  });

  @override
  Widget build(BuildContext context) {
    final cards = [
      DashboardCardData(
        index: 1,
        icon: Icons.auto_awesome,
        title: 'AI Chat',
        text:
            'Ask Lumora to explain topics, summarize notes, or help with data and research.',
      ),
      DashboardCardData(
        index: 2,
        icon: Icons.menu_book,
        title: 'Study Planner',
        text:
            'Build personalized study plans by student name and educational level.',
      ),
      DashboardCardData(
        index: 3,
        icon: Icons.article,
        title: 'Research Helper',
        text:
            'Generate research summaries, thesis statements, outlines, and introductions.',
      ),
      DashboardCardData(
        index: 4,
        icon: Icons.quiz,
        title: 'Quiz Generator',
        text:
            'Create personalized quizzes with answers and explanations from any topic.',
      ),
      DashboardCardData(
        index: 5,
        icon: Icons.style,
        title: 'Flashcards',
        text:
            'Turn notes into personalized flashcards for fast review and memorization.',
      ),
      DashboardCardData(
        index: 6,
        icon: Icons.image,
        title: 'Image Generator',
        text:
            'Generate educational images from text prompts using Lumora.',
      ),
      DashboardCardData(
        index: 7,
        icon: Icons.movie_creation,
        title: 'Video Generator',
        text:
            'Generate short educational videos from text prompts using Lumora.',
      ),
    ];

    return Padding(
      padding: const EdgeInsets.all(24),
      child: LayoutBuilder(
        builder: (context, constraints) {
          int columns = 3;

          if (constraints.maxWidth < 750) {
            columns = 1;
          } else if (constraints.maxWidth < 1150) {
            columns = 2;
          }

          return GridView.count(
            crossAxisCount: columns,
            crossAxisSpacing: 18,
            mainAxisSpacing: 18,
            childAspectRatio: 1.55,
            children: cards
                .map(
                  (card) => DashboardCard(
                    icon: card.icon,
                    title: card.title,
                    text: card.text,
                    onTap: () => onOpen(card.index),
                  ),
                )
                .toList(),
          );
        },
      ),
    );
  }
}

class DashboardCardData {
  final int index;
  final IconData icon;
  final String title;
  final String text;

  DashboardCardData({
    required this.index,
    required this.icon,
    required this.title,
    required this.text,
  });
}

class DashboardCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  final VoidCallback onTap;

  const DashboardCard({
    super.key,
    required this.icon,
    required this.title,
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: const Color(0xFF101827),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: const Color(0xFF253044)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              backgroundColor: const Color(0xFF211A4A),
              child: Icon(icon, color: const Color(0xFFBBA7FF)),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Text(
                text,
                style: const TextStyle(
                  color: Color(0xFFCBD5E1),
                  height: 1.4,
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Open →',
              style: TextStyle(
                color: Color(0xFFBBA7FF),
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

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
      text:
          'Hello, I’m Lumora — your research and study assistant. I can help you explain topics, summarize notes, create quizzes, build study plans, write research drafts, generate image prompts, and understand data.',
    ),
  ];

  bool loading = false;
  String selectedMode = 'study';

  Future<void> sendMessage() async {
    final text = controller.text.trim();

    if (text.isEmpty || loading) return;

    setState(() {
      messages.add(ChatMessage(role: 'user', text: text));
      controller.clear();
      loading = true;
    });

    _scrollToBottom();

    try {
      final reply = await callBackend(text);

      setState(() {
        messages.add(ChatMessage(role: 'assistant', text: reply));
      });
    } catch (e) {
      setState(() {
        messages.add(
          ChatMessage(
            role: 'assistant',
            text:
                'Lumora could not connect to the local backend. Make sure FastAPI is running at http://127.0.0.1:8000. Error: $e',
          ),
        );
      });
    } finally {
      setState(() {
        loading = false;
      });
      _scrollToBottom();
    }
  }

  Future<String> callBackend(String message) async {
    final historyItems = messages.length > 1
        ? messages.sublist(0, messages.length - 1)
        : <ChatMessage>[];

    return callLumoraBackend(
      message: message,
      mode: selectedMode,
      history: historyItems
          .map(
            (m) => {
              'role': m.role,
              'content': m.text,
            },
          )
          .toList(),
    );
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 150), () {
      if (!scrollController.hasClients) return;

      scrollController.animateTo(
        scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
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
        Container(
          padding: const EdgeInsets.all(16),
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            border: Border(
              bottom: BorderSide(color: Color(0xFF253044)),
            ),
          ),
          child: Row(
            children: [
              const Text(
                'Mode:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 12),
              DropdownButton<String>(
                value: selectedMode,
                dropdownColor: const Color(0xFF101827),
                items: const [
                  DropdownMenuItem(value: 'study', child: Text('Study')),
                  DropdownMenuItem(value: 'research', child: Text('Research')),
                  DropdownMenuItem(value: 'writing', child: Text('Writing')),
                  DropdownMenuItem(value: 'data', child: Text('Data')),
                  DropdownMenuItem(value: 'image', child: Text('Image Prompt')),
                  DropdownMenuItem(value: 'video', child: Text('Video Prompt')),
                ],
                onChanged: (value) {
                  if (value == null) return;

                  setState(() {
                    selectedMode = value;
                  });
                },
              ),
              const Spacer(),
              const Chip(
                label: Text('Local backend selected'),
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.builder(
            controller: scrollController,
            padding: const EdgeInsets.all(20),
            itemCount: messages.length + (loading ? 1 : 0),
            itemBuilder: (context, index) {
              if (loading && index == messages.length) {
                return const ChatBubble(
                  role: 'assistant',
                  text: 'Thinking...',
                );
              }

              final msg = messages[index];
              return ChatBubble(role: msg.role, text: msg.text);
            },
          ),
        ),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: const BoxDecoration(
            color: Color(0xFF101827),
            border: Border(
              top: BorderSide(color: Color(0xFF253044)),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: controller,
                  minLines: 1,
                  maxLines: 4,
                  onSubmitted: (_) => sendMessage(),
                  decoration: InputDecoration(
                    hintText:
                        'Ask Lumora... example: Search internet for latest AI news today',
                    filled: true,
                    fillColor: const Color(0xFF080B14),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(18),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: loading ? null : sendMessage,
                icon: const Icon(Icons.send),
                label: const Text('Send'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}


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
      final imageResult = await callLumoraImageBackend(
        prompt: prompt,
        style: style.isEmpty ? 'professional realistic' : style,
        width: 1024,
        height: 1024,
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

Important:
- Use clean plain text only.
- Do not use markdown bold symbols.
- Do not invent details that are not related to the image topic.
- Keep it clear for students.
''';

      final textResult = await callLumoraBackend(
        message: explanationPrompt,
        mode: 'study',
      );

      final historyItem = ImageHistoryItem(
        image: imageResult,
        explanation: textResult,
        createdAt: DateTime.now(),
      );

      setState(() {
        result = imageResult;
        generatedText = textResult;
        imageHistory.insert(0, historyItem);
      });
    } catch (e) {
      setState(() {
        error =
            'Lumora could not generate the image or explanation. Make sure your FastAPI backend is running and the /image and /chat endpoints work. Error: $e';
      });
    } finally {
      setState(() {
        loading = false;
      });
    }
  }

  void downloadGeneratedImage([ImageGenerationResult? image]) {
    final imageToDownload = image ?? result;

    if (imageToDownload == null) return;

    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final blob = html.Blob([imageToDownload.imageBytes], 'image/png');
    final url = html.Url.createObjectUrlFromBlob(blob);

    html.AnchorElement(href: url)
      ..setAttribute('download', 'lumora_generated_image_$timestamp.png')
      ..click();

    html.Url.revokeObjectUrl(url);
  }

  Future<void> copyText(String text, String message) async {
    if (text.trim().isEmpty) return;

    await Clipboard.setData(ClipboardData(text: text));

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
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

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      filled: true,
      fillColor: const Color(0xFF080B14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF253044)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF7C5CFF)),
      ),
    );
  }

  Widget _buildActionButtons() {
    final promptText = result?.prompt ?? promptController.text.trim();
    final explanationText = generatedText ?? '';

    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        FilledButton.icon(
          onPressed: result == null ? null : () => downloadGeneratedImage(),
          icon: const Icon(Icons.download),
          label: const Text('Download Image'),
        ),
        OutlinedButton.icon(
          onPressed: promptText.trim().isEmpty
              ? null
              : () => copyText(promptText, 'Prompt copied'),
          icon: const Icon(Icons.copy),
          label: const Text('Copy Prompt'),
        ),
        OutlinedButton.icon(
          onPressed: explanationText.trim().isEmpty
              ? null
              : () => copyText(explanationText, 'Explanation copied'),
          icon: const Icon(Icons.copy_all),
          label: const Text('Copy Text'),
        ),
      ],
    );
  }

  Widget _buildImageResult() {
    if (error != null) {
      return Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFF3B1020),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFF7F1D1D)),
        ),
        child: Text(
          error!,
          style: const TextStyle(height: 1.45),
        ),
      );
    }

    if (result == null) {
      return Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: const Color(0xFF101827),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: const Color(0xFF253044)),
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Generated Image',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 14),
            Text(
              'Your generated image, clean text labels, copy buttons, download button, and history will appear here.',
              style: TextStyle(
                color: Color(0xFFCBD5E1),
                height: 1.45,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF253044)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Generated Image',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Image.memory(
              result!.imageBytes,
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(height: 16),
          _buildActionButtons(),
          const SizedBox(height: 16),
          Text(
            'Model: ${result!.model}',
            style: const TextStyle(color: Color(0xFFCBD5E1)),
          ),
          const SizedBox(height: 6),
          Text(
            'Size: ${result!.width} x ${result!.height}',
            style: const TextStyle(color: Color(0xFFCBD5E1)),
          ),
          const SizedBox(height: 16),
          CopyBox(
            label: 'Prompt',
            text: result!.prompt,
          ),
          const SizedBox(height: 18),
          CopyBox(
            label: 'Clean Text Labels',
            text: generatedText ?? 'Generating explanation...',
            multiline: true,
          ),
        ],
      ),
    );
  }

  Widget _buildHistorySection() {
    if (imageHistory.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF253044)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Image History',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'History is stored while the app is open. Use Download Image to save images permanently.',
            style: TextStyle(
              color: Color(0xFFCBD5E1),
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          for (final item in imageHistory) ...[
            Container(
              padding: const EdgeInsets.all(14),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF080B14),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFF253044)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.memory(
                      item.image.imageBytes,
                      width: 90,
                      height: 90,
                      fit: BoxFit.cover,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.createdAt.toLocal().toString().split('.').first,
                          style: const TextStyle(
                            color: Color(0xFFBBA7FF),
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          item.image.prompt,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Color(0xFFE5E7EB),
                            height: 1.35,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            OutlinedButton.icon(
                              onPressed: () => restoreHistoryItem(item),
                              icon: const Icon(Icons.visibility),
                              label: const Text('View'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () =>
                                  downloadGeneratedImage(item.image),
                              icon: const Icon(Icons.download),
                              label: const Text('Download'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => copyText(
                                item.explanation,
                                'History text copied',
                              ),
                              icon: const Icon(Icons.copy_all),
                              label: const Text('Copy Text'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1150),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF101827),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFF253044)),
                ),
                child: const Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundColor: Color(0xFF211A4A),
                      child: Icon(
                        Icons.image,
                        size: 30,
                        color: Color(0xFFBBA7FF),
                      ),
                    ),
                    SizedBox(width: 18),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Image Generator',
                            style: TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Generate images, clean text labels, copy results, download images, and keep history while the app is open.',
                            style: TextStyle(
                              color: Color(0xFFCBD5E1),
                              height: 1.45,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth >= 950;

                  final form = Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: const Color(0xFF101827),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: const Color(0xFF253044)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Image prompt',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: promptController,
                          maxLines: 5,
                          decoration: _inputDecoration(
                            'Example: A clean educational diagram of an atom with no text labels inside the image',
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Style',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: styleController,
                          maxLines: 2,
                          decoration: _inputDecoration(
                            'Example: educational science diagram, no text, no labels, sharp and large',
                          ),
                        ),
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: loading ? null : generateImage,
                          icon: loading
                              ? const SizedBox(
                                  height: 18,
                                  width: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.image),
                          label: Text(
                            loading
                                ? 'Generating Image and Text...'
                                : 'Generate Image + Text',
                          ),
                        ),
                      ],
                    ),
                  );

                  final imageBox = _buildImageResult();

                  if (!isWide) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        form,
                        const SizedBox(height: 20),
                        imageBox,
                      ],
                    );
                  }

                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: form),
                      const SizedBox(width: 20),
                      Expanded(child: imageBox),
                    ],
                  );
                },
              ),
              const SizedBox(height: 20),
              _buildHistorySection(),
            ],
          ),
        ),
      ),
    );
  }
}




class VideoGeneratorPage extends StatefulWidget {
  const VideoGeneratorPage({super.key});

  @override
  State<VideoGeneratorPage> createState() => _VideoGeneratorPageState();
}

class _VideoGeneratorPageState extends State<VideoGeneratorPage> {
  final TextEditingController promptController = TextEditingController(
    text:
        'A short educational animation showing an atom with electrons smoothly orbiting around a glowing nucleus. No readable text inside the video.',
  );

  final TextEditingController styleController = TextEditingController(
    text:
        'educational science animation, clean 3D style, smooth motion, no text, no labels',
  );

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
      final videoResult = await callLumoraVideoBackend(
        prompt: prompt,
        style: style.isEmpty ? 'professional educational video' : style,
        seconds: 4,
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
5. 3 study questions

Important:
- Use clean plain text only.
- Do not use markdown bold symbols.
- Do not invent details unrelated to the video topic.
- Keep it clear for students.
''';

      final textResult = await callLumoraBackend(
        message: explanationPrompt,
        mode: 'study',
      );

      final historyItem = VideoHistoryItem(
        video: videoResult,
        explanation: textResult,
        createdAt: DateTime.now(),
      );

      setState(() {
        result = videoResult;
        generatedText = textResult;
        videoHistory.insert(0, historyItem);
      });
    } catch (e) {
      setState(() {
        error =
            'Lumora could not generate the video or explanation. Video generation can take longer and may require Hugging Face provider access. Error: $e';
      });
    } finally {
      setState(() {
        loading = false;
      });
    }
  }

  void _prepareVideoPreview(VideoGenerationResult video) {
    if (videoUrl != null) {
      html.Url.revokeObjectUrl(videoUrl!);
    }

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

    ui_web.platformViewRegistry.registerViewFactory(
      viewType,
      (int viewId) => videoElement,
    );

    videoUrl = url;
    videoViewType = viewType;
  }

  void downloadGeneratedVideo([VideoGenerationResult? video]) {
    final videoToDownload = video ?? result;

    if (videoToDownload == null) return;

    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final blob = html.Blob([videoToDownload.videoBytes], videoToDownload.mimeType);
    final url = html.Url.createObjectUrlFromBlob(blob);

    html.AnchorElement(href: url)
      ..setAttribute('download', 'lumora_generated_video_$timestamp.mp4')
      ..click();

    html.Url.revokeObjectUrl(url);
  }

  Future<void> copyText(String text, String message) async {
    if (text.trim().isEmpty) return;

    await Clipboard.setData(ClipboardData(text: text));

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void restoreHistoryItem(VideoHistoryItem item) {
    setState(() {
      result = item.video;
      generatedText = item.explanation;
      promptController.text = item.video.prompt;
      _prepareVideoPreview(item.video);
    });
  }

  @override
  void dispose() {
    if (videoUrl != null) {
      html.Url.revokeObjectUrl(videoUrl!);
    }
    promptController.dispose();
    styleController.dispose();
    super.dispose();
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      filled: true,
      fillColor: const Color(0xFF080B14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF253044)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF7C5CFF)),
      ),
    );
  }

  Widget _buildActionButtons() {
    final promptText = result?.prompt ?? promptController.text.trim();
    final explanationText = generatedText ?? '';

    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        FilledButton.icon(
          onPressed: result == null ? null : () => downloadGeneratedVideo(),
          icon: const Icon(Icons.download),
          label: const Text('Download Video'),
        ),
        OutlinedButton.icon(
          onPressed: promptText.trim().isEmpty
              ? null
              : () => copyText(promptText, 'Video prompt copied'),
          icon: const Icon(Icons.copy),
          label: const Text('Copy Prompt'),
        ),
        OutlinedButton.icon(
          onPressed: explanationText.trim().isEmpty
              ? null
              : () => copyText(explanationText, 'Video text copied'),
          icon: const Icon(Icons.copy_all),
          label: const Text('Copy Text'),
        ),
      ],
    );
  }

  Widget _buildVideoResult() {
    if (error != null) {
      return Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFF3B1020),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFF7F1D1D)),
        ),
        child: Text(
          error!,
          style: const TextStyle(height: 1.45),
        ),
      );
    }

    if (result == null || videoViewType == null) {
      return Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: const Color(0xFF101827),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: const Color(0xFF253044)),
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Generated Video',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 14),
            Text(
              'Your generated video, clean text explanation, copy buttons, download button, and history will appear here. Video generation can take longer than image generation.',
              style: TextStyle(
                color: Color(0xFFCBD5E1),
                height: 1.45,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF253044)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Generated Video',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(
            height: 360,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: HtmlElementView(viewType: videoViewType!),
            ),
          ),
          const SizedBox(height: 16),
          _buildActionButtons(),
          const SizedBox(height: 16),
          Text(
            'Model: ${result!.model}',
            style: const TextStyle(color: Color(0xFFCBD5E1)),
          ),
          const SizedBox(height: 6),
          Text(
            'Provider: ${result!.provider}',
            style: const TextStyle(color: Color(0xFFCBD5E1)),
          ),
          const SizedBox(height: 6),
          Text(
            'Duration: about ${result!.seconds} seconds',
            style: const TextStyle(color: Color(0xFFCBD5E1)),
          ),
          const SizedBox(height: 16),
          CopyBox(
            label: 'Prompt',
            text: result!.prompt,
          ),
          const SizedBox(height: 18),
          CopyBox(
            label: 'Clean Video Notes',
            text: generatedText ?? 'Generating explanation...',
            multiline: true,
          ),
        ],
      ),
    );
  }

  Widget _buildHistorySection() {
    if (videoHistory.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF253044)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Video History',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'History is stored while the app is open. Use Download Video to save videos permanently.',
            style: TextStyle(
              color: Color(0xFFCBD5E1),
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          for (final item in videoHistory) ...[
            Container(
              padding: const EdgeInsets.all(14),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF080B14),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFF253044)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(
                    radius: 32,
                    backgroundColor: Color(0xFF211A4A),
                    child: Icon(
                      Icons.movie_creation,
                      color: Color(0xFFBBA7FF),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.createdAt.toLocal().toString().split('.').first,
                          style: const TextStyle(
                            color: Color(0xFFBBA7FF),
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          item.video.prompt,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Color(0xFFE5E7EB),
                            height: 1.35,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            OutlinedButton.icon(
                              onPressed: () => restoreHistoryItem(item),
                              icon: const Icon(Icons.visibility),
                              label: const Text('View'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () =>
                                  downloadGeneratedVideo(item.video),
                              icon: const Icon(Icons.download),
                              label: const Text('Download'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => copyText(
                                item.explanation,
                                'History video text copied',
                              ),
                              icon: const Icon(Icons.copy_all),
                              label: const Text('Copy Text'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1150),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF101827),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFF253044)),
                ),
                child: const Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundColor: Color(0xFF211A4A),
                      child: Icon(
                        Icons.movie_creation,
                        size: 30,
                        color: Color(0xFFBBA7FF),
                      ),
                    ),
                    SizedBox(width: 18),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Video Generator',
                            style: TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Generate short videos, clean notes, copy results, download videos, and keep history while the app is open.',
                            style: TextStyle(
                              color: Color(0xFFCBD5E1),
                              height: 1.45,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth >= 950;

                  final form = Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: const Color(0xFF101827),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: const Color(0xFF253044)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Video prompt',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: promptController,
                          maxLines: 5,
                          decoration: _inputDecoration(
                            'Example: A short educational animation showing an atom with electrons orbiting a nucleus.',
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Style',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: styleController,
                          maxLines: 2,
                          decoration: _inputDecoration(
                            'Example: educational science animation, clean 3D style, smooth motion',
                          ),
                        ),
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: loading ? null : generateVideo,
                          icon: loading
                              ? const SizedBox(
                                  height: 18,
                                  width: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.movie_creation),
                          label: Text(
                            loading ? 'Generating Video...' : 'Generate Video',
                          ),
                        ),
                      ],
                    ),
                  );

                  final videoBox = _buildVideoResult();

                  if (!isWide) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        form,
                        const SizedBox(height: 20),
                        videoBox,
                      ],
                    );
                  }

                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: form),
                      const SizedBox(width: 20),
                      Expanded(child: videoBox),
                    ],
                  );
                },
              ),
              const SizedBox(height: 20),
              _buildHistorySection(),
            ],
          ),
        ),
      ),
    );
  }
}


class CopyBox extends StatelessWidget {
  final String text;
  final String? label;
  final bool multiline;

  const CopyBox({
    super.key,
    required this.text,
    this.label,
    this.multiline = false,
  });

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: text));

    if (!context.mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied to clipboard'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final displayText = text.trim().isEmpty ? 'Nothing to copy yet.' : text;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(
            label!,
            style: const TextStyle(
              color: Color(0xFFCBD5E1),
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
        ],
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          decoration: BoxDecoration(
            color: const Color(0xFF080B14),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: const Color(0xFF2B3448)),
          ),
          child: Row(
            crossAxisAlignment:
                multiline ? CrossAxisAlignment.start : CrossAxisAlignment.center,
            children: [
              Expanded(
                child: SelectableText(
                  displayText,
                  style: TextStyle(
                    fontFamily: multiline ? null : 'monospace',
                    fontSize: 15,
                    height: multiline ? 1.5 : 1.25,
                    color: const Color(0xFFE5E7EB),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              IconButton(
                tooltip: 'Copy',
                onPressed: () => _copy(context),
                icon: const Icon(Icons.copy_rounded),
                color: const Color(0xFFE5E7EB),
              ),
            ],
          ),
        ),
      ],
    );
  }
}


class ChatBubble extends StatelessWidget {
  final String role;
  final String text;

  const ChatBubble({
    super.key,
    required this.role,
    required this.text,
  });

  Future<void> _copyMessage(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: text));

    if (!context.mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Message copied'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isUser = role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 780),
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF4F46E5) : const Color(0xFF101827),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: isUser ? const Color(0xFF6D5DFB) : const Color(0xFF253044),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SelectableText(
              text,
              style: const TextStyle(height: 1.45, fontSize: 15),
            ),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => _copyMessage(context),
                icon: const Icon(Icons.copy_rounded, size: 18),
                label: const Text('Copy'),
                style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFFBBA7FF),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ChatMessage {
  final String role;
  final String text;

  ChatMessage({
    required this.role,
    required this.text,
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

  @override
  State<AiToolPage> createState() => _AiToolPageState();
}

class _AiToolPageState extends State<AiToolPage> {
  late final Map<String, TextEditingController> controllers;

  bool loading = false;
  String? result;
  String? error;

  @override
  void initState() {
    super.initState();

    controllers = {
      for (final field in widget.fields)
        field.key: TextEditingController(text: field.initialValue),
    };
  }

  @override
  void dispose() {
    for (final controller in controllers.values) {
      controller.dispose();
    }

    super.dispose();
  }

  Future<void> generate() async {
    final values = {
      for (final entry in controllers.entries) entry.key: entry.value.text.trim()
    };

    final prompt = widget.promptBuilder(values).trim();

    if (prompt.isEmpty || loading) return;

    setState(() {
      loading = true;
      result = null;
      error = null;
    });

    try {
      final reply = await callLumoraBackend(
        message: prompt,
        mode: widget.mode,
      );

      setState(() {
        result = reply;
      });
    } catch (e) {
      setState(() {
        error =
            'Lumora could not generate the result. Make sure your FastAPI backend is running at http://127.0.0.1:8000. Error: $e';
      });
    } finally {
      setState(() {
        loading = false;
      });
    }
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      filled: true,
      fillColor: const Color(0xFF080B14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF253044)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF7C5CFF)),
      ),
    );
  }

  Widget _buildResultBox() {
    if (error != null) {
      return Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFF3B1020),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFF7F1D1D)),
        ),
        child: Text(
          error!,
          style: const TextStyle(height: 1.45),
        ),
      );
    }

    if (result == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF253044)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Lumora Result',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 14),
          SelectableText(
            result!,
            style: const TextStyle(
              height: 1.55,
              fontSize: 15,
              color: Color(0xFFE5E7EB),
            ),
          ),
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: result!));

                if (!context.mounted) return;

                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Result copied'),
                    duration: Duration(seconds: 2),
                  ),
                );
              },
              icon: const Icon(Icons.copy_rounded, size: 18),
              label: const Text('Copy'),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFFBBA7FF),
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 980),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF101827),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFF253044)),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundColor: const Color(0xFF211A4A),
                      child: Icon(
                        widget.icon,
                        size: 30,
                        color: const Color(0xFFBBA7FF),
                      ),
                    ),
                    const SizedBox(width: 18),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.title,
                            style: const TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            widget.description,
                            style: const TextStyle(
                              color: Color(0xFFCBD5E1),
                              height: 1.45,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF101827),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFF253044)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final field in widget.fields) ...[
                      Text(
                        field.label,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: controllers[field.key],
                        maxLines: field.maxLines,
                        decoration: _inputDecoration(field.hint),
                      ),
                      const SizedBox(height: 16),
                    ],
                    const SizedBox(height: 4),
                    FilledButton.icon(
                      onPressed: loading ? null : generate,
                      icon: loading
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.auto_awesome),
                      label: Text(loading ? 'Generating...' : widget.buttonText),
                    ),
                  ],
                ),
              ),
              if (error != null || result != null) ...[
                const SizedBox(height: 20),
                _buildResultBox(),
              ],
            ],
          ),
        ),
      ),
    );
  }
}