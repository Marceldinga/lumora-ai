from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_table_spacing_fix.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

old = """  // Clean extra blank lines.
  s = s.replaceAll(RegExp(r'\\n{3,}'), '\\n\\n');

  return s.trim();
}"""

new = """  // Fix table/list spacing after markdown table normalization.
  s = s.replaceAll('Bedrooms -> Price- ', 'Bedrooms -> Price\\n\\n- ');
  s = s.replaceAll('Price- ', 'Price\\n\\n- ');
  s = s.replaceAllMapped(
    RegExp(r'(:)\\n(Bedrooms -> Price)'),
    (match) => '\${match.group(1)}\\n\\n\${match.group(2)}\\n',
  );

  // Ensure bullet rows do not stick to previous text.
  s = s.replaceAllMapped(
    RegExp(r'([^\\n])(-\\s+\\d+\\s+->)'),
    (match) => '\${match.group(1)}\\n\${match.group(2)}',
  );

  // Clean extra blank lines.
  s = s.replaceAll(RegExp(r'\\n{3,}'), '\\n\\n');

  return s.trim();
}"""

if old not in text:
    raise RuntimeError("Could not find normalizeLumoraDisplay ending block.")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("Table spacing fix applied.")
