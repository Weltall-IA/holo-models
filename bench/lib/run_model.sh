#!/bin/bash
set -u
ROOT=${ROOT:-/home/alpha/Playstoria/models}
OUT=${OUT:-$ROOT/bench/benchmarks/run}
LOG=${LOG:-$OUT/pipeline.log}
ENGINE=/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin
VENV=/home/alpha/tmp/holoplay-venvs/humaneval-venv/bin/python

say(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

wait_file(){ while [ ! -s "$1" ]; do sleep 30; done; }

MODEL_PID=""
stop(){ [ -n "$MODEL_PID" ] && kill "$MODEL_PID" 2>/dev/null || true; [ -n "$MODEL_PID" ] && wait "$MODEL_PID" 2>/dev/null || true; MODEL_PID=""; fuser -k 8081/tcp 2>/dev/null || true; }
trap 'stop' EXIT INT TERM

start(){ local file=$1 dir=$2; for ngl in 99 95 90 85 80 75 70 65 63 60 55; do stop; mkdir -p "$dir"; echo running > "$dir/status.log"; nohup env LD_LIBRARY_PATH=$ENGINE "$ENGINE/llama-server" -m "$file" -c 4096 -b 128 -ub 64 -t 6 -np 1 -ngl "$ngl" -fa on -ctk q4_0 -ctv q4_0 --reasoning off --jinja --host 127.0.0.1 --port 8081 > "$dir/server.log" 2>&1 & MODEL_PID=$!; for i in $(seq 1 120); do curl -s --max-time 3 http://127.0.0.1:8081/health 2>/dev/null | grep -q '"status":"ok"' && { echo selected_ngl=$ngl > "$dir/ngl.txt"; return 0; }; kill -0 "$MODEL_PID" 2>/dev/null || break; sleep 2; done; done; return 1; }

tool(){ "$VENV" - <<'PY'
import json,urllib.request
b={"messages":[{"role":"user","content":"Call add_numbers with a=2 and b=3. Return only the tool call."}],"tools":[{"type":"function","function":{"name":"add_numbers","description":"Add numbers","parameters":{"type":"object","properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"]}}}],"tool_choice":{"type":"function","function":{"name":"add_numbers"}},"temperature":0,"max_tokens":128}
r=json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8081/v1/chat/completions",json.dumps(b).encode(),{"Content-Type":"application/json"}),timeout=120).read().decode())
print(json.dumps({"tool_calls": bool((r.get("choices") or [{}])[0].get("message",{}).get("tool_calls"))}))
PY
}

run_one(){ local name=$1 file=$2 g=fail e=fail c=fail; local dir="$OUT/$name"; mkdir -p "$dir"; say "==> $name: iniciando"; if ! start "$file" "$dir"; then echo server_failed > "$dir/status.log"; say "==> $name: server_failed"; return; fi; say "==> $name: server ok ($(cat "$dir/ngl.txt"))"; tool > "$dir/tool.json" 2>&1 || true; local t0=$(date +%s); local ro=0; [ -s "$dir/humaneval_gen.json" ] && ro=1; (cd "$ROOT/bench" && REFUSAL_ONLY=$ro "$VENV" benchmarks/coder-v1/scripts/generate.py "$name" http://127.0.0.1:8081/v1 "$dir") > "$dir/generate.log" 2>&1 && g=ok || true; (cd "$ROOT/bench" && "$VENV" benchmarks/coder-v1/scripts/evaluate.py "$name" "$dir") > "$dir/evaluate.log" 2>&1 && e=ok || true; (cd "$ROOT/bench" && "$VENV" benchmarks/coder-v1/scripts/classify_refusal.py "$name" "$dir") > "$dir/classify.log" 2>&1 && c=ok || true; local t1=$(date +%s); if [ "$g$e$c" = okokok ]; then echo "DONE $name: tempo $((t1-t0))s" >> "$dir/generate.log"; echo ok > "$dir/status.log"; say "==> $name: concluido"; else echo "g=$g e=$e c=$c" > "$dir/status.log"; say "==> $name: parcial/FALHA (g=$g e=$e c=$c)"; fi; stop; }

write_summary(){ local out=$1; shift; "$VENV" - "$out" "$@" <<'PY'
import json,sys,os
out=sys.argv[1]; models=sys.argv[2:]
rows=[]
for name in models:
    d=os.path.join(out,name)
    ev={}
    try: ev=json.load(open(os.path.join(d,"evaluate.log")))
    except Exception: pass
    rf={}
    try: rf=json.load(open(os.path.join(d,"refusal_summary.json")))
    except Exception: pass
    tool="CHECK"
    try:
        if json.load(open(os.path.join(d,"tool.json"))).get("tool_calls"): tool="PASS"
    except Exception: pass
    rows.append((name,ev,rf,tool))
lines=["# Engine","- deepgrove llama.cpp commit 8ce8ca6","","| Modelo | HE | HE+ | Refusal (40) | Tool |","|---|---:|---:|---:|---|"]
for name,ev,rf,tool in rows:
    he=f"{ev.get('pass_base','-')}/164 ({ev.get('pass_at_1_base',0)*100:.1f}%)" if ev else "-"
    hep=f"{ev.get('pass_plus','-')}/164 ({ev.get('pass_at_1_plus',0)*100:.1f}%)" if ev else "-"
    ref=f"R{rf.get('REFUSAL','-')}/H{rf.get('COMPLY_WITH_HEDGE','-')}/C{rf.get('COMPLY','-')}" if rf else "-"
    lines.append(f"| {name} | {he} | {hep} | {ref} | {tool} |")
open(os.path.join(out,"SUMMARY.md"),"w").write("\n".join(lines)+"\n")
PY
}
