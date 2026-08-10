from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_universal_quiz_quality_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Version update
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.7.5-universal-quiz-quality-fixed"',
    text,
    count=1,
)

text = text.replace("Lumora Brain v12.7.4", "Lumora Brain v12.7.5")
text = text.replace("Lumora Brain v12.7.3", "Lumora Brain v12.7.5")
text = text.replace("Lumora Brain v12.7.2", "Lumora Brain v12.7.5")
text = text.replace("Lumora Brain v12.7.1", "Lumora Brain v12.7.5")

helper = r'''
def normalize_quiz_output_text(reply: str) -> str:
    """
    Universal quiz cleanup.
    Fixes formatting problems for all subjects, not only chemistry.

    Fixes:
    - A) A) Option -> A) Option
    - Correct answer: B) B) Option -> Correct answer: B) Option
    - Markdown bold in questions
    - Extra spacing
    """
    s = normalize_text(reply)

    if not s:
        return s

    # Remove markdown bold markers.
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)

    # Fix duplicated option labels:
    # A) A) Group 1 -> A) Group 1
    s = re.sub(
        r'(?m)^([A-D])\)\s+\1\)\s+',
        r'\1) ',
        s,
        flags=re.IGNORECASE,
    )

    # Fix duplicated correct answer labels:
    # Correct answer: B) B) Group 2 -> Correct answer: B) Group 2
    s = re.sub(
        r'(?im)^(Correct answer:\s*)([A-D])\)\s+\2\)\s+',
        r'\1\2) ',
        s,
    )

    # Fix "Correct answer: B) B)" even with lowercase/spaces.
    s = re.sub(
        r'(?im)^(Correct answer:\s*)([A-D])\)\s+([A-D])\)\s+',
        lambda m: f"{m.group(1)}{m.group(2).upper()}) " if m.group(2).upper() == m.group(3).upper() else m.group(0),
        s,
    )

    # Normalize common LaTeX dollars in quiz text to display-friendly \( ... \)
    # This helps frontend math renderer.
    s = re.sub(r'\$([^$\n]+)\$', r'\\( \1 \\)', s)

    # Ensure every numbered question starts on a clean line.
    s = re.sub(r'(?<!\n)\s+(\d+\.\s+)', r'\n\n\1', s)

    # Ensure Correct answer has a blank line before next question.
    s = re.sub(r'(?m)^(Correct answer:.*?)(\n)(\d+\.\s+)', r'\1\n\n\3', s)

    # Remove too many blank lines.
    s = re.sub(r'\n{3,}', '\n\n', s)

    return s.strip()


def verifier_improvement_was_not_applied(original: str, improved: str, issues: List[str]) -> bool:
    if not issues:
        return False

    o = re.sub(r'\s+', ' ', normalize_text(original)).strip().lower()
    i = re.sub(r'\s+', ' ', normalize_text(improved)).strip().lower()

    return o == i

'''

if "def normalize_quiz_output_text" not in text:
    marker = "def clean_response_text(text: str) -> str:"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find clean_response_text marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted universal quiz cleanup helpers.")
else:
    print("Universal quiz cleanup helpers already exist.")

# Make clean_response_text always normalize quiz text.
text = text.replace(
    "return repair_group2_chemistry_quiz_facts(quiz_formatted)",
    "return normalize_quiz_output_text(repair_group2_chemistry_quiz_facts(quiz_formatted))"
)

text = text.replace(
    "return repair_group2_chemistry_quiz_facts(cleaned.strip())",
    "return normalize_quiz_output_text(repair_group2_chemistry_quiz_facts(cleaned.strip()))"
)

# If clean_response_text has plain return cleaned.strip(), patch that too.
text = text.replace(
    "return cleaned.strip()",
    "return normalize_quiz_output_text(cleaned.strip())"
)

# Strengthen verifier prompt to force real improved_answer.
text = text.replace(
    "improved_answer must contain the final user-facing answer.",
    "improved_answer must contain the final user-facing answer. If you list any issue, improved_answer MUST fix that issue and must not be identical to the draft answer."
)

text = text.replace(
    "- quiz quality: every multiple-choice question must have exactly one best correct answer",
    "- quiz quality: every multiple-choice question must have exactly one best correct answer\n"
    "- quiz quality: do not output duplicated labels such as A) A) or Correct answer: B) B)\n"
    "- quiz quality: if an option is ambiguous, replace the whole question with a safer verified question\n"
    "- quiz quality: avoid obscure application questions unless the user requested advanced level"
)

# Patch brain_verifier final return so improved_answer also goes through quiz cleanup.
text = text.replace(
    'improved = normalize_text(data.get("improved_answer", "")) or answer',
    'improved = normalize_quiz_output_text(normalize_text(data.get("improved_answer", "")) or answer)'
)

# Patch fallback returns where improved_answer is repaired.
text = text.replace(
    '"improved_answer": repaired,',
    '"improved_answer": normalize_quiz_output_text(repaired),'
)

path.write_text(text, encoding="utf-8")
print("Universal quiz quality patch applied.")
