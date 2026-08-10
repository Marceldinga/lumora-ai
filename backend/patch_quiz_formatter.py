from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_quiz_formatter_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Add ast import for parsing Python-style dict strings like {'quiz': [...]}
if "import ast" not in text:
    text = text.replace("import json\n", "import json\nimport ast\n", 1)

# Update version labels
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.7.2-quiz-output-formatter"',
    text,
    count=1,
)
text = text.replace("Lumora Brain v12.7.1", "Lumora Brain v12.7.2")
text = text.replace("Lumora Brain v12.7", "Lumora Brain v12.7.2")

helper = r'''
def format_quiz_object_response(raw_text: str) -> Optional[str]:
    """
    Converts raw quiz dict/JSON text into a clean student-friendly quiz.

    Handles:
    {'quiz': [{'question': ..., 'options': [...], 'correct': ...}]}
    {"quiz": [{"question": ..., "options": [...], "correct": ...}]}
    {"questions": [...]}
    """
    raw = normalize_text(raw_text)
    if not raw:
        return None

    lower = raw.lower()
    if "'quiz'" not in lower and '"quiz"' not in lower and '"questions"' not in lower and "'questions'" not in lower:
        return None

    candidate = raw.strip()
    candidate = candidate.replace("```json", "").replace("```python", "").replace("```", "").strip()

    # Extract only the object portion if the model added prose around it.
    if "{" in candidate and "}" in candidate:
        candidate = candidate[candidate.find("{"):candidate.rfind("}") + 1]

    data = None

    try:
        data = json.loads(candidate)
    except Exception:
        try:
            data = ast.literal_eval(candidate)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    quiz_items = data.get("quiz") or data.get("questions") or data.get("items")
    if not isinstance(quiz_items, list) or not quiz_items:
        return None

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lines: List[str] = ["Quiz", ""]

    for idx, item in enumerate(quiz_items, start=1):
        if not isinstance(item, dict):
            continue

        question = normalize_text(
            item.get("question")
            or item.get("prompt")
            or item.get("q")
            or ""
        )

        if not question:
            continue

        options = item.get("options") or item.get("choices") or item.get("answers") or []
        correct = normalize_text(
            item.get("correct")
            or item.get("correct_answer")
            or item.get("answer")
            or ""
        )
        explanation = normalize_text(item.get("explanation") or item.get("why") or "")

        lines.append(f"{idx}. {question}")

        option_labels: Dict[str, str] = {}

        if isinstance(options, dict):
            for key, value in options.items():
                label = normalize_text(key).upper().replace(")", "").replace(".", "")
                value_text = normalize_text(value)
                if label and value_text:
                    option_labels[label] = value_text
                    lines.append(f"{label}) {value_text}")

        elif isinstance(options, list):
            for opt_index, value in enumerate(options):
                if opt_index >= len(letters):
                    break
                label = letters[opt_index]
                value_text = normalize_text(value)
                option_labels[label] = value_text
                lines.append(f"{label}) {value_text}")

        correct_label = ""
        correct_text = correct

        if correct:
            clean_correct = correct.strip()
            clean_correct_label = clean_correct.upper().replace(")", "").replace(".", "")

            if clean_correct_label in option_labels:
                correct_label = clean_correct_label
                correct_text = option_labels[correct_label]
            else:
                for label, value in option_labels.items():
                    if clean_correct.lower() == value.lower():
                        correct_label = label
                        correct_text = value
                        break

        if correct_text:
            if correct_label:
                lines.append("")
                lines.append(f"Correct answer: {correct_label}) {correct_text}")
            else:
                lines.append("")
                lines.append(f"Correct answer: {correct_text}")

        if explanation:
            lines.append(f"Explanation: {explanation}")

        lines.append("")

    formatted = "\n".join(lines).strip()
    return formatted if formatted != "Quiz" else None

'''

if "def format_quiz_object_response" not in text:
    marker = "def clean_response_text(text: str) -> str:"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find clean_response_text marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted format_quiz_object_response().")
else:
    print("format_quiz_object_response() already exists.")

pattern = r'def clean_response_text\(text: str\) -> str:\s*\n\s*if not text:\s*\n\s*return ""\s*\n\s*cleaned = str\(text\)'

replacement = '''def clean_response_text(text: str) -> str:
    if not text:
        return ""

    quiz_formatted = format_quiz_object_response(str(text))
    if quiz_formatted:
        return quiz_formatted

    cleaned = str(text)'''

new_text, count = re.subn(pattern, replacement, text, count=1)

if count == 0:
    print("clean_response_text already patched or pattern not found.")
    new_text = text
else:
    print("Patched clean_response_text() to format quiz objects.")

path.write_text(new_text, encoding="utf-8")
print("Quiz formatter patch complete.")
