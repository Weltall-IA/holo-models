import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from cases.coding import CODING_CASES, run_coding_eval
from cases.tools import TOOL_CASES, eval_t01, eval_t02, eval_t03, eval_t04, eval_t05
from cases.recovery import RECOVERY_CASES, RecoveryEnvironment
from cases.long_context import generate_long_context_retrieval_case, eval_long_context
from runner.server_manager import LlamaServerProcess
from runner.client import LlamaClient

TOOL_EVALUATORS = {
    "eval_t01": eval_t01,
    "eval_t02": eval_t02,
    "eval_t03": eval_t03,
    "eval_t04": eval_t04,
    "eval_t05": eval_t05
}

def run_phase2_for_model(model_info: dict, ctx_size: int, raw_file):
    print(f"\n=======================================================")
    print(f"Phase 2: {model_info['name']} @ CTX {ctx_size}")
    print(f"=======================================================")
    
    server = LlamaServerProcess(
        model_path=model_info["local_path"],
        ctx_size=ctx_size,
        port=8089,
        kv_cache_type="q4_0",
        flash_attn=True,
        ngl=999
    )
    
    try:
        server.start()
        server.warmup()
    except Exception as e:
        print(f"Fit Failure / OOM @ ctx {ctx_size} for {model_info['name']}: {e}")
        rec = {
            "model_id": model_info["id"],
            "model_name": model_info["name"],
            "quant": model_info["quant"],
            "phase": f"phase2_ctx_{ctx_size}",
            "ctx_size": ctx_size,
            "boot_success": False,
            "error": str(e),
            "fit_failure": 1
        }
        raw_file.write(json.dumps(rec) + "\n")
        raw_file.flush()
        return rec
        
    client = LlamaClient(base_url=server.base_url)
    seed = 42
    results = []
    
    # 1. Coding (C01..C06)
    for case in CODING_CASES:
        print(f"  Coding {case['id']}...", end=" ", flush=True)
        out = client.generate(
            messages=[{"role": "user", "content": case["prompt"]}],
            temperature=0.2,
            top_p=0.95,
            seed=seed,
            max_tokens=4096
        )
        eval_res = run_coding_eval(case, out["content"]) if out["success"] else {"success": 0, "stderr": out["error"]}
        rec = {
            "model_id": model_info["id"],
            "model_name": model_info["name"],
            "quant": model_info["quant"],
            "phase": f"phase2_ctx_{ctx_size}",
            "ctx_size": ctx_size,
            "case_id": case["id"],
            "category": "coding",
            "seed": seed,
            "success": eval_res["success"],
            "prompt_tokens": out["prompt_tokens"],
            "completion_tokens": out["completion_tokens"],
            "ttft": out["ttft"],
            "tok_per_sec": out["tok_per_sec"],
            "wall_time": out["wall_time"],
            "peak_vram_mib": server.update_peak_vram()
        }
        raw_file.write(json.dumps(rec) + "\n")
        raw_file.flush()
        results.append(rec)
        print(f"Success={rec['success']}")
        
    # 2. Tools (T01..T05)
    for case in TOOL_CASES:
        print(f"  Tools {case['id']}...", end=" ", flush=True)
        if case["type"] == "single_turn":
            out = client.generate(
                messages=list(case["messages"]),
                tools=case.get("tools"),
                temperature=0.2,
                top_p=0.95,
                seed=seed,
                max_tokens=2048
            )
            eval_fn = TOOL_EVALUATORS[case["evaluator"]]
            eval_res = eval_fn(out["tool_calls"], out["content"])
            rec = {
                "model_id": model_info["id"],
                "model_name": model_info["name"],
                "quant": model_info["quant"],
                "phase": f"phase2_ctx_{ctx_size}",
                "ctx_size": ctx_size,
                "case_id": case["id"],
                "category": "tools",
                "seed": seed,
                "success": eval_res["success"],
                "prompt_tokens": out["prompt_tokens"],
                "completion_tokens": out["completion_tokens"],
                "ttft": out["ttft"],
                "tok_per_sec": out["tok_per_sec"],
                "wall_time": out["wall_time"],
                "peak_vram_mib": server.update_peak_vram()
            }
        else: # multi_turn
            messages = list(case["messages"])
            tools = case.get("tools")
            mock_responses = case.get("mock_responses", {})
            total_tool_calls = []
            total_prompt_toks = 0
            total_comp_toks = 0
            total_time = 0.0
            total_ttft = 0.0
            
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
                if total_ttft == 0.0: total_ttft = out["ttft"]
                if out["tool_calls"]:
                    total_tool_calls.extend(out["tool_calls"])
                    messages.append({"role": "assistant", "content": out["content"], "tool_calls": out["tool_calls"]})
                    for tc in out["tool_calls"]:
                        fn = tc.get("function", {}).get("name")
                        messages.append({"role": "tool", "tool_call_id": tc.get("id", "call_0"), "content": json.dumps(mock_responses.get(fn, {}))})
                else:
                    messages.append({"role": "assistant", "content": out["content"]})
                    break
            eval_fn = TOOL_EVALUATORS[case["evaluator"]]
            eval_res = eval_fn(total_tool_calls, messages[-1].get("content", ""))
            rec = {
                "model_id": model_info["id"],
                "model_name": model_info["name"],
                "quant": model_info["quant"],
                "phase": f"phase2_ctx_{ctx_size}",
                "ctx_size": ctx_size,
                "case_id": case["id"],
                "category": "tools",
                "seed": seed,
                "success": eval_res["success"],
                "prompt_tokens": total_prompt_toks,
                "completion_tokens": total_comp_toks,
                "ttft": total_ttft,
                "tok_per_sec": round(total_comp_toks / max(0.001, total_time - total_ttft), 2),
                "wall_time": total_time,
                "peak_vram_mib": server.update_peak_vram()
            }
        raw_file.write(json.dumps(rec) + "\n")
        raw_file.flush()
        results.append(rec)
        print(f"Success={rec['success']}")
        
    # 3. Recovery (A01..A03)
    for case in RECOVERY_CASES:
        print(f"  Recovery {case['id']}...", end=" ", flush=True)
        env = RecoveryEnvironment(case["id"])
        messages = list(case["messages"])
        tools = case.get("tools")
        max_turns = case.get("max_turns", 5)
        total_prompt_toks = 0
        total_comp_toks = 0
        total_time = 0.0
        total_ttft = 0.0
        
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
            if total_ttft == 0.0: total_ttft = out["ttft"]
            if out["tool_calls"]:
                messages.append({"role": "assistant", "content": out["content"], "tool_calls": out["tool_calls"]})
                for tc in out["tool_calls"]:
                    fn = tc.get("function", {}).get("name")
                    try:
                        args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                    except:
                        args = {}
                    t_res = env.execute_tool(fn, args)
                    messages.append({"role": "tool", "tool_call_id": tc.get("id", "call_0"), "content": json.dumps(t_res)})
            else:
                messages.append({"role": "assistant", "content": out["content"]})
                break
        eval_res = env.evaluate(messages[-1].get("content", ""))
        rec = {
            "model_id": model_info["id"],
            "model_name": model_info["name"],
            "quant": model_info["quant"],
            "phase": f"phase2_ctx_{ctx_size}",
            "ctx_size": ctx_size,
            "case_id": case["id"],
            "category": "recovery",
            "seed": seed,
            "success": eval_res["success"],
            "prompt_tokens": total_prompt_toks,
            "completion_tokens": total_comp_toks,
            "ttft": total_ttft,
            "tok_per_sec": round(total_comp_toks / max(0.001, total_time - total_ttft), 2),
            "wall_time": total_time,
            "peak_vram_mib": server.update_peak_vram()
        }
        raw_file.write(json.dumps(rec) + "\n")
        raw_file.flush()
        results.append(rec)
        print(f"Success={rec['success']}")
        
    # 4. Long Context Retrieval Stress Case (L01)
    target_toks = 24000 if ctx_size == 32768 else 48000
    print(f"  Long Context Retrieval L01 (target doc ~{target_toks} tokens, evaluating on GPU ~30-60s)...", end=" ", flush=True)
    l_case = generate_long_context_retrieval_case(target_tokens=target_toks)
    out = client.generate(
        messages=[{"role": "user", "content": l_case["prompt"]}],
        temperature=0.2,
        top_p=0.95,
        seed=seed,
        max_tokens=1024
    )
    eval_res = eval_long_context(out["content"], l_case["expected"])
    rec = {
        "model_id": model_info["id"],
        "model_name": model_info["name"],
        "quant": model_info["quant"],
        "phase": f"phase2_ctx_{ctx_size}",
        "ctx_size": ctx_size,
        "case_id": "L01",
        "category": "long_context",
        "seed": seed,
        "success": eval_res["success"],
        "partial_score": eval_res["partial_score"],
        "matches": eval_res["matches"],
        "prompt_tokens": out["prompt_tokens"],
        "completion_tokens": out["completion_tokens"],
        "ttft": out["ttft"],
        "tok_per_sec": out["tok_per_sec"],
        "wall_time": out["wall_time"],
        "peak_vram_mib": server.update_peak_vram(),
        "error": eval_res["error"]
    }
    raw_file.write(json.dumps(rec) + "\n")
    raw_file.flush()
    results.append(rec)
    print(f"Success={rec['success']} (Matches: {eval_res['matches']}/5, TTFT={rec['ttft']}s, {rec['tok_per_sec']} t/s)")
    
    server.stop()
    
    summary = {
        "model_id": model_info["id"],
        "model_name": model_info["name"],
        "ctx_size": ctx_size,
        "boot_success": True,
        "fit_failure": 0,
        "total_passed": sum(r["success"] for r in results),
        "total_cases": len(results),
        "avg_tok_s": round(sum(r["tok_per_sec"] for r in results) / len(results), 2),
        "avg_ttft": round(sum(r["ttft"] for r in results) / len(results), 4),
        "peak_vram_mib": max(r["peak_vram_mib"] for r in results)
    }
    return summary
