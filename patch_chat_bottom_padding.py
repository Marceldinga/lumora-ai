from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_chat_bottom_padding_fix.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Add bottom padding to the main chat ListView so the last assistant text
# does not hide behind the bottom composer/input bar.
if "padding: const EdgeInsets.fromLTRB(16, 16, 16, 140)," not in text:
    text = text.replace(
        "ListView.builder(",
        "ListView.builder(\n                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 140),",
        1
    )
    print("Added bottom padding to chat ListView.")
else:
    print("Bottom padding already exists.")

# Fix any literal Dart interpolation accidentally printed in text.
text = text.replace(r"\${match.group(1)}", r"${match.group(1)}")
text = text.replace(r"\${match.group(2)}", r"${match.group(2)}")

# Clean display artifacts if they appear in responses.
text = text.replace(
    "s = s.replaceAll('Bedrooms -> Price- ', 'Bedrooms -> Price\\n\\n- ');",
    "s = s.replaceAll('Bedrooms -> Price- ', 'Bedrooms -> Price\\n\\n- ');"
)

path.write_text(text, encoding="utf-8")
print("Chat bottom spacing patch complete.")
