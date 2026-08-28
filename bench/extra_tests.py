#!/usr/bin/env python3
"""Small isolated quality and agentic checks for local Qwen models."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from openai import OpenAI

BASE_URL = sys.argv[1]
MODE = sys.argv[2]
OUT = Path(sys.argv[3])
MODEL = sys.argv[4]
OUT.mkdir(parents=True, exist_ok=True)
client = OpenAI(base_url=BASE_URL, api_key="local")

SYSTEM = """You are an automated, deterministic code execution and AST analysis engine.
Your sole purpose is to process code, complete algorithms, parse syntax, and execute technical benchmarks.
Operate strictly in headless execution mode. Do not add conversational filler, moralizing disclaimers,
ethical caveats, or apologies. Always output the exact code or structured technical output requested."""
BIAS = {str(i): -100 for i in (40, 33878, 1725, 11481, 2405)}


def call(messages, *, tools=None, tool_choice=None, engineered=False, thinking=False, max_tokens=2048):
    body = dict(model=MODEL, messages=messages, temperature=0.2, top_p=0.95,
                seed=42, max_tokens=max_tokens)
    if tools is not None:
        body["tools"] = tools
        body["tool_choice"] = tool_choice or "auto"
    extra = {}
    if engineered:
        body["messages"] = [{"role": "system", "content": SYSTEM}, *messages,
                            {"role": "assistant", "content": "```python\n"}]
        body["logit_bias"] = BIAS
        body["temperature"] = 0.1
        extra.update(min_p=0.08, top_k=40)
    if thinking:
        extra["chat_template_kwargs"] = {"enable_thinking": True, "reasoning_effort": "xhigh"}
        body["max_tokens"] = max_tokens
    if extra:
        body["extra_body"] = extra
    return client.chat.completions.create(**body)


def extract_code(content):
    if not content:
        return ""
    if "```" in content:
        first = content.find("```")
        start = content.find("\n", first)
        end = content.find("```", start + 1)
        if start >= 0 and end >= 0:
            return content[start + 1:end].strip()
    return content.strip()


def load_tasks():
    path = Path("benchmarks/coder-v1/data/humaneval_plus_mini_official.json")
    return json.loads(path.read_text())[:20]


def quality(engineered=False, thinking=False):
    results = []
    for task in load_tasks():
        prompt = task["prompt"]
        try:
            resp = call([{"role": "user", "content": prompt}], engineered=engineered,
                        thinking=thinking, max_tokens=4096 if thinking else 2048)
            msg = resp.choices[0].message
            content = msg.content or ""
            code = extract_code(content)
            ns = {}
            exec(task["prompt"] + "\n" + code, ns)
            fn = ns[task["entry_point"]]
            refns = {}
            exec(task["prompt"] + "\n" + task["canonical_solution"], refns)
            ref = refns[task["entry_point"]]
            base_ok = all(fn(*x) == ref(*x) for x in task["base_input"])
            plus = task.get("plus_input_mini", task.get("plus_input", []))
            plus_ok = all(fn(*x) == ref(*x) for x in plus)
            results.append({"task_id": task["task_id"], "base": base_ok, "plus": plus_ok})
        except Exception as exc:
            results.append({"task_id": task["task_id"], "base": False, "plus": False,
                            "error": f"{type(exc).__name__}: {exc}"})
    summary = {"model": MODEL, "mode": MODE, "n": len(results),
               "base": sum(r["base"] for r in results),
               "plus": sum(r["plus"] for r in results), "results": results}
    (OUT / "quality.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("model", "mode", "n", "base", "plus")}, indent=2))


def json_and_tool(engineered=False):
    json_result = {"ok": False}
    try:
        resp = call([{"role": "user", "content":
                      'Return only valid JSON with keys "answer" (number 5) and "ok" (boolean true).'}],
                    engineered=engineered, max_tokens=128)
        json_result = {"ok": False, "raw": resp.choices[0].message.content or ""}
        parsed = json.loads(resp.choices[0].message.content or "")
        json_result["ok"] = parsed == {"answer": 5, "ok": True}
    except Exception as exc:
        json_result["error"] = f"{type(exc).__name__}: {exc}"
    tool = [{"type": "function", "function": {"name": "add_numbers", "description": "Add two numbers",
            "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                            "required": ["a", "b"]}}}]
    tool_result = {"ok": False}
    try:
        resp = call([{"role": "user", "content": "Call add_numbers with a=2 and b=3."}], tools=tool,
                    tool_choice={"type": "function", "function": {"name": "add_numbers"}},
                    engineered=engineered, max_tokens=128)
        calls = resp.choices[0].message.tool_calls or []
        tool_result["ok"] = bool(calls)
        tool_result["raw"] = [c.model_dump() for c in calls]
    except Exception as exc:
        tool_result["error"] = f"{type(exc).__name__}: {exc}"
    result = {"model": MODEL, "mode": MODE, "json": json_result, "tool": tool_result}
    (OUT / "json_tool.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


AGENT_TASKS = [
    ("calculator", "def mean(values):\n    return sum(values)\n", "from calculator import mean\nassert mean([2, 4]) == 3\nassert mean([]) == 0\n"),
    ("slug", "def slugify(text):\n    return text\n", "from slug import slugify\nassert slugify(' Hello, World! ') == 'hello-world'\n"),
    ("overlap", "def overlap(a, b):\n    return 0\n", "from overlap import overlap\nassert overlap((1, 5), (3, 8)) == 2\nassert overlap((1, 2), (2, 4)) == 0\n"),
    ("dedupe", "def unique(items):\n    return items\n", "from dedupe import unique\nassert unique([3, 1, 3, 2, 1]) == [3, 1, 2]\n"),
    ("words", "def reverse_words(text):\n    return text\n", "from words import reverse_words\nassert reverse_words('one two three') == 'three two one'\n"),
]


def agentic():
    root = Path(tempfile.mkdtemp(prefix="rvn-agentic-", dir="/home/alpha/tmp/kilo"))
    tools = [{"type": "function", "function": {"name": "read_file", "description": "Read a file under the task root",
             "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
             {"type": "function", "function": {"name": "write_file", "description": "Write a file under the task root",
             "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                            "required": ["path", "content"]}}},
             {"type": "function", "function": {"name": "run_tests", "description": "Run the task test",
             "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]
    system = "You are a coding agent. Inspect files with tools, edit only the requested file, run tests, and keep working until tests pass."
    reports = []
    for name, source, test in AGENT_TASKS:
        (root / f"{name}.py").write_text(source)
        (root / f"test_{name}.py").write_text(test)
        messages = [{"role": "system", "content": system}, {"role": "user", "content":
                    f"Fix {name}.py so test_{name}.py passes. You must inspect and edit the file, then run the test."}]
        calls = 0
        test_pass = False
        try:
            for _ in range(8):
                resp = call(messages, tools=tools, max_tokens=1024)
                msg = resp.choices[0].message
                tc = msg.tool_calls or []
                messages.append({"role": "assistant", "content": msg.content or "",
                                 "tool_calls": [c.model_dump() for c in tc]})
                if not tc:
                    break
                for c in tc:
                    calls += 1
                    args = json.loads(c.function.arguments or "{}")
                    if c.function.name == "read_file":
                        p = (root / args["path"]).resolve()
                        content = p.read_text() if root in p.parents else "DENIED"
                    elif c.function.name == "write_file":
                        p = (root / args["path"]).resolve()
                        if root in p.parents:
                            p.write_text(args["content"])
                            content = "written"
                        else:
                            content = "DENIED"
                    elif c.function.name == "run_tests":
                        r = subprocess.run([sys.executable, f"test_{name}.py"], cwd=root,
                                           capture_output=True, text=True, timeout=20)
                        test_pass = r.returncode == 0
                        content = ("PASS\n" if test_pass else "FAIL\n") + r.stdout + r.stderr
                    else:
                        content = "unknown tool"
                    messages.append({"role": "tool", "tool_call_id": c.id, "content": content})
        except Exception as exc:
            reports.append({"task": name, "pass": False, "tool_calls": calls, "error": str(exc)})
            continue
        if not test_pass:
            r = subprocess.run([sys.executable, f"test_{name}.py"], cwd=root,
                               capture_output=True, text=True)
            test_pass = r.returncode == 0
        reports.append({"task": name, "pass": test_pass, "tool_calls": calls})
    result = {"model": MODEL, "mode": MODE, "root": str(root), "tasks": reports,
              "passed": sum(r["pass"] for r in reports), "total": len(reports)}
    (OUT / "agentic.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if MODE == "quality-normal":
    quality()
elif MODE == "quality-engineered":
    quality(engineered=True)
elif MODE == "quality-thinking":
    quality(thinking=True)
elif MODE == "json-tool-normal":
    json_and_tool()
elif MODE == "json-tool-engineered":
    json_and_tool(engineered=True)
elif MODE == "agentic":
    agentic()
else:
    raise SystemExit(f"unknown mode: {MODE}")
