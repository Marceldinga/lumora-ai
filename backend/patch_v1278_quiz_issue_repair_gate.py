from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_v1278_quiz_issue_repair_gate.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Version update
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.7.8-quiz-issue-repair-gate"',
    text,
    count=1,
)

text = re.sub(
    r'Lumora Brain v12\.7(?:\.\d+)?',
    'Lumora Brain v12.7.8',
    text,
)

helper = r'''
def quiz_needs_repair(reply: str, verification: Dict[str, Any]) -> bool:
    """
    Repair quizzes when verifier finds issues, even if approved=true.
    Also repair obvious formatting/encoding problems.
    """
    if not verification:
        return False

    issues = verification.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]

    improved = normalize_text(verification.get("improved_answer") or "")
    original = normalize_text(reply)

    has_issues = len([x for x in issues if normalize_text(str(x)).strip()]) > 0
    rejected = not verification.get("approved", True)

    improved_same = False
    if improved:
        improved_same = re.sub(r"\s+", " ", improved).strip().lower() == re.sub(r"\s+", " ", original).strip().lower()

    suspicious_text = any(bad in original.lower() for bad in [
        "â",
        "�",
        "a) a)",
        "b) b)",
        "c) c)",
        "d) d)",
        "all of the above",
        "both a and c",
    ])

    return rejected or has_issues or suspicious_text or (has_issues and improved_same)
'''

if "def quiz_needs_repair(" not in text:
    marker = "def repair_unapproved_quiz_with_ai("
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find repair_unapproved_quiz_with_ai marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted quiz_needs_repair().")
else:
    print("quiz_needs_repair() already exists.")

# Update repair prompt wording if present
text = text.replace(
    "The verifier rejected this quiz. Rewrite it before the student sees it.",
    "The verifier rejected or flagged this quiz. Rewrite it before the student sees it."
)

text = text.replace(
    "- If asking about oxygen released in photosynthesis, oxygen comes from water during light-dependent reactions.",
    "- If asking about oxygen released in photosynthesis, oxygen comes from water during light-dependent reactions.\n"
    "- For photosynthesis, the standard overall equation is: 6CO2 + 6H2O -> C6H12O6 + 6O2.\n"
    "- Avoid broken characters like â or �. Use -> or LaTeX \\rightarrow."
)

# Improve quiz cleanup for broken arrows and common mojibake.
if "def normalize_quiz_output_text" in text:
    text = text.replace(
        "s = normalize_text(reply)",
        "s = normalize_text(reply)\n\n    # Fix common mojibake/broken arrow characters in model output.\n    s = s.replace('â†’', '→').replace('â\x86\x92', '→').replace('�', '→')\n    s = re.sub(r'\\s+â\\s+', ' → ', s)"
    )

tag = "# FINAL_QUIZ_ISSUE_REPAIR_GATE_V1278"

if tag not in text:
    # Put the new gate after the existing v12.7.7 gate if available.
    old_tag = "# FINAL_QUIZ_REPAIR_GATE_V1277"
    idx = text.find(old_tag)

    if idx == -1:
        # fallback: insert after any verifier call line
        lines = text.splitlines(keepends=True)
        target_i = None
        for i, line in enumerate(lines):
            if "verification" in line and "brain_verifier" in line and "=" in line:
                target_i = i
                break
        if target_i is None:
            raise RuntimeError("Could not find verifier gate insertion point.")
        indent = lines[target_i][:len(lines[target_i]) - len(lines[target_i].lstrip())]
        insert_at = target_i + 1
    else:
        # find line containing old tag
        before = text[:idx]
        line_no = before.count("\n")
        lines = text.splitlines(keepends=True)
        indent = lines[line_no][:len(lines[line_no]) - len(lines[line_no].lstrip())]
        # Insert before old gate so issue-repair happens first.
        insert_at = line_no

    gate = f'''
{indent}{tag}
{indent}if task_type == "quiz" and verification and quiz_needs_repair(reply, verification):
{indent}    repaired_quiz = repair_unapproved_quiz_with_ai(message, reply, verification)
{indent}    if repaired_quiz:
{indent}        reply = normalize_quiz_output_text(repaired_quiz)
{indent}        verification = brain_verifier(message, reply, task_type)
{indent}        improved_after_repair = verification.get("improved_answer") if verification else None
{indent}        if improved_after_repair:
{indent}            reply = normalize_quiz_output_text(improved_after_repair)
{indent}    else:
{indent}        reply = normalize_quiz_output_text(reply)
'''

    lines.insert(insert_at, gate)
    text = "".join(lines)
    print("Inserted FINAL_QUIZ_ISSUE_REPAIR_GATE_V1278.")
else:
    print("FINAL_QUIZ_ISSUE_REPAIR_GATE_V1278 already exists.")

path.write_text(text, encoding="utf-8")
print("v12.7.8 quiz issue repair gate patch complete.")
