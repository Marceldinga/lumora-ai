from pathlib import Path
import re

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_group2_quiz_fact_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Update backend version
text = re.sub(
    r'APP_VERSION = "[^"]+"',
    'APP_VERSION = "12.7.3-group2-quiz-fact-check"',
    text,
    count=1,
)

text = text.replace("Lumora Brain v12.7.2.2", "Lumora Brain v12.7.3")
text = text.replace("Lumora Brain v12.7.2", "Lumora Brain v12.7.3")
text = text.replace("Lumora Brain v12.7.1", "Lumora Brain v12.7.3")
text = text.replace("Lumora Brain v12.7", "Lumora Brain v12.7.3")

helper = r'''
def repair_group2_chemistry_quiz_facts(reply: str) -> str:
    """
    Local chemistry fact repair for Group 2 quizzes.
    Prevents common wrong answer keys before the user sees them.
    """
    s = normalize_text(reply)

    lower = s.lower()
    if "group 2" not in lower and "alkaline earth" not in lower:
        return s

    # Group 2 reactivity trend:
    # Reactivity generally increases down the group.
    s = re.sub(
        r'(?ms)^(\d+)\.\s+What is the trend in the reactivity of Group 2 elements\?\s*'
        r'\nA\)\s+Increases down the group\s*'
        r'\nB\)\s+Decreases down the group\s*'
        r'\nC\)\s+Remains the same down the group\s*'
        r'\nD\)\s+Increases up the group\s*'
        r'\n\s*Correct answer:\s+B\)\s+Decreases down the group',
        r'\1. What is the trend in the reactivity of Group 2 elements?\n'
        r'A) Increases down the group\n'
        r'B) Decreases down the group\n'
        r'C) Remains the same down the group\n'
        r'D) Increases up the group\n\n'
        r'Correct answer: A) Increases down the group',
        s,
    )

    # If a model gives only the wrong answer line in a reactivity block, fix it.
    s = re.sub(
        r'(?ms)(What is the trend in the reactivity of Group 2 elements\?.*?)'
        r'Correct answer:\s+B\)\s+Decreases down the group',
        r'\1Correct answer: A) Increases down the group',
        s,
    )

    # Group 2 melting points do not follow a perfectly simple monotonic trend.
    s = re.sub(
        r'(?ms)^(\d+)\.\s+What is the trend in the melting points of Group 2 elements\?.*?'
        r'Correct answer:\s+[A-D]\).*?(?=\n\n\d+\.|\Z)',
        r'\1. Which statement best describes the melting point trend of Group 2 elements?\n'
        r'A) They follow a simple steady increase down the group\n'
        r'B) They follow a simple steady decrease down the group\n'
        r'C) They vary and do not follow a perfectly regular trend\n'
        r'D) They are all the same\n\n'
        r'Correct answer: C) They vary and do not follow a perfectly regular trend',
        s,
    )

    # Fireworks color facts.
    # Barium = green, Strontium = red, Magnesium = bright white light/sparks.
    s = re.sub(
        r'(?ms)^(\d+)\.\s+Which Group 2 element is used in fireworks to produce a bright green color\?.*?'
        r'Correct answer:\s+[A-D]\).*?(?=\n\n\d+\.|\Z)',
        r'\1. Which Group 2 element is used in fireworks to produce a bright green color?\n'
        r'A) Magnesium (Mg)\n'
        r'B) Calcium (Ca)\n'
        r'C) Strontium (Sr)\n'
        r'D) Barium (Ba)\n\n'
        r'Correct answer: D) Barium (Ba)',
        s,
    )

    s = re.sub(
        r'(?ms)^(\d+)\.\s+Which Group 2 element is used in fireworks to produce a red color\?.*?'
        r'Correct answer:\s+[A-D]\).*?(?=\n\n\d+\.|\Z)',
        r'\1. Which Group 2 element is used in fireworks to produce a red color?\n'
        r'A) Magnesium (Mg)\n'
        r'B) Calcium (Ca)\n'
        r'C) Strontium (Sr)\n'
        r'D) Barium (Ba)\n\n'
        r'Correct answer: C) Strontium (Sr)',
        s,
    )

    return s.strip()

'''

if "def repair_group2_chemistry_quiz_facts" not in text:
    marker = "def clean_response_text(text: str) -> str:"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find clean_response_text marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted repair_group2_chemistry_quiz_facts().")
else:
    print("repair_group2_chemistry_quiz_facts() already exists.")

# Make clean_response_text pass all output through the repair.
text = text.replace(
    "return quiz_formatted",
    "return repair_group2_chemistry_quiz_facts(quiz_formatted)"
)

text = text.replace(
    "return cleaned.strip()",
    "return repair_group2_chemistry_quiz_facts(cleaned.strip())"
)

# Strengthen verifier prompt if the text exists.
text = text.replace(
    "- chemistry accuracy: balanced equations, oxidation states, ion charges, and periodic trends",
    "- chemistry accuracy: balanced equations, oxidation states, ion charges, and periodic trends\n"
    "- Group 2 rule: reactivity increases down the group\n"
    "- Group 2 rule: elements usually form +2 ions and have outer configuration ns^2\n"
    "- Group 2 rule: Group 2 oxides are generally basic\n"
    "- Group 2 rule: barium gives green fireworks, strontium gives red, magnesium gives bright white light/sparks\n"
    "- Group 2 rule: melting points do not follow a perfectly regular simple trend"
)

path.write_text(text, encoding="utf-8")
print("Group 2 quiz fact-check patch applied.")
