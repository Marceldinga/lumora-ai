from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_frontend_display_fix.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# 1. Use local fixed backend by default
text = text.replace(
    "defaultValue: 'https://lumora-ai-production.up.railway.app'",
    "defaultValue: 'http://127.0.0.1:8000'"
)

# 2. Use the same /chat endpoint we tested successfully in PowerShell
text = text.replace(
    "const String kChatPath = '/brain-chat';",
    "const String kChatPath = '/chat';"
)

# 3. Add display-normalizer function if it does not already exist
helper = r'''

String normalizeLumoraDisplay(String input) {
  var s = input;

  // Render inline LaTeX as clean readable text inside sentences.
  // Example: \( x = 2 \) becomes x = 2.
  s = s.replaceAllMapped(
    RegExp(r'\\\((.*?)\\\)', dotAll: true),
    (match) => match.group(1)?.trim() ?? '',
  );

  // Remove markdown table separator rows like |---:|---:|.
  s = s.replaceAll(
    RegExp(r'^\s*\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|\s*$', multiLine: true),
    '',
  );

  // Make simple 2-column markdown tables readable in the current UI.
  s = s.replaceAllMapped(
    RegExp(r'^\s*\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|\s*$', multiLine: true),
    (match) {
      final left = (match.group(1) ?? '').trim();
      final right = (match.group(2) ?? '').trim();

      if (left.isEmpty || right.isEmpty) return '';

      final lower = '$left $right'.toLowerCase();
      if (lower.contains('bedrooms') && lower.contains('price')) {
        return 'Bedrooms -> Price';
      }

      return '- $left -> $right';
    },
  );

  // Clean extra blank lines.
  s = s.replaceAll(RegExp(r'\n{3,}'), '\n\n');

  return s.trim();
}

'''

if "String normalizeLumoraDisplay(String input)" not in text:
    marker = "class LumoraApiException implements Exception"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find LumoraApiException marker.")
    text = text[:idx] + helper + text[idx:]
    print("Inserted normalizeLumoraDisplay().")
else:
    print("normalizeLumoraDisplay() already exists.")

# 4. Wrap cleanPlainOutput(...) so replies are normalized before display.
text = re.sub(
    r'return\s+cleanPlainOutput\((.*?)\);',
    r'return normalizeLumoraDisplay(cleanPlainOutput(\1));',
    text,
    flags=re.DOTALL,
)

path.write_text(text, encoding="utf-8")
print("Frontend display/backend patch complete.")
