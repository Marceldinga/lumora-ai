from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_syntax_force_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

start_marker = '    if ctype == "physics_force":'
end_marker = '    if ctype == "kinetic_energy":'

start = text.find(start_marker)
if start == -1:
    raise RuntimeError("Could not find physics_force block start.")

end = text.find(end_marker, start)
if end == -1:
    raise RuntimeError("Could not find kinetic_energy block after physics_force.")

replacement = r'''    if ctype == "physics_force":
        force_value = fmt_num(calculation.get("force"), 6)
        return (
            "Force result\n\n"
            "\\[ F = ma \\]\n\n"
            f"\\[ F = {fmt_num(calculation.get('mass'), 6)} \\times {fmt_num(calculation.get('acceleration'), 6)} = {force_value}\\,\\text{{N}} \\]\n\n"
            f"Final answer: \\( F = {force_value}\\,\\text{{N}} \\)"
        )

'''

new_text = text[:start] + replacement + text[end:]

new_text = new_text.replace(
    'APP_VERSION = "12.6.1-force-unit-fixed"',
    'APP_VERSION = "12.6.2-force-unit-syntax-fixed"'
)
new_text = new_text.replace(
    'APP_VERSION = "12.5.0-study-verifier-quality-fixed"',
    'APP_VERSION = "12.6.2-force-unit-syntax-fixed"'
)
new_text = new_text.replace(
    'APP_VERSION = "12.4.0-universal-study-router-intent-fixed"',
    'APP_VERSION = "12.6.2-force-unit-syntax-fixed"'
)

new_text = new_text.replace("Lumora Brain v12.4", "Lumora Brain v12.6")
new_text = new_text.replace("universal-v12.4-intent-fixed", "universal-v12.6-force-unit-syntax-fixed")
new_text = new_text.replace("universal-v12.5-study-verifier", "universal-v12.6-force-unit-syntax-fixed")

path.write_text(new_text, encoding="utf-8")
print("Fixed physics_force block and syntax.")
