from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_final_quiz_repair_gate.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Version update
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.7.7-final-quiz-repair-gate"',
    text,
    count=1,
)

text = text.replace("Lumora Brain v12.7.6", "Lumora Brain v12.7.7")
text = text.replace("Lumora Brain v12.7.5", "Lumora Brain v12.7.7")
text = text.replace("Lumora Brain v12.7.4", "Lumora Brain v12.7.7")

helper = r'''
def text_equivalent_for_verifier(a: str, b: str) -> bool:
    aa = re.sub(r"\s+", " ", normalize_text(a)).strip().lower()
    bb = re.sub(r"\s+", " ", normalize_text(b)).strip().lower()
    return aa == bb


def repair_unapproved_quiz_with_ai(question: str, draft_answer: str, verification: Dict[str, Any]) -> Optional[str]:
    """
    Universal quiz repair pass for any subject.
    Used when verifier says approved=false or the improved_answer did not actually fix issues.
    """
    if not GROQ_API_KEY:
        return None

    issues = verification.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]

    issues_text = "\n".join(f"- {normalize_text(str(x))}" for x in issues)

    repair_prompt = f"""
You are Lumora Quiz Repair.

The quiz below was NOT approved by the verifier.

Your job:
Rewrite the quiz so it is correct, clear, student-friendly, and unambiguous.

Universal rules:
- Works for any subject.
- Every multiple-choice question must have exactly one best answer.
- Do not use ambiguous questions.
- Do not use duplicated labels like A) A).
- Do not use "all of the above" or "both A and C" unless absolutely necessary.
- Make answer keys match options exactly.
- Use simple, verified concepts.
- If a fact is uncertain, replace the whole question with a safer question.
- Return only the repaired quiz text.
- Do not return JSON.
- Do not explain the repair.

Format:
Quiz

1. Question text
A) Option
B) Option
C) Option
D) Option

Correct answer: B) Option text

Verifier issues:
{issues_text}

User request:
{question}

Draft quiz:
{draft_answer}
"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_VERIFIER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You repair quizzes for factual accuracy and clarity. Return only the final quiz.",
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

    except Exception:
        return None
'''

if "def repair_unapproved_quiz_with_ai" not in text:
    marker = "def brain_store_memory("
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find brain_store_memory marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted universal quiz repair helper.")
else:
    print("Universal quiz repair helper already exists.")

old_block = '''if verification:
            improved = verification.get("improved_answer")
            if improved:
                reply = normalize_quiz_output_text(improved)

        if verification and not verification.get("approved", True):
            reply = verification.get("improved_answer") or reply'''

new_block = '''if verification:
            improved = verification.get("improved_answer")
            if improved:
                reply = normalize_quiz_output_text(improved)

            # Final quiz safety gate:
            # If the verifier rejects a quiz, repair it before returning to the student.
            if task_type == "quiz" and not verification.get("approved", True):
                repaired_quiz = repair_unapproved_quiz_with_ai(message, reply, verification)

                if repaired_quiz:
                    reply = repaired_quiz
                    verification = brain_verifier(message, reply, task_type)

                    improved_after_repair = verification.get("improved_answer") if verification else None
                    if improved_after_repair:
                        reply = normalize_quiz_output_text(improved_after_repair)

        if verification and not verification.get("approved", True):
            # Do not silently return a failed quiz as if it were approved.
            if task_type == "quiz":
                reply = normalize_quiz_output_text(reply)
            else:
                reply = verification.get("improved_answer") or reply'''

if old_block in text:
    text = text.replace(old_block, new_block)
    print("Patched existing verification gate.")
else:
    print("Exact verification block not found. Trying fallback insertion.")

    fallback = '''if verification and not verification.get("approved", True):'''
    idx = text.find(fallback)
    if idx == -1:
        raise RuntimeError("Could not find verification fallback block.")

    insert = '''if verification and task_type == "quiz" and not verification.get("approved", True):
            repaired_quiz = repair_unapproved_quiz_with_ai(message, reply, verification)
            if repaired_quiz:
                reply = repaired_quiz
                verification = brain_verifier(message, reply, task_type)
                improved_after_repair = verification.get("improved_answer") if verification else None
                if improved_after_repair:
                    reply = normalize_quiz_output_text(improved_after_repair)

        '''
    text = text[:idx] + insert + text[idx:]
    print("Inserted fallback quiz repair gate.")

path.write_text(text, encoding="utf-8")
print("Final quiz repair gate patch applied.")
