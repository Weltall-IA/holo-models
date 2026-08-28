import json
import re

REASONING_CASES = [
    {
        "id": "R01",
        "name": "ordering_constraints",
        "prompt": """Determine which sequence satisfies all of the following rules:
Rules:
- A must come before C.
- D must come before B.
- C must come before B.

Options:
1. B, D, A, C
2. A, D, C, B
3. D, C, A, B
4. A, C, B, D

Respond with ONLY the option number (1, 2, 3, or 4).""",
        "evaluator": "eval_r01"
    },
    {
        "id": "R02",
        "name": "deployment_window_choice",
        "prompt": """Evaluate the available deployment windows based on company policy:
Deployment Windows:
- W1: Tuesday 01:00 UTC (Database maintenance overlaps)
- W2: Wednesday 03:00 UTC (No conflicting maintenance, on-call engineer present)
- W3: Thursday 02:00 UTC (No conflicting maintenance, no on-call engineer present)

Policy requirements:
1. The deployment must NOT overlap with any maintenance window.
2. An on-call engineer MUST be present during deployment.

Which deployment window must be chosen? Answer with ONLY the window identifier (W1, W2, or W3).""",
        "evaluator": "eval_r02"
    },
    {
        "id": "R03",
        "name": "exact_data_transform",
        "prompt": """Given the following JSON list of line items:
[{"id":"a","qty":2,"price":5},{"id":"b","qty":1,"price":12},{"id":"c","qty":3,"price":4}]

Task:
Calculate the line total for each item (qty * price). Return a JSON object with:
- "total": the sum of all line totals (integer).
- "ids": an array of item ids whose line total is at least 12, sorted alphabetically.

Respond with ONLY the valid JSON object, no Markdown formatting or surrounding text.""",
        "evaluator": "eval_r03"
    }
]

def eval_r01(text: str) -> dict:
    cleaned = text.strip()
    match = re.search(r"\b([1-4])\b", cleaned)
    if match and match.group(1) == "2":
        return {"success": 1, "error": None}
    return {"success": 0, "error": f"Expected option 2, got: {cleaned}"}

def eval_r02(text: str) -> dict:
    cleaned = text.strip().upper()
    if "W2" in cleaned and "W1" not in cleaned and "W3" not in cleaned:
        return {"success": 1, "error": None}
    match = re.search(r"\bW[1-3]\b", cleaned)
    if match and match.group(0) == "W2":
        return {"success": 1, "error": None}
    return {"success": 0, "error": f"Expected W2, got: {cleaned}"}

def eval_r03(text: str) -> dict:
    # Try parsing json directly or extract json
    cleaned = text.strip()
    match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        data = json.loads(cleaned)
        if data.get("total") == 34 and sorted(data.get("ids", [])) == ["b", "c"]:
            return {"success": 1, "error": None}
        return {"success": 0, "error": f"Incorrect content in JSON: {data}"}
    except Exception as e:
        return {"success": 0, "error": f"Failed to parse JSON: {cleaned}"}
