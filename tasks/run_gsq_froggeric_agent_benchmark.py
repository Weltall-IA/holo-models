#!/usr/bin/env python3
import json
import os
import re
import signal
import statistics
import subprocess
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path("/home/alpha/Playstoria/models").resolve()
BENCH_DIR = ROOT / "benchmarks/gsq-froggeric-agent-tools-v1"
RESULTS_DIR = BENCH_DIR / "results"
PREFLIGHT_DIR = RESULTS_DIR / "gpu-preflight"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PREFLIGHT_DIR.mkdir(parents=True, exist_ok=True)

CASES_FILE = BENCH_DIR / "CASES.json"
CASES_DATA = json.loads(CASES_FILE.read_text(encoding="utf-8"))

LLAMA_BIN = str(Path.home() / ".local/bin/llama")
TARGET_MODEL = str(ROOT / "text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf")
FROGGERIC_TEMPLATE = str(ROOT / "text/froggeric-Qwen-Fixed-Chat-Templates-v22.5/chat_template.jinja")

PORT = 8197
CTX = 8192
THREADS = 8

def vram_mib():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None

def run_gpu_preflight(arm_name, max_retries=10, retry_delay=5):
    print(f"\n[Preflight] Checking Clean-GPU Gate for {arm_name}...")
    for attempt in range(1, max_retries + 1):
        smi_out = subprocess.check_output(["nvidia-smi"], text=True)
        pmon_out = subprocess.check_output(["nvidia-smi", "pmon", "-s", "u", "-c", "5", "-d", "1"], text=True)

        sm_counts = {}
        for line in pmon_out.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 9:
                pid = parts[1]
                sm_str = parts[3]
                cmd = parts[8] if len(parts) > 8 else ""
                if cmd in ("llama", "llama-server", "python", "python3"):
                    continue
                try:
                    sm_val = int(sm_str)
                    if sm_val >= 25:
                        sm_counts[pid] = sm_counts.get(pid, 0) + 1
                except ValueError:
                    pass

        heavy_pids = [pid for pid, count in sm_counts.items() if count >= 3]

        if not heavy_pids:
            print(f"[Preflight] Clean-GPU Gate PASSED for {arm_name}.")
            preflight_file = PREFLIGHT_DIR / f"{arm_name}.txt"
            preflight_file.write_text(f"=== NVIDIA-SMI ===\n{smi_out}\n\n=== PMON (5 samples) ===\n{pmon_out}\n\nClean Gate: PASSED (attempt {attempt})\n", encoding="utf-8")
            return {
                "passed": True,
                "attempt": attempt,
                "file": str(preflight_file.relative_to(ROOT)),
                "smi_snapshot": smi_out,
                "pmon_snapshot": pmon_out
            }

        print(f"[Preflight] Attempt {attempt}/{max_retries}: Heavy external GPU load detected on PID(s): {heavy_pids}. Waiting {retry_delay}s...")
        time.sleep(retry_delay)

    raise RuntimeError(f"Clean-GPU Gate FAILED for {arm_name} after {max_retries} attempts.")

def wait_health(timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                data = json.loads(r.read().decode())
                if data.get("status") == "ok":
                    return True
        except Exception:
            time.sleep(1)
    return False

def post_chat(payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    peak = vram_mib()
    stop = threading.Event()

    def sampler():
        nonlocal peak
        while not stop.wait(0.05):
            v = vram_mib()
            if v is not None and (peak is None or v > peak):
                peak = v

    th = threading.Thread(target=sampler, daemon=True)
    th.start()

    data = {}
    err_msg = None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        err_msg = f"HTTPError {e.code}: {err_body}"
        try:
            data = json.loads(err_body)
        except Exception:
            data = {"error": err_body}
    except Exception as e:
        err_msg = f"RequestError: {e}"
        data = {"error": str(e)}
    finally:
        stop.set()
        th.join(timeout=2)
    ended = time.perf_counter()

    choices = data.get("choices", [])
    message = choices[0].get("message", {}) if choices else {}
    if not message and err_msg:
        message = {"role": "assistant", "content": "", "error": err_msg}
    usage = data.get("usage", {})
    timings = data.get("timings", {})

    return {
        "message": message,
        "usage": usage,
        "timings": timings,
        "wall_time_s": round(ended - started, 4),
        "peak_vram_mib": peak,
        "raw_response": data,
        "error": err_msg
    }

def match_stub(case, tool_name, args):
    for stub in case.get("stubs", []):
        if stub["tool"] != tool_name:
            continue
        stub_args = stub.get("arguments", {})
        matches = True
        for arg_key, rule in stub_args.items():
            val = args.get(arg_key)
            if "equals" in rule:
                if val != rule["equals"]:
                    matches = False
                    break
            elif "contains_all_ci" in rule:
                if not isinstance(val, str):
                    matches = False
                    break
                for term in rule["contains_all_ci"]:
                    if term.lower() not in val.lower():
                        matches = False
                        break
                if not matches:
                    break
        if matches:
            res = stub["result"]
            return json.dumps(res, ensure_ascii=False) if not isinstance(res, str) else res, True
    return json.dumps(CASES_DATA["matching_semantics"]["default_unmatched_tool_result"]), False

def validate_rule(rule, val):
    if "equals" in rule:
        return val == rule["equals"]
    if "contains_all_ci" in rule:
        if not isinstance(val, str):
            return False
        return all(term.lower() in val.lower() for term in rule["contains_all_ci"])
    return False

def evaluate_run(case, turns_record, final_text):
    # turns_record: list of dicts with {"tool_calls": [...], "results": [...]}
    expected = case["expected"]
    expected_seq = expected.get("tool_sequence", [])
    arg_rules = expected.get("argument_rules", [])
    must_inc = expected.get("final_must_include", [])
    must_not_inc = expected.get("final_must_not_include", [])

    observed_tool_calls = []
    for t in turns_record:
        for tc in t.get("tool_calls", []):
            observed_tool_calls.append(tc)

    observed_seq = [tc["name"] for tc in observed_tool_calls]

    # 1. Tool selection & sequence (3 pts)
    seq_score = 0
    seq_reasons = []
    if case["id"] == "T04":
        if len(observed_seq) == 0:
            seq_score = 3
        else:
            seq_reasons.append(f"Expected 0 tool calls, but observed {observed_seq}")
    else:
        if observed_seq == expected_seq:
            seq_score = 3
        else:
            seq_reasons.append(f"Sequence mismatch: expected {expected_seq}, observed {observed_seq}")

    # 2. Arguments & schema (3 pts)
    arg_score = 0
    arg_reasons = []
    if case["id"] == "T04":
        if len(observed_tool_calls) == 0:
            arg_score = 3
        else:
            arg_reasons.append("Tool called when none expected")
    else:
        # Check argument rules against observed calls
        all_args_valid = True
        if len(observed_tool_calls) < len(arg_rules):
            all_args_valid = False
            arg_reasons.append(f"Fewer tool calls ({len(observed_tool_calls)}) than required rules ({len(arg_rules)})")
        else:
            for rule in arg_rules:
                idx = rule["index"]
                if idx >= len(observed_tool_calls):
                    all_args_valid = False
                    arg_reasons.append(f"Missing call at index {idx}")
                    continue
                tc = observed_tool_calls[idx]
                tc_name = tc["name"]
                tc_args = tc.get("args_parsed", {})
                if tc_name != rule["tool"]:
                    all_args_valid = False
                    arg_reasons.append(f"Call {idx}: tool name {tc_name} != expected {rule['tool']}")
                    continue
                for param_k, param_rule in rule.items():
                    if param_k in ("index", "tool"):
                        continue
                    param_val = tc_args.get(param_k)
                    if not validate_rule(param_rule, param_val):
                        all_args_valid = False
                        arg_reasons.append(f"Call {idx} param '{param_k}' failed rule {param_rule}: got {param_val}")

        if all_args_valid and seq_score == 3:
            arg_score = 3

    # 3. Final answer grounded (3 pts)
    final_score = 0
    final_reasons = []
    missing_inc = [item for item in must_inc if item not in final_text]
    present_not_inc = [item for item in must_not_inc if item in final_text]

    if not missing_inc and not present_not_inc:
        final_score = 3
    else:
        if missing_inc:
            final_reasons.append(f"Final answer missing required content: {missing_inc}")
        if present_not_inc:
            final_reasons.append(f"Final answer contains forbidden content: {present_not_inc}")

    # 4. Protocol hygiene (1 pt)
    hygiene_score = 0
    hygiene_reasons = []
    protocol_violation = False

    # Check for raw tool tags leaking into final content
    if "<tool_call>" in final_text or "</tool_call>" in final_text or "<|im_start|>tool" in final_text:
        protocol_violation = True
        hygiene_reasons.append("Raw tool tag leaked into final content")

    # Check for hallucinated tool names
    valid_tools = list(CASES_DATA["tool_catalog"].keys())
    for tc in observed_tool_calls:
        if tc["name"] not in valid_tools:
            protocol_violation = True
            hygiene_reasons.append(f"Hallucinated tool name: {tc['name']}")
        if not tc.get("args_valid_json", False):
            protocol_violation = True
            hygiene_reasons.append(f"Malformed JSON arguments in {tc['name']}")

    # Check for extra tool calls beyond expected
    if expected.get("forbid_extra_tool_calls", False):
        if len(observed_seq) > len(expected_seq):
            protocol_violation = True
            hygiene_reasons.append(f"Extra tool calls observed ({len(observed_seq)} > {len(expected_seq)})")

    if not protocol_violation:
        hygiene_score = 1

    total_score = seq_score + arg_score + final_score + hygiene_score
    strict_pass = (total_score == 10)

    loss_reasons = seq_reasons + arg_reasons + final_reasons + hygiene_reasons

    return {
        "strict_pass": strict_pass,
        "total_score": total_score,
        "component_scores": {
            "tool_sequence": seq_score,
            "arguments_schema": arg_score,
            "final_answer_grounded": final_score,
            "protocol_hygiene": hygiene_score
        },
        "observed_sequence": observed_seq,
        "loss_reasons": loss_reasons,
        "has_protocol_violation": protocol_violation
    }

def start_server(template_mode="native", log_fp=None):
    server_args = [
        LLAMA_BIN, "serve",
        "-m", TARGET_MODEL,
        "-ngl", "999",
        "-fa", "on",
        "--fit", "off",
        "-np", "1",
        "-t", str(THREADS),
        "-tb", str(THREADS),
        "-c", str(CTX),
        "-ctk", "q8_0",
        "-ctv", "q4_0",
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--jinja",
        "--reasoning-format", "deepseek",
        "--chat-template-kwargs", json.dumps({"enable_thinking": False, "reasoning_effort": "none", "tool_call_format": "json"}, separators=(",", ":")),
        "--reasoning", "off",
        "--no-ui"
    ]

    if template_mode == "froggeric":
        server_args.extend([
            "--chat-template-file", FROGGERIC_TEMPLATE
        ])

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{ROOT}/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH', '')}"

    proc = subprocess.Popen(server_args, stdout=log_fp, stderr=subprocess.STDOUT, env=env)
    return proc

def run_agent_arm(arm_id, arm_label, template_mode="native"):
    print(f"\n{'='*75}")
    print(f"{arm_id}: {arm_label}")
    print(f"{'='*75}")

    preflight_info = run_gpu_preflight(f"arm_{template_mode}")

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    log_filename = f"server-arm_{template_mode}.log"
    log_path = RESULTS_DIR / log_filename
    log_fp = open(log_path, "w", encoding="utf-8")
    proc = start_server(template_mode=template_mode, log_fp=log_fp)
    rows = []

    try:
        print(f"Waiting for server ({arm_id})...")
        if not wait_health(120):
            raise RuntimeError(f"Server failed to start for {arm_id}. Check {log_path}")

        print("Server healthy! Running warmup...")
        post_chat({
            "messages": [
                {"role": "system", "content": CASES_DATA["system_prompt"]},
                {"role": "user", "content": "Olá, você pode me ajudar?"}
            ],
            "temperature": 0.0,
            "seed": 9137,
            "max_tokens": 16
        })

        if template_mode == "native":
            out_jsonl = RESULTS_DIR / "NATIVE_RESULTS.jsonl"
        else:
            out_jsonl = RESULTS_DIR / "FROGGERIC_RESULTS.jsonl"

        if out_jsonl.exists():
            out_jsonl.unlink()

        for case in CASES_DATA["cases"]:
            cid = case["id"]
            title = case["title"]
            print(f"\n-> Executing {cid}: {title}...")

            # Build tools list for this case from catalog
            tools_for_case = [CASES_DATA["tool_catalog"][tname] for tname in case["tools"]]

            messages = [
                {"role": "system", "content": CASES_DATA["system_prompt"]},
                {"role": "user", "content": case["user"]}
            ]

            turns_record = []
            final_text = ""
            total_wall_s = 0.0
            peak_vram_arm = 0
            speeds = []
            rounds_count = 0

            for round_idx in range(1, 5): # max 4 rounds
                rounds_count += 1
                payload = {
                    "messages": messages,
                    "tools": tools_for_case,
                    "tool_choice": "auto",
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "seed": 9137,
                    "max_tokens": 384
                }

                res = post_chat(payload)
                msg = res["message"]
                timings = res.get("timings", {})
                speed = timings.get("predicted_per_second")
                if speed: speeds.append(speed)
                total_wall_s += res["wall_time_s"]
                if res["peak_vram_mib"] and res["peak_vram_mib"] > peak_vram_arm:
                    peak_vram_arm = res["peak_vram_mib"]

                if res.get("error"):
                    print(f"   [Round {round_idx}] Error during request: {res['error']}")
                    final_text = content or res["error"]
                    break

                tool_calls = msg.get("tool_calls", [])
                content = msg.get("content", "") or ""

                if not tool_calls:
                    final_text = content
                    print(f"   [Round {round_idx}] Final response received ({len(final_text)} chars): {final_text[:120].replace(chr(10), ' ')}...")
                    break

                # Handle tool calls
                print(f"   [Round {round_idx}] Assistant generated {len(tool_calls)} tool call(s):")
                tc_records = []
                messages.append(msg) # append assistant tool_calls message

                for tc in tool_calls:
                    func = tc.get("function", {})
                    fn_name = func.get("name", "")
                    raw_args = func.get("arguments", "")
                    tc_id = tc.get("id", f"call_{round_idx}")

                    args_parsed = {}
                    args_valid = True
                    try:
                        args_parsed = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        args_valid = False

                    stub_result_str, matched = match_stub(case, fn_name, args_parsed)
                    print(f"      Call: {fn_name}({raw_args}) -> Matched Stub: {matched} | Result Preview: {stub_result_str[:80]}...")

                    tc_records.append({
                        "id": tc_id,
                        "name": fn_name,
                        "raw_args": raw_args,
                        "args_parsed": args_parsed,
                        "args_valid_json": args_valid,
                        "stub_result": stub_result_str,
                        "matched_stub": matched
                    })

                    # Append tool response
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": fn_name,
                        "content": stub_result_str
                    })

                turns_record.append({
                    "round": round_idx,
                    "tool_calls": tc_records,
                    "timings": timings,
                    "wall_time_s": res["wall_time_s"]
                })

            eval_res = evaluate_run(case, turns_record, final_text)

            row = {
                "case_id": cid,
                "title": title,
                "arm": arm_id,
                "template_mode": template_mode,
                "strict_pass": eval_res["strict_pass"],
                "total_score": eval_res["total_score"],
                "component_scores": eval_res["component_scores"],
                "observed_sequence": eval_res["observed_sequence"],
                "loss_reasons": eval_res["loss_reasons"],
                "turns_record": turns_record,
                "final_text": final_text,
                "total_wall_s": round(total_wall_s, 4),
                "peak_vram_mib": peak_vram_arm,
                "rounds_count": rounds_count,
                "mean_tok_s": round(statistics.mean(speeds), 2) if speeds else None,
            }

            with out_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)

            status_str = "STRICT PASS (10/10)" if row["strict_pass"] else f"SCORE: {row['total_score']}/10"
            reasons_str = f" | Loss: {'; '.join(row['loss_reasons'])}" if row["loss_reasons"] else ""
            print(f"   => [{cid}] {status_str} | Seq: {row['observed_sequence']} | Time: {row['total_wall_s']:.2f}s{reasons_str}")

        return rows, preflight_info
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try: proc.kill()
            except: pass
        log_fp.close()
        subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
        time.sleep(2)

def generate_summary(native_rows, froggeric_rows, preflight_records):
    # Aggregates
    n_strict = sum(1 for r in native_rows if r["strict_pass"])
    f_strict = sum(1 for r in froggeric_rows if r["strict_pass"])

    n_total_score = sum(r["total_score"] for r in native_rows)
    f_total_score = sum(r["total_score"] for r in froggeric_rows)

    n_seq_acc = sum(r["component_scores"]["tool_sequence"] for r in native_rows) / (len(native_rows) * 3) * 100
    f_seq_acc = sum(r["component_scores"]["tool_sequence"] for r in froggeric_rows) / (len(froggeric_rows) * 3) * 100

    n_arg_acc = sum(r["component_scores"]["arguments_schema"] for r in native_rows) / (len(native_rows) * 3) * 100
    f_arg_acc = sum(r["component_scores"]["arguments_schema"] for r in froggeric_rows) / (len(froggeric_rows) * 3) * 100

    n_final_acc = sum(r["component_scores"]["final_answer_grounded"] for r in native_rows) / (len(native_rows) * 3) * 100
    f_final_acc = sum(r["component_scores"]["final_answer_grounded"] for r in froggeric_rows) / (len(froggeric_rows) * 3) * 100

    n_hygiene_acc = sum(r["component_scores"]["protocol_hygiene"] for r in native_rows) / (len(native_rows) * 1) * 100
    f_hygiene_acc = sum(r["component_scores"]["protocol_hygiene"] for r in froggeric_rows) / (len(froggeric_rows) * 1) * 100

    # T07 recovery
    n_t07 = next((r for r in native_rows if r["case_id"] == "T07"), None)
    f_t07 = next((r for r in froggeric_rows if r["case_id"] == "T07"), None)
    n_t07_recovery = "PASS (10/10)" if n_t07 and n_t07["strict_pass"] else f"SCORE {n_t07['total_score']}/10"
    f_t07_recovery = "PASS (10/10)" if f_t07 and f_t07["strict_pass"] else f"SCORE {f_t07['total_score']}/10"

    # Wall times & VRAM
    n_wall_total = sum(r["total_wall_s"] for r in native_rows)
    f_wall_total = sum(r["total_wall_s"] for r in froggeric_rows)
    n_peak_vram = max(r["peak_vram_mib"] for r in native_rows)
    f_peak_vram = max(r["peak_vram_mib"] for r in froggeric_rows)

    # Classification logic from SPEC:
    # - FROGGERIC_AGENT_CLEAR_WIN: Froggeric vence por >=2 STRICT PASS, ou por >=10 pontos no total sem aumentar violações de protocolo;
    # - FROGGERIC_AGENT_EDGE: Froggeric vence por 1 STRICT PASS ou 5–9 pontos sem aumentar violações;
    # - AGENT_PARITY: diferença <5 pontos e mesmo número de STRICT PASS;
    # - NATIVE_AGENT_EDGE: simétrico ao edge acima;
    # - NATIVE_AGENT_CLEAR_WIN: simétrico ao clear win acima;
    # - MIXED_AGENT_RESULT: direções opostas.
    pass_diff = f_strict - n_strict
    score_diff = f_total_score - n_total_score

    if pass_diff >= 2 or score_diff >= 10:
        classification = "FROGGERIC_AGENT_CLEAR_WIN"
    elif pass_diff == 1 or (5 <= score_diff <= 9):
        classification = "FROGGERIC_AGENT_EDGE"
    elif pass_diff == 0 and abs(score_diff) < 5:
        classification = "AGENT_PARITY"
    elif pass_diff == -1 or (-9 <= score_diff <= -5):
        classification = "NATIVE_AGENT_EDGE"
    elif pass_diff <= -2 or score_diff <= -10:
        classification = "NATIVE_AGENT_CLEAR_WIN"
    else:
        classification = "MIXED_AGENT_RESULT"

    lines = []
    lines.append("# GSQ Froggeric Agent / Tool-Calling Benchmark v1 — Summary\n")
    lines.append("## 1. Overview\n")
    lines.append("Direct side-by-side evaluation of **Tool-Calling & Agentic Multi-Turn Interaction** on `Qwen3.8-27B GSQ-RCO IQ2_S` comparing **Native GGUF Chat Template** vs **Froggeric v22.5** across 8 canonical cases.\n")
    lines.append(f"- **Target Model**: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`")
    lines.append(f"- **Froggeric Template**: `chat_template.jinja` (`4ea21db`, SHA256: `e57684ba...`, version: `qwen3.8-froggeric-v22.5`)")
    lines.append(f"- **Runtime**: `llama.cpp` build 10752, `-c 8192 -ngl 999 -fa on --fit off -ctk q8_0 -ctv q4_0`")
    lines.append(f"- **Tool Protocol**: OpenAI-compatible `/v1/chat/completions` with `tools`, `tool_choice=auto`, `tool_call_format=json`, deterministic sampling (`temp=0.0, top_p=1.0, seed=9137`).\n")

    lines.append("## 2. Aggregate Scorecard\n")
    lines.append("| Metric | Arm N (Native Template) | Arm F (Froggeric v22.5) | Delta (F vs N) |")
    lines.append("|---|:---:|:---:|:---:|")
    lines.append(f"| **STRICT PASS (/8)** | **{n_strict}/8** | **{f_strict}/8** | **{pass_diff:+d}** |")
    lines.append(f"| **Total Component Score (/80)** | **{n_total_score}/80** | **{f_total_score}/80** | **{score_diff:+d}** |")
    lines.append(f"| Tool Selection / Sequence Accuracy | {n_seq_acc:.1f}% | {f_seq_acc:.1f}% | {f_seq_acc - n_seq_acc:+.1f}% |")
    lines.append(f"| Arguments & Schema Accuracy | {n_arg_acc:.1f}% | {f_arg_acc:.1f}% | {f_arg_acc - n_arg_acc:+.1f}% |")
    lines.append(f"| Grounded Final Answer Accuracy | {n_final_acc:.1f}% | {f_final_acc:.1f}% | {f_final_acc - n_final_acc:+.1f}% |")
    lines.append(f"| Protocol Hygiene | {n_hygiene_acc:.1f}% | {f_hygiene_acc:.1f}% | {f_hygiene_acc - n_hygiene_acc:+.1f}% |")
    lines.append(f"| **T07 Error Recovery** | {n_t07_recovery} | {f_t07_recovery} | — |")
    lines.append(f"| Total Benchmark Wall Time | {n_wall_total:.2f} s | {f_wall_total:.2f} s | {f_wall_total - n_wall_total:+.2f} s |")
    lines.append(f"| Peak VRAM | {n_peak_vram} MiB | {f_peak_vram} MiB | {f_peak_vram - n_peak_vram:+d} MiB |")

    lines.append("\n## 3. Case-by-Case Side-by-Side Breakdown\n")
    lines.append("| Case | Title | Native Pass | Froggeric Pass | Native Score | Froggeric Score | Native Sequence | Froggeric Sequence | Loss Reasons (if any) |")
    lines.append("|---|---|:---:|:---:|:---:|:---:|---|---|---|")

    n_map = {r["case_id"]: r for r in native_rows}
    f_map = {r["case_id"]: r for r in froggeric_rows}

    for case in CASES_DATA["cases"]:
        cid = case["id"]
        title = case["title"]
        rn = n_map[cid]
        rf = f_map[cid]

        st_n = "PASS" if rn["strict_pass"] else "FAIL"
        st_f = "PASS" if rf["strict_pass"] else "FAIL"
        sc_n = f"{rn['total_score']}/10"
        sc_f = f"{rf['total_score']}/10"
        seq_n = " -> ".join(rn["observed_sequence"]) if rn["observed_sequence"] else "*(none)*"
        seq_f = " -> ".join(rf["observed_sequence"]) if rf["observed_sequence"] else "*(none)*"

        reasons = []
        if rn["loss_reasons"]:
            reasons.append(f"**Native**: {'; '.join(rn['loss_reasons'])}")
        if rf["loss_reasons"]:
            reasons.append(f"**Froggeric**: {'; '.join(rf['loss_reasons'])}")
        reasons_repr = "<br>".join(reasons) if reasons else "*None (Perfect 10/10)*"

        lines.append(f"| **{cid}** | `{title}` | **{st_n}** | **{st_f}** | {sc_n} | {sc_f} | `{seq_n}` | `{seq_f}` | {reasons_repr} |")

    lines.append("\n## 4. Final Classification\n")
    lines.append(f"**Classification**: `{classification}`\n")

    if classification == "AGENT_PARITY":
        lines.append("- Both Native and Froggeric v22.5 templates exhibit **functional parity** across all 8 agentic tool-calling tasks.")
    elif "FROGGERIC" in classification:
        lines.append("- Froggeric v22.5 demonstrated superior tool-calling and agentic behavior.")
    elif "NATIVE" in classification:
        lines.append("- The Native template demonstrated superior tool-calling and agentic behavior.")
    else:
        lines.append("- The benchmark produced mixed results across component metrics.")

    summary_text = "\n".join(lines) + "\n"
    (RESULTS_DIR / "SUMMARY.md").write_text(summary_text, encoding="utf-8")
    print(f"\nSummary successfully written to {RESULTS_DIR / 'SUMMARY.md'}")

    # Generate RUN_MANIFEST.json
    manifest = {
        "benchmark": "gsq-froggeric-agent-tools-v1",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target_model": {
            "path": TARGET_MODEL,
            "sha256": "16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb"
        },
        "froggeric_template": {
            "repo": "froggeric/Qwen-Fixed-Chat-Templates",
            "commit": "4ea21db90694e60d002500dae85ebff26e4b23ad",
            "sha256": "e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2",
            "internal_version": "qwen3.8-froggeric-v22.5",
            "path": FROGGERIC_TEMPLATE
        },
        "runtime": {
            "binary": LLAMA_BIN,
            "version": "0.3.0-dev (build 10752, commit b96806d96)"
        },
        "gpu": "NVIDIA GeForce RTX 5060 Ti 16 GB",
        "clean_gpu_preflight": preflight_records,
        "results": {
            "classification": classification,
            "native_strict_pass": n_strict,
            "froggeric_strict_pass": f_strict,
            "native_total_score": n_total_score,
            "froggeric_total_score": f_total_score,
            "native_wall_s": round(n_wall_total, 2),
            "froggeric_wall_s": round(f_wall_total, 2)
        }
    }
    (RESULTS_DIR / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest written to {RESULTS_DIR / 'RUN_MANIFEST.json'}")

def main():
    print("===========================================================================")
    print("STARTING GSQ FROGGERIC AGENT / TOOL-CALLING BENCHMARK v1 (16 RUNS)")
    print("===========================================================================")

    preflight_records = {}

    # Arm N (Native)
    native_rows, pf_n = run_agent_arm("Arm N", "GSQ Native Chat Template", template_mode="native")
    preflight_records["Arm N"] = {"label": "GSQ Native Chat Template", **pf_n}

    # Arm F (Froggeric v22.5)
    froggeric_rows, pf_f = run_agent_arm("Arm F", "GSQ + Froggeric v22.5 Chat Template", template_mode="froggeric")
    preflight_records["Arm F"] = {"label": "GSQ + Froggeric v22.5 Chat Template", **pf_f}

    # Generate summary & manifest
    generate_summary(native_rows, froggeric_rows, preflight_records)

    print("\nAll 16 agent runs and summaries completed successfully!")

if __name__ == "__main__":
    main()
