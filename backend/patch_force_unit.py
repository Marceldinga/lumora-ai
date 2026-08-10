from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_force_unit_direct_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Update visible version labels
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.6.1-force-unit-fixed"',
    text,
    count=1
)
text = text.replace("Lumora Brain v12.4", "Lumora Brain v12.6")
text = text.replace("universal-v12.4-intent-fixed", "universal-v12.6-force-unit-fixed")
text = text.replace("universal-v12.5-study-verifier", "universal-v12.6-force-unit-fixed")
text = text.replace("universal-v12.6-json-verifier", "universal-v12.6-force-unit-fixed")

pattern = r'    if ctype == "physics_force":.*?    if ctype == "kinetic_energy":'

replacement = r'''    if ctype == "physics_force":
        force_value = fmt_num(calculation.get("force"), 6)
        return (
            "Force result\n\n"
            "\\[ F = ma \\]\n\n"
            f"\\[ F = {fmt_num(calculation.get('mass'), 6)} \\times {fmt_num(calculation.get('acceleration'), 6)} = {force_value}\\,\\text{{N}} \\]\n\n"
            f"Final answer: \\( F = {force_value}\\,\\text{{N}} \\)"
        )

    if ctype == "kinetic_energy":'''

new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)

if count != 1:
    raise RuntimeError("physics_force block not found or not replaced.")

path.write_text(new_text, encoding="utf-8")
print("Physics force unit formatter fixed.")
