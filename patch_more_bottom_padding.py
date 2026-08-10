from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_more_bottom_padding.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Increase chat ListView bottom padding so the last answer line is not hidden by the input bar.
text = text.replace(
    """              140,
            ),
            itemCount: messages.length + (loading ? 1 : 0),""",
    """              220,
            ),
            itemCount: messages.length + (loading ? 1 : 0),"""
)

path.write_text(text, encoding="utf-8")
print("Bottom padding increased to 220.")
