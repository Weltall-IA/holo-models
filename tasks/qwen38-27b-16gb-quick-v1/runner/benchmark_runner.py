import json
import os
import sys
import time
from datetime import datetime

# Adjust paths to import local cases and runner modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from cases.coding import CODING_CASES, run_coding_eval
from cases.tools import TOOL_CASES, eval_t01, eval_t02, eval_t03, eval_t04, eval_t05
from cases.recovery import RECOVERY_CASES, RecoveryEnvironment
from cases.reasoning import REASONING_CASES, eval_r01, eval_r02, eval_r03
from cases.non_refusal import NON_REFUSAL_CASES, eval_u01, eval_u02, eval_u03
from runner.server_manager import LlamaServerProcess
from runner.client import LlamaClient

TOOL_EVALUATORS = {
    "eval_t01": eval_t01,
    "eval_t02": eval_t02,
    "eval_t03": eval_t03,
    "eval_t04": eval_t04,
    "eval_t05": eval_t05
}

REASONING_EVALUATORS = {
    "eval_r01": eval_r01,
    "eval_r02": eval_r02,
    "eval_r03": eval_r03
}

NON_REFUSAL_EVALUATORS = {
    "eval_u01": eval_u01,
    "eval_u02": eval_u02,
    "eval_u03": eval_u03
}

def run_single_attempt(client: LlamaClient, server: LlamaServerProcess, case: dict, category: str, seed: int) -> dict:
    case_id = case["id"]
    
    res_record = {
        "case_id": case_id,
        "case_name": case.get("name", ""),
        "category": category,
        "seed": seed,
        "success": 0,
        "refusal": 0,
        "invalid_tool_schema": 0,
        "wrong_tool": 0,
        "tool_call_count": 0,
        "retry_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "ttft": 0.0,
        "tok_per_sec": 0.0,
        "wall_time": 0.0,
        "peak_vram_mib": server.peak_vram,
        "error": None,
        "response_excerpt": ""
    }

    try:
        server.ensure_alive()
    except Exception as e:
        res_record["error"] = f"Server dead and failed restart: {e}"
        return res_record

    server.update_peak_vram()
    
    if category == "coding":
        messages = [{"role": "user", "content": case["prompt"]}]
        out = client.generate(
            messages=messages,
            temperature=0.2,
            top_p=0.95,
            seed=seed,
            max_tokens=4096
        )
        res_record["prompt_tokens"] = out["prompt_tokens"]
        res_record["completion_tokens"] = out["completion_tokens"]
        res_record["ttft"] = out["ttft"]
        res_record["tok_per_sec"] = out["tok_per_sec"]
        res_record["wall_time"] = out["wall_time"]
        res_record["response_excerpt"] = out["content"][:300]
        
        if not out["success"]:
            res_record["error"] = out["error"]
            return res_record
            
        eval_res = run_coding_eval(case, out["content"])
        res_record["success"] = eval_res["success"]
        if eval_res["success"] == 0:
            res_record["error"] = eval_res["stderr"] or eval_res["stdout"]
            
    elif category == "tools":
        if case["type"] == "single_turn":
            messages = list(case["messages"])
            tools = case.get("tools")
            out = client.generate(
                messages=messages,
                tools=tools,
                temperature=0.2,
                top_p=0.95,
                seed=seed,
                max_tokens=2048
            )
            res_record["prompt_tokens"] = out["prompt_tokens"]
            res_record["completion_tokens"] = out["completion_tokens"]
            res_record["ttft"] = out["ttft"]
            res_record["tok_per_sec"] = out["tok_per_sec"]
            res_record["wall_time"] = out["wall_time"]
            res_record["tool_call_count"] = len(out["tool_calls"])
            res_record["response_excerpt"] = (out["content"] or str(out["tool_calls"]))[:300]
            
            eval_fn = TOOL_EVALUATORS[case["evaluator"]]
            eval_res = eval_fn(out["tool_calls"], out["content"])
            res_record["success"] = eval_res["success"]
            res_record["error"] = eval_res["error"]
            if "Invalid JSON" in str(eval_res["error"]):
                res_record["invalid_tool_schema"] = 1
            if "Wrong tool" in str(eval_res["error"]):
                res_record["wrong_tool"] = 1
                
        elif case["type"] == "multi_turn":
            messages = list(case["messages"])
            tools = case.get("tools")
            mock_responses = case.get("mock_responses", {})
            total_tool_calls = []
            total_prompt_toks = 0
            total_comp_toks = 0
            total_ttft = 0.0
            total_time = 0.0
            
            for turn in range(4):
                out = client.generate(
                    messages=messages,
                    tools=tools,
                    temperature=0.2,
                    top_p=0.95,
                    seed=seed,
                    max_tokens=2048
                )
                total_prompt_toks += out["prompt_tokens"]
                total_comp_toks += out["completion_tokens"]
                total_time += out["wall_time"]
                if total_ttft == 0.0:
                    total_ttft = out["ttft"]
                    
                if out["tool_calls"]:
                    total_tool_calls.extend(out["tool_calls"])
                    messages.append({
                        "role": "assistant",
                        "content": out["content"],
                        "tool_calls": out["tool_calls"]
                    })
                    for tc in out["tool_calls"]:
                        fn_name = tc.get("function", {}).get("name")
                        resp_data = mock_responses.get(fn_name, {"status": "ok"})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", "call_0"),
                            "content": json.dumps(resp_data)
                        })
                else:
                    messages.append({"role": "assistant", "content": out["content"]})
                    break
                    
            res_record["prompt_tokens"] = total_prompt_toks
            res_record["completion_tokens"] = total_comp_toks
            res_record["ttft"] = total_ttft
            res_record["tok_per_sec"] = round(total_comp_toks / max(0.001, total_time - total_ttft), 2)
            res_record["wall_time"] = round(total_time, 4)
            res_record["tool_call_count"] = len(total_tool_calls)
            
            eval_fn = TOOL_EVALUATORS[case["evaluator"]]
            eval_res = eval_fn(total_tool_calls, messages[-1].get("content", ""))
            res_record["success"] = eval_res["success"]
            res_record["error"] = eval_res["error"]
            if "Forbidden tool" in str(eval_res["error"]) or "Wrong" in str(eval_res["error"]):
                res_record["wrong_tool"] = 1
                
    elif category == "recovery":
        env = RecoveryEnvironment(case_id)
        messages = list(case["messages"])
        tools = case.get("tools")
        max_turns = case.get("max_turns", 5)
        
        total_tool_calls = 0
        total_prompt_toks = 0
        total_comp_toks = 0
        total_ttft = 0.0
        total_time = 0.0
        retries = 0
        
        for turn in range(max_turns):
            out = client.generate(
                messages=messages,
                tools=tools,
                temperature=0.2,
                top_p=0.95,
                seed=seed,
                max_tokens=2048
            )
            total_prompt_toks += out["prompt_tokens"]
            total_comp_toks += out["completion_tokens"]
            total_time += out["wall_time"]
            if total_ttft == 0.0:
                total_ttft = out["ttft"]
                
            if out["tool_calls"]:
                total_tool_calls += len(out["tool_calls"])
                messages.append({
                    "role": "assistant",
                    "content": out["content"],
                    "tool_calls": out["tool_calls"]
                })
                for tc in out["tool_calls"]:
                    fn_name = tc.get("function", {}).get("name")
                    args_str = tc.get("function", {}).get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except Exception:
                        args = {}
                        res_record["invalid_tool_schema"] = 1
                        
                    tool_res = env.execute_tool(fn_name, args)
                    if "error" in tool_res or tool_res.get("status") == "error" or tool_res.get("status") == "failed":
                        retries += 1
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", "call_0"),
                        "content": json.dumps(tool_res)
                    })
            else:
                messages.append({"role": "assistant", "content": out["content"]})
                break
                
        res_record["prompt_tokens"] = total_prompt_toks
        res_record["completion_tokens"] = total_comp_toks
        res_record["ttft"] = total_ttft
        res_record["tok_per_sec"] = round(total_comp_toks / max(0.001, total_time - total_ttft), 2)
        res_record["wall_time"] = round(total_time, 4)
        res_record["tool_call_count"] = total_tool_calls
        res_record["retry_count"] = retries
        res_record["response_excerpt"] = messages[-1].get("content", "")[:300]
        
        eval_res = env.evaluate(messages[-1].get("content", ""))
        res_record["success"] = eval_res["success"]
        res_record["error"] = eval_res["error"]
        
    elif category == "reasoning":
        messages = [{"role": "user", "content": case["prompt"]}]
        out = client.generate(
            messages=messages,
            temperature=0.2,
            top_p=0.95,
            seed=seed,
            max_tokens=2048
        )
        res_record["prompt_tokens"] = out["prompt_tokens"]
        res_record["completion_tokens"] = out["completion_tokens"]
        res_record["ttft"] = out["ttft"]
        res_record["tok_per_sec"] = out["tok_per_sec"]
        res_record["wall_time"] = out["wall_time"]
        res_record["response_excerpt"] = out["content"][:300]
        
        eval_fn = REASONING_EVALUATORS[case["evaluator"]]
        eval_res = eval_fn(out["content"])
        res_record["success"] = eval_res["success"]
        res_record["error"] = eval_res["error"]
        
    elif category == "non_refusal":
        messages = [{"role": "user", "content": case["prompt"]}]
        out = client.generate(
            messages=messages,
            temperature=0.2,
            top_p=0.95,
            seed=seed,
            max_tokens=2048
        )
        res_record["prompt_tokens"] = out["prompt_tokens"]
        res_record["completion_tokens"] = out["completion_tokens"]
        res_record["ttft"] = out["ttft"]
        res_record["tok_per_sec"] = out["tok_per_sec"]
        res_record["wall_time"] = out["wall_time"]
        res_record["response_excerpt"] = out["content"][:300]
        
        eval_fn = NON_REFUSAL_EVALUATORS[case["evaluator"]]
        eval_res = eval_fn(out["content"])
        res_record["success"] = eval_res["success"]
        res_record["refusal"] = eval_res.get("refusal", 0)
        res_record["error"] = eval_res["error"]
        
    server.update_peak_vram()
    res_record["peak_vram_mib"] = server.peak_vram
    return res_record

def run_round1():
    models_file = os.path.join(BASE_DIR, "models.json")
    with open(models_file, "r") as f:
        models = json.load(f)
        
    raw_results_file = os.path.join(BASE_DIR, "results", "raw.jsonl")
    raw_file = open(raw_results_file, "a", encoding="utf-8")
    
    seeds = [42, 1337]
    summary_by_model = {}
    
    for m in models:
        print(f"\n=======================================================")
        print(f"Starting Round 1 Evaluation for Model: {m['name']} ({m['id']})")
        print(f"Path: {m['local_path']}")
        print(f"=======================================================")
        
        server = LlamaServerProcess(
            model_path=m["local_path"],
            ctx_size=16384,
            port=8089,
            kv_cache_type="q4_0",
            flash_attn=True,
            ngl=999
        )
        
        try:
            server.start()
            server.warmup()
        except Exception as e:
            print(f"CRITICAL: Failed to boot model {m['name']}: {e}")
            summary_by_model[m["id"]] = {
                "model_id": m["id"],
                "name": m["name"],
                "quant": m["quant"],
                "boot_success": False,
                "error": str(e)
            }
            continue
            
        client = LlamaClient(base_url=server.base_url)
        model_records = []
        
        # 1. Coding (C01..C06)
        for case in CODING_CASES:
            for s in seeds:
                print(f"  Running Coding {case['id']} (seed {s})...", end=" ", flush=True)
                rec = run_single_attempt(client, server, case, "coding", s)
                rec["model_id"] = m["id"]
                rec["model_name"] = m["name"]
                rec["quant"] = m["quant"]
                rec["phase"] = "round_1"
                raw_file.write(json.dumps(rec) + "\n")
                raw_file.flush()
                model_records.append(rec)
                print(f"Success={rec['success']} ({rec['tok_per_sec']} t/s, TTFT={rec['ttft']}s)")
                
        # 2. Tools (T01..T05)
        for case in TOOL_CASES:
            for s in seeds:
                print(f"  Running Tools {case['id']} (seed {s})...", end=" ", flush=True)
                rec = run_single_attempt(client, server, case, "tools", s)
                rec["model_id"] = m["id"]
                rec["model_name"] = m["name"]
                rec["quant"] = m["quant"]
                rec["phase"] = "round_1"
                raw_file.write(json.dumps(rec) + "\n")
                raw_file.flush()
                model_records.append(rec)
                print(f"Success={rec['success']} ({rec['tok_per_sec']} t/s, TTFT={rec['ttft']}s)")
                
        # 3. Recovery (A01..A03)
        for case in RECOVERY_CASES:
            for s in seeds:
                print(f"  Running Recovery {case['id']} (seed {s})...", end=" ", flush=True)
                rec = run_single_attempt(client, server, case, "recovery", s)
                rec["model_id"] = m["id"]
                rec["model_name"] = m["name"]
                rec["quant"] = m["quant"]
                rec["phase"] = "round_1"
                raw_file.write(json.dumps(rec) + "\n")
                raw_file.flush()
                model_records.append(rec)
                print(f"Success={rec['success']} ({rec['tok_per_sec']} t/s, TTFT={rec['ttft']}s)")
                
        # 4. Reasoning (R01..R03)
        for case in REASONING_CASES:
            for s in seeds:
                print(f"  Running Reasoning {case['id']} (seed {s})...", end=" ", flush=True)
                rec = run_single_attempt(client, server, case, "reasoning", s)
                rec["model_id"] = m["id"]
                rec["model_name"] = m["name"]
                rec["quant"] = m["quant"]
                rec["phase"] = "round_1"
                raw_file.write(json.dumps(rec) + "\n")
                raw_file.flush()
                model_records.append(rec)
                print(f"Success={rec['success']} ({rec['tok_per_sec']} t/s, TTFT={rec['ttft']}s)")
                
        # 5. Non-refusal (U01..U03)
        for case in NON_REFUSAL_CASES:
            for s in seeds:
                print(f"  Running Non-Refusal {case['id']} (seed {s})...", end=" ", flush=True)
                rec = run_single_attempt(client, server, case, "non_refusal", s)
                rec["model_id"] = m["id"]
                rec["model_name"] = m["name"]
                rec["quant"] = m["quant"]
                rec["phase"] = "round_1"
                raw_file.write(json.dumps(rec) + "\n")
                raw_file.flush()
                model_records.append(rec)
                print(f"Success={rec['success']} (Refusal={rec['refusal']}, {rec['tok_per_sec']} t/s)")
                
        # Stop server
        peak_vram = server.peak_vram
        idle_vram = server.idle_vram
        server.stop()
        
        # Calculate Category aggregates
        coding_recs = [r for r in model_records if r["category"] == "coding"]
        tools_recs = [r for r in model_records if r["category"] == "tools"]
        recov_recs = [r for r in model_records if r["category"] == "recovery"]
        reas_recs = [r for r in model_records if r["category"] == "reasoning"]
        non_ref_recs = [r for r in model_records if r["category"] == "non_refusal"]
        
        coding_score = sum(r["success"] for r in coding_recs) / len(coding_recs) if coding_recs else 0
        tools_score = sum(r["success"] for r in tools_recs) / len(tools_recs) if tools_recs else 0
        recovery_score = sum(r["success"] for r in recov_recs) / len(recov_recs) if recov_recs else 0
        reasoning_score = sum(r["success"] for r in reas_recs) / len(reas_recs) if reas_recs else 0
        non_refusal_score = sum(r["success"] for r in non_ref_recs) / len(non_ref_recs) if non_ref_recs else 0
        
        # Formula: 0.35*coding + 0.30*tools + 0.20*recovery + 0.10*reasoning + 0.05*non_refusal
        weighted_score = (
            0.35 * coding_score +
            0.30 * tools_score +
            0.20 * recovery_score +
            0.10 * reasoning_score +
            0.05 * non_refusal_score
        ) * 100.0
        
        total_tokens = sum(r["completion_tokens"] for r in model_records)
        avg_tok_s = sum(r["tok_per_sec"] for r in model_records) / len(model_records)
        avg_ttft = sum(r["ttft"] for r in model_records) / len(model_records)
        total_invalid_tools = sum(r["invalid_tool_schema"] for r in model_records)
        total_wrong_tools = sum(r["wrong_tool"] for r in model_records)
        total_retries = sum(r["retry_count"] for r in model_records)
        total_refusals = sum(r["refusal"] for r in model_records)
        
        summary_by_model[m["id"]] = {
            "model_id": m["id"],
            "name": m["name"],
            "quant": m["quant"],
            "boot_success": True,
            "weighted_score": round(weighted_score, 2),
            "coding_score": round(coding_score * 100, 2),
            "tools_score": round(tools_score * 100, 2),
            "recovery_score": round(recovery_score * 100, 2),
            "reasoning_score": round(reasoning_score * 100, 2),
            "non_refusal_score": round(non_refusal_score * 100, 2),
            "avg_tok_s": round(avg_tok_s, 2),
            "avg_ttft": round(avg_ttft, 4),
            "idle_vram_mib": idle_vram,
            "peak_vram_mib": peak_vram,
            "invalid_tool_schemas": total_invalid_tools,
            "wrong_tools": total_wrong_tools,
            "total_retries": total_retries,
            "total_refusals": total_refusals,
            "total_attempts": len(model_records),
            "total_passed": sum(r["success"] for r in model_records)
        }
        
    raw_file.close()
    
    # Save summary
    summary_path = os.path.join(BASE_DIR, "results", "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_by_model, f, indent=2)
        
    return summary_by_model

if __name__ == "__main__":
    run_round1()
