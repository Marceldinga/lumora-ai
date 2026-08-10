from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_v1277_final_quiz_gate.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Update version
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.7.7-final-quiz-repair-gate"',
    text,
    count=1,
)

# Update visible brain labels
text = re.sub(
    r'Lumora Brain v12\.7(?:\.\d+)?',
    'Lumora Brain v12.7.7',
    text,
)

helper = r'''
def repair_unapproved_quiz_with_ai(question: str, draft_answer: str, verification: Dict[str, Any]) -> Optional[str]:
    """
    Universal quiz repair pass for any subject.
    Runs when verifier rejects a quiz.
    """
    if not GROQ_API_KEY:
        return None

    issues = verification.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]

    issues_text = "\n".join(f"- {normalize_text(str(x))}" for x in issues)

    repair_prompt = f"""
You are Lumora Quiz Repair.

The verifier rejected this quiz. Rewrite it before the student sees it.

Rules:
- Works for any subject.
- Return only the repaired quiz text.
- Do not return JSON.
- Every multiple-choice question must have exactly one best answer.
- Use A), B), C), D) options.
- Include "Correct answer: X) option text" after every question.
- Fix every verifier issue.
- Avoid ambiguous questions.
- Avoid duplicated labels like A) A).
- Avoid "all of the above" and "both A and C".
- If a question is unclear, replace the entire question with a safer verified one.
- If asking about loss of electrons, the process is oxidation.
- If asking about oxygen released in photosynthesis, oxygen comes from water during light-dependent reactions.

Verifier issues:
{issues_text}

User request:
{question}

Rejected quiz:
{draft_answer}
"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_VERIFIER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You repair quizzes for factual accuracy, clarity, and unambiguous answer keys.",
                },
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0,
            max_tokens=2200,
        )

        repaired = response.choices[0].message.content or ""
        repaired = clean_response_text(repaired)
        repaired = normalize_quiz_output_text(repaired)
        return repaired.strip() if repaired.strip() else None

    except Exception as e:
        print(f"Quiz repair failed: {e}")
        return None

'''

if "def repair_unapproved_quiz_with_ai" not in text:
    marker = "def brain_store_memory("
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find def brain_store_memory marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted repair_unapproved_quiz_with_ai().")
else:
    print("repair_unapproved_quiz_with_ai() already exists.")

# Insert repair gate immediately after verifier call(s).
tag = "# FINAL_QUIZ_REPAIR_GATE_V1277"

if tag not in text:
    pattern = re.compile(
        r'(?m)^(\s*)verification\s*=\s*brain_verifier\(message,\s*reply,\s*task_type\)\s*$'
    )

    def add_gate(match):
        indent = match.group(1)
        line = match.group(0)

        gate = f"""
{indent}{tag}
{indent}if task_type == "quiz" and verification and not verification.get("approved", True):
{indent}    repaired_quiz = repair_unapproved_quiz_with_ai(message, reply, verification)
{indent}    if repaired_quiz:
{indent}        reply = repaired_quiz
{indent}        verification = brain_verifier(message, reply, task_type)
{indent}        improved_after_repair = verification.get("improved_answer") if verification else None
{indent}        if improved_after_repair:
{indent}            reply = normalize_quiz_output_text(improved_after_repair)
"""
        return line + gate

    text, count = pattern.subn(add_gate, text, count=1)

    if count == 0:
        raise RuntimeError("Could not find verification = brain_verifier(message, reply, task_type).")

    print("Inserted FINAL_QUIZ_REPAIR_GATE_V1277.")
else:
    print("FINAL_QUIZ_REPAIR_GATE_V1277 already exists.")

# Make sure improved answer use is normalized when present.
text = text.replace(
    'reply = improved',
    'reply = normalize_quiz_output_text(improved)'
)

path.write_text(text, encoding="utf-8")
print("v12.7.7 final quiz repair gate patch complete.")
