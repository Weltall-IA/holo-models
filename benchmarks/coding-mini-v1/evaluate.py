#!/usr/bin/env python3
import re
import sys
from pathlib import Path

# Add tests directory to sys.path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tests.test_py01 import run_py01_tests
from tests.test_py02 import run_py02_tests
from tests.test_py03 import run_py03_tests
from tests.test_cpp01 import run_cpp01_tests
from tests.test_cpp02 import run_cpp02_tests
from tests.test_cpp03 import run_cpp03_tests


def extract_code_block(text: str, language: str) -> str:
    if not text:
        return ""

    # Try matching fenced code blocks
    if language == "python":
        m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Fallback to def/class if no fence
        m_def = re.search(r"(?:class\s+\w+|def\s+\w+).*", text, re.DOTALL)
        if m_def:
            return m_def.group(0).strip()
    elif language == "cpp":
        m = re.search(r"```(?:cpp|c\+\+|c)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Fallback to #include / int main
        m_inc = re.search(r"(?:#include|int\s+main).*", text, re.DOTALL)
        if m_inc:
            return m_inc.group(0).strip()

    return text.strip()


def evaluate_case(case_id: str, raw_output: str) -> dict:
    lang = "python" if case_id.startswith("PY") else "cpp"
    code = extract_code_block(raw_output, lang)

    if not code:
        return {
            "case_id": case_id,
            "language": lang,
            "compile_pass": False,
            "public_pass": False,
            "hidden_pass": False,
            "passed": False,
            "extracted_code": "",
            "error": "No code block extracted from model response"
        }

    res = {}
    if case_id == "PY01":
        res = run_py01_tests(code)
        compile_pass = True if not res.get("error") or "SyntaxError" not in res.get("error", "") else False
    elif case_id == "PY02":
        res = run_py02_tests(code)
        compile_pass = True if not res.get("error") or "SyntaxError" not in res.get("error", "") else False
    elif case_id == "PY03":
        res = run_py03_tests(code)
        compile_pass = True if not res.get("error") or "SyntaxError" not in res.get("error", "") else False
    elif case_id == "CPP01":
        res = run_cpp01_tests(code)
        compile_pass = res.get("compile_pass", False)
    elif case_id == "CPP02":
        res = run_cpp02_tests(code)
        compile_pass = res.get("compile_pass", False)
    elif case_id == "CPP03":
        res = run_cpp03_tests(code)
        compile_pass = res.get("compile_pass", False)
    else:
        return {
            "case_id": case_id,
            "language": lang,
            "compile_pass": False,
            "public_pass": False,
            "hidden_pass": False,
            "passed": False,
            "extracted_code": code,
            "error": f"Unknown case ID: {case_id}"
        }

    pub = bool(res.get("public_pass", False))
    hid = bool(res.get("hidden_pass", False))
    comp = bool(compile_pass)
    passed = comp and pub and hid

    out = {
        "case_id": case_id,
        "language": lang,
        "compile_pass": comp,
        "public_pass": pub,
        "hidden_pass": hid,
        "passed": passed,
        "extracted_code": code,
        "error": res.get("error")
    }

    if "differential_passed" in res:
        out["differential_passed"] = res["differential_passed"]
        out["differential_total"] = res["differential_total"]

    return out


if __name__ == "__main__":
    print("Evaluate module loaded successfully.")
