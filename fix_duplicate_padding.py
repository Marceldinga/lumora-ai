from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_fix_duplicate_padding.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Remove the duplicate padding line that was inserted before an existing padding argument.
text = text.replace(
    "                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 140),\n            padding: EdgeInsets.all(MediaQuery.of(context).size.width < 900 ? 12 : 22),",
    "            padding: EdgeInsets.fromLTRB(\n              MediaQuery.of(context).size.width < 900 ? 12 : 22,\n              MediaQuery.of(context).size.width < 900 ? 12 : 22,\n              MediaQuery.of(context).size.width < 900 ? 12 : 22,\n              140,\n            ),"
)

# Backup pattern in case indentation is different.
text = re.sub(
    r'\s*padding:\s*const EdgeInsets\.fromLTRB\(16,\s*16,\s*16,\s*140\),\s*\n\s*padding:\s*EdgeInsets\.all\(MediaQuery\.of\(context\)\.size\.width < 900 \? 12 : 22\),',
    r'''
            padding: EdgeInsets.fromLTRB(
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              140,
            ),''',
    text,
    count=1,
)

path.write_text(text, encoding="utf-8")
print("Duplicate padding fixed.")
