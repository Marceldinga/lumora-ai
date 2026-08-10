from pathlib import Path

path = Path(r"C:\Users\mding\lumora_ai\backend\main.py")
text = path.read_text(encoding="utf-8")

backup = path.with_name("main_backup_linear_regression_lesson_fix.py")
backup.write_text(text, encoding="utf-8")
print(f"Backup created: {backup}")

# Version labels
for old in [
    'APP_VERSION = "12.6.2-force-unit-syntax-fixed"',
    'APP_VERSION = "12.6.1-force-unit-fixed"',
    'APP_VERSION = "12.6.0-json-verifier-fallback-fixed"',
    'APP_VERSION = "12.5.0-study-verifier-quality-fixed"',
    'APP_VERSION = "12.4.0-universal-study-router-intent-fixed"',
]:
    text = text.replace(old, 'APP_VERSION = "12.7.0-deterministic-math-lessons"')

text = text.replace("# Version: 12.6.2-force-unit-syntax-fixed", "# Version: 12.7.0-deterministic-math-lessons")
text = text.replace("# Version: 12.6.1-force-unit-format-fixed", "# Version: 12.7.0-deterministic-math-lessons")
text = text.replace("# Version: 12.5.0-study-verifier-quality-fixed", "# Version: 12.7.0-deterministic-math-lessons")
text = text.replace("# Version: 12.4.0-universal-study-router-intent-fixed", "# Version: 12.7.0-deterministic-math-lessons")

text = text.replace("Lumora Brain v12.6", "Lumora Brain v12.7")
text = text.replace("Lumora Brain v12.4", "Lumora Brain v12.7")
text = text.replace("universal-v12.6-force-unit-syntax-fixed", "universal-v12.7-deterministic-lessons")
text = text.replace("universal-v12.6-force-unit-fixed", "universal-v12.7-deterministic-lessons")
text = text.replace("universal-v12.5-study-verifier", "universal-v12.7-deterministic-lessons")
text = text.replace("universal-v12.4-intent-fixed", "universal-v12.7-deterministic-lessons")

helper = r'''
def is_deterministic_linear_regression_lesson_request(message: str) -> bool:
    text = normalize_text(message).lower()

    if "linear regression" not in text:
        return False

    # If the user gives real x/y data, let the Python calculation engine handle it.
    try:
        if parse_regression_pairs(message):
            return False
    except Exception:
        pass

    lesson_words = [
        "explain", "what is", "teach", "simple example", "example",
        "lesson", "understand", "overview", "how does", "in simple terms"
    ]

    return any(word in text for word in lesson_words)


def deterministic_linear_regression_lesson_reply(message: str) -> Optional[str]:
    if not is_deterministic_linear_regression_lesson_request(message):
        return None

    # Verified example:
    # x = bedrooms, y = house price
    # slope = 50000, intercept = 50000
    # model: y = 50000x + 50000
    # prediction for x = 6: y = 350000
    return (
        "Linear regression explained\n\n"
        "Linear regression is a method used to model the relationship between an input variable "
        "\\( x \\) and an output variable \\( y \\). It finds the best straight line that can be used "
        "to predict \\( y \\) from \\( x \\).\n\n"
        "The general equation is:\n\n"
        "\\[ y = mx + b \\]\n\n"
        "Where:\n"
        "- \\( y \\) is the value we want to predict\n"
        "- \\( x \\) is the input value\n"
        "- \\( m \\) is the slope\n"
        "- \\( b \\) is the intercept\n\n"
        "Simple example\n\n"
        "Suppose we want to predict house price from the number of bedrooms:\n\n"
        "| Bedrooms \\(x\\) | Price \\(y\\) |\n"
        "|---:|---:|\n"
        "| 2 | 150,000 |\n"
        "| 3 | 200,000 |\n"
        "| 4 | 250,000 |\n"
        "| 5 | 300,000 |\n\n"
        "Each time the number of bedrooms increases by 1, the price increases by 50,000. "
        "So the slope is:\n\n"
        "\\[ m = 50000 \\]\n\n"
        "Now use one point, for example \\( x = 2, y = 150000 \\), to find the intercept:\n\n"
        "\\[ y = mx + b \\]\n\n"
        "\\[ 150000 = 50000(2) + b \\]\n\n"
        "\\[ 150000 = 100000 + b \\]\n\n"
        "\\[ b = 50000 \\]\n\n"
        "So the correct regression equation is:\n\n"
        "\\[ y = 50000x + 50000 \\]\n\n"
        "Prediction example\n\n"
        "For a 6-bedroom house:\n\n"
        "\\[ y = 50000(6) + 50000 \\]\n\n"
        "\\[ y = 300000 + 50000 = 350000 \\]\n\n"
        "Final answer: the predicted price for a 6-bedroom house is 350,000.\n\n"
        "Key idea: linear regression finds the line that best predicts an output from an input."
    )
'''

if "def deterministic_linear_regression_lesson_reply" not in text:
    marker = "def lumora_brain_engine("
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find lumora_brain_engine marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]
    print("Inserted deterministic linear regression lesson helper.")
else:
    print("Helper already exists.")

lesson_branch = r'''
    lesson_reply = deterministic_linear_regression_lesson_reply(message)
    if lesson_reply:
        verification = {
            "approved": True,
            "score": 100,
            "issues": [],
            "verifier": "deterministic_lesson_template",
            "verifier_model": None,
        }

        brain_store_memory(
            user_key=user_key,
            question=message,
            answer=lesson_reply,
            task_type="study",
            provider="python",
            model="deterministic-linear-regression-lesson",
            verification=verification,
        )
        track_usage(user_key, "chat", True)

        return {
            "ok": True,
            "reply": lesson_reply,
            "brain": "Lumora Brain v12.7",
            "task_type": "study",
            "mode": "study",
            "provider": "python",
            "model": "deterministic-linear-regression-lesson",
            "cached": False,
            "used_search": False,
            "calculation_used": False,
            "calculation_result": None,
            "request_id": request_id,
            "elapsed_seconds": 0.0,
            "verification": verification,
        }

'''

if "deterministic-linear-regression-lesson" not in text:
    target = "    task_type = brain_classify_task(message)"
    idx = text.find(target)
    if idx == -1:
        raise RuntimeError("Could not find task_type classification marker.")
    text = text[:idx] + lesson_branch + text[idx:]
    print("Inserted deterministic lesson branch.")
else:
    print("Lesson branch already exists.")

path.write_text(text, encoding="utf-8")
print("Patch complete.")
