from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_v1278_gate_guard_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

start_marker = "# FINAL_QUIZ_ISSUE_REPAIR_GATE_V1278"
end_marker = "# FINAL_QUIZ_REPAIR_GATE_V1277"

start = text.find(start_marker)
if start == -1:
    raise RuntimeError("Could not find FINAL_QUIZ_ISSUE_REPAIR_GATE_V1278 marker.")

end = text.find(end_marker, start)
if end == -1:
    raise RuntimeError("Could not find FINAL_QUIZ_REPAIR_GATE_V1277 marker after v12.7.8 gate.")

# Preserve indentation from the marker line
line_start = text.rfind("\n", 0, start) + 1
indent = text[line_start:start]

replacement = f'''{start_marker}
{indent}try:
{indent}    needs_quiz_repair = bool(
{indent}        task_type == "quiz"
{indent}        and verification
{indent}        and quiz_needs_repair(reply, verification)
{indent}    )
{indent}except Exception as e:
{indent}    print(f"Quiz issue-repair check failed: {{e}}")
{indent}    needs_quiz_repair = False

{indent}if needs_quiz_repair:
{indent}    try:
{indent}        repaired_quiz = repair_unapproved_quiz_with_ai(message, reply, verification)
{indent}        if repaired_quiz:
{indent}            reply = normalize_quiz_output_text(repaired_quiz)
{indent}            verification = brain_verifier(message, reply, task_type)
{indent}            improved_after_repair = verification.get("improved_answer") if verification else None
{indent}            if improved_after_repair:
{indent}                reply = normalize_quiz_output_text(improved_after_repair)
{indent}        else:
{indent}            reply = normalize_quiz_output_text(reply)
{indent}    except Exception as e:
{indent}        print(f"Quiz issue-repair gate failed: {{e}}")
{indent}        reply = normalize_quiz_output_text(reply)

{indent}'''

text = text[:start] + replacement + text[end:]

path.write_text(text, encoding="utf-8")
print("v12.7.8 quiz gate guard fix applied.")
