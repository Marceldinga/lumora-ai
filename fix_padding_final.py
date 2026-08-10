from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\lib\main.dart")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_remove_duplicate_padding_final.dart")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Remove the inserted duplicate padding line everywhere.
text = text.replace(
    "                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 140),\n",
    ""
)
text = text.replace(
    "            padding: const EdgeInsets.fromLTRB(16, 16, 16, 140),\n",
    ""
)
text = text.replace(
    "        padding: const EdgeInsets.fromLTRB(16, 16, 16, 140),\n",
    ""
)

old = "padding: EdgeInsets.all(MediaQuery.of(context).size.width < 900 ? 12 : 22),"

new = """padding: EdgeInsets.fromLTRB(
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              MediaQuery.of(context).size.width < 900 ? 12 : 22,
              140,
            ),"""

# Replace only the first matching chat ListView padding.
if old not in text:
    print("Existing EdgeInsets.all padding line not found. It may already be fixed.")
else:
    text = text.replace(old, new, 1)
    print("Converted chat ListView padding to bottom-safe padding.")

path.write_text(text, encoding="utf-8")
print("Duplicate padding final fix complete.")
