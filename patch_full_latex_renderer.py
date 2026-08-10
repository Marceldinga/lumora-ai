from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_full_latex_renderer_fix.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Ensure flutter_math_fork import exists.
if "package:flutter_math_fork/flutter_math.dart" not in text:
    last_import = list(re.finditer(r"^import .+?;\s*$", text, flags=re.MULTILINE))[-1]
    insert_at = last_import.end()
    text = text[:insert_at] + "\nimport 'package:flutter_math_fork/flutter_math.dart';" + text[insert_at:]
    print("Added flutter_math_fork import.")

# Replace normalizeLumoraDisplay so it preserves LaTeX instead of destroying inline math.
normalize_start = text.find("String normalizeLumoraDisplay(String input)")
if normalize_start != -1:
    next_class = text.find("class LumoraApiException", normalize_start)
    if next_class == -1:
        raise RuntimeError("Could not find class LumoraApiException after normalizeLumoraDisplay.")

    new_normalize = r'''
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
    '⁺': '+',
    '⁻': '-',
    '₂': '_2',
    '₃': '_3',
    'Â': '',
  };

  replacements.forEach((bad, good) {
    s = s.replaceAll(bad, good);
  });

  // Remove excessive blank lines only.
  s = s.replaceAll(RegExp(r'\n{4,}'), '\n\n\n');

  return s.trim();
}

'''
    text = text[:normalize_start] + new_normalize + text[next_class:]
    print("Replaced normalizeLumoraDisplay().")
else:
    print("normalizeLumoraDisplay() not found. Skipped.")

# Replace the full LumoraSmartText widget with a robust Markdown + LaTeX renderer.
start = text.find("class LumoraSmartText extends StatelessWidget")
if start == -1:
    raise RuntimeError("Could not find LumoraSmartText class.")

# Find next top-level class after LumoraSmartText.
m = re.search(r"\nclass\s+\w+", text[start + 10:])
if not m:
    raise RuntimeError("Could not find next class after LumoraSmartText.")
end = start + 10 + m.start()

new_widget = r'''
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

'''

text = text[:start] + new_widget + text[end:]

path.write_text(text, encoding="utf-8")
print("Full LaTeX + Markdown renderer patch applied.")
