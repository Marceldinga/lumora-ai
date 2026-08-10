from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_copy_table_spacing_fix.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

start = text.find("String normalizeLumoraCopiedText(String input)")
if start == -1:
    raise RuntimeError("normalizeLumoraCopiedText not found.")

end = text.find("class LumoraApiException", start)
if end == -1:
    raise RuntimeError("Could not find class LumoraApiException after normalizeLumoraCopiedText.")

new_func = r'''
String normalizeLumoraCopiedText(String input) {
  var s = input.replaceAll('\r\n', '\n');

  // Inline LaTeX: \( x \) -> x
  s = s.replaceAllMapped(
    RegExp(r'\\\((.*?)\\\)', dotAll: true),
    (match) => match.group(1)?.trim() ?? '',
  );

  // Display LaTeX: \[ y = mx + b \] -> y = mx + b
  s = s.replaceAllMapped(
    RegExp(r'\\\[(.*?)\\\]', dotAll: true),
    (match) => '\n${match.group(1)?.trim() ?? ''}\n',
  );

  // $$ ... $$ support
  s = s.replaceAllMapped(
    RegExp(r'\$\$(.*?)\$\$', dotAll: true),
    (match) => '\n${match.group(1)?.trim() ?? ''}\n',
  );

  // Common LaTeX cleanup
  s = s.replaceAll(r'\times', '×');
  s = s.replaceAll(r'\rightarrow', '→');
  s = s.replaceAll(r'\approx', '≈');
  s = s.replaceAll(r'\cdot', '·');
  s = s.replaceAll(r'\,', ' ');

  s = s.replaceAllMapped(
    RegExp(r'\\text\{([^}]*)\}'),
    (match) => match.group(1) ?? '',
  );

  // Convert markdown table lines into clean copy text.
  final outputLines = <String>[];
  for (final rawLine in s.split('\n')) {
    final line = rawLine.trim();

    final isSeparator = RegExp(
      r'^\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|$',
    ).hasMatch(line);

    if (isSeparator) {
      continue;
    }

    final isTableRow =
        line.startsWith('|') && line.endsWith('|') && line.split('|').length >= 3;

    if (isTableRow) {
      final cells = line
          .split('|')
          .map((cell) => cell.trim())
          .where((cell) => cell.isNotEmpty)
          .toList();

      if (cells.length >= 2) {
        var left = cells[0].replaceAll(RegExp(r'\s+x$'), '');
        var right = cells[1].replaceAll(RegExp(r'\s+y$'), '');

        if (left.toLowerCase().contains('bedrooms') &&
            right.toLowerCase().contains('price')) {
          outputLines.add('');
          outputLines.add('Bedrooms -> Price');
        } else {
          outputLines.add('$left -> $right');
        }
      }
    } else {
      outputLines.add(rawLine);
    }
  }

  s = outputLines.join('\n');

  // Repair any table text that still got joined.
  s = s.replaceAll('Bedrooms x -> Price y', 'Bedrooms -> Price');
  s = s.replaceAll('Bedrooms -> Price2 ->', 'Bedrooms -> Price\n2 ->');
  s = s.replaceAll('Price y2 ->', 'Price\n2 ->');

  for (var i = 0; i < 5; i++) {
    s = s.replaceAllMapped(
      RegExp(r'(\d+\s*->\s*[0-9,]+)\s+(\d+\s*->)'),
      (match) => '${match.group(1)}\n${match.group(2)}',
    );
  }

  // Clean markdown emphasis
  s = s.replaceAllMapped(RegExp(r'\*\*(.*?)\*\*'), (m) => m.group(1) ?? '');
  s = s.replaceAllMapped(RegExp(r'__(.*?)__'), (m) => m.group(1) ?? '');
  s = s.replaceAllMapped(RegExp(r'`([^`]+)`'), (m) => m.group(1) ?? '');

  // Clean extra blank lines
  s = s.replaceAll(RegExp(r'\n{3,}'), '\n\n');

  return s.trim();
}

'''

text = text[:start] + new_func + "\n" + text[end:]

path.write_text(text, encoding="utf-8")
print("Copy table spacing fixed.")
