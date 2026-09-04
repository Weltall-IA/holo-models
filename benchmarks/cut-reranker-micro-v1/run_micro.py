from __future__ import annotations

import argparse, gc, hashlib, json, os, random, statistics, subprocess, sys, threading, time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RV2 = ROOT / "benchmarks/reranker-v2-unbiased"
DATA = ROOT / "benchmarks/embedding-v3/data/holo_fake_scenes_v3"
RANKINGS = ROOT / "benchmarks/embedding-v3/results/wemm-v1/embeddinggemma_300m/rankings.json"
OUT = HERE / "results/embeddinggemma-top50-v1"
TOPK, SEED, RESAMPLES = 50, 20260904, 10_000
sys.path.insert(0, str(RV2))
import run_benchmark as rv2  # noqa: E402


def jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def qgpu():
    fields = "utilization.gpu,memory.used,power.draw,temperature.gpu,clocks.sm"
    try:
        s = subprocess.check_output(
            ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits", "--id=0"],
            text=True, stderr=subprocess.DEVNULL, timeout=2,
        ).strip().splitlines()[0]
        vals = []
        for x in s.split(","):
            try: vals.append(float(x.strip()))
            except ValueError: vals.append(None)
        return dict(t=time.perf_counter(), util=vals[0], vram=vals[1], watts=vals[2], temp=vals[3], clock=vals[4])
    except Exception:
        return dict(t=time.perf_counter(), util=None, vram=None, watts=None, temp=None, clock=None)


def summarize(samples):
    def vals(k): return [float(x[k]) for x in samples if x.get(k) is not None]
    def avg(v): return statistics.fmean(v) if v else None
    def p95(v): return float(np.percentile(v, 95)) if v else None
    u, m, w, t, c = (vals(k) for k in ("util", "vram", "watts", "temp", "clock"))
    energy = None
    pw = [(x["t"], x["watts"]) for x in samples if x.get("watts") is not None]
    if len(pw) > 1:
        joules = sum((p0+p1)/2 * max(0, t1-t0) for (t0,p0),(t1,p1) in zip(pw,pw[1:]))
        energy = joules / 3600
    return {
        "samples": len(samples),
        "gpu_util_percent_avg": avg(u), "gpu_util_percent_p95": p95(u), "gpu_util_percent_max": max(u) if u else None,
        "gpu_memory_used_mib_avg": avg(m), "gpu_memory_used_mib_max": max(m) if m else None,
        "power_w_avg": avg(w), "power_w_p95": p95(w), "power_w_max": max(w) if w else None,
        "temperature_c_avg": avg(t), "temperature_c_max": max(t) if t else None,
        "sm_clock_mhz_avg": avg(c), "energy_wh_approx": energy,
    }


class Monitor:
    def __init__(self, interval=.5):
        self.interval, self.samples, self.stop_evt = interval, [], threading.Event()
        self.proc = psutil.Process(os.getpid())
    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True); self.thread.start()
    def _run(self):
        while not self.stop_evt.is_set():
            x = qgpu()
            try:
                x["rss_mib"] = self.proc.memory_info().rss / 2**20
            except psutil.Error:
                x["rss_mib"] = None
            self.samples.append(x); self.stop_evt.wait(self.interval)
    def stop(self):
        self.stop_evt.set(); self.thread.join(timeout=3); return self.samples


def idle_sample(seconds=2):
    xs=[]; end=time.perf_counter()+seconds
    while time.perf_counter()<end:
        xs.append(qgpu()); time.sleep(.5)
    return summarize(xs)


def build_data():
    corpus_rows, query_rows = jsonl(DATA/"corpus.jsonl"), jsonl(DATA/"queries.jsonl")
    rankings = json.loads(RANKINGS.read_text(encoding="utf-8"))
    if len(corpus_rows)!=600 or len(query_rows)!=150: raise RuntimeError("Expected frozen 600-doc/150-query scene corpus")
    corpus = {str(x["chunk_id"]): str(x["text"]) for x in corpus_rows}
    rows, frozen = [], {}
    for q in query_rows:
        qid=str(q["query_id"]); cand=[str(x) for x in rankings[qid][:TOPK]]
        if len(cand)!=TOPK or len(set(cand))!=TOPK: raise RuntimeError(f"{qid}: invalid top50")
        if set(cand)-set(corpus): raise RuntimeError(f"{qid}: unknown doc")
        frozen[qid]=cand
        rows.append({"query_id":qid,"query":q["query"],"relevant_doc_ids":q["relevant_chunk_ids"],
                     "candidate_ids":cand,"pipeline_candidate_ids":cand,"dataset":"holo_fake_scenes_v3",
                     "group_id":qid,"query_type":q.get("query_type","unknown")})
    prov={"first_stage":"embeddinggemma-300m QAT Q4_0 (existing measured rankings)","candidate_top_k":TOPK,
          "query_count":len(rows),"pair_count_per_model":len(rows)*TOPK,
          "hashes":{"corpus":sha(DATA/"corpus.jsonl"),"queries":sha(DATA/"queries.jsonl"),"rankings":sha(RANKINGS)}}
    return corpus, rows, frozen, prov


def agg_subset(perq, ids): return rv2.aggregate({q:perq[q] for q in ids})


def by_type(perq, rows):
    g=defaultdict(list)
    for r in rows: g[r["query_type"]].append(r["query_id"])
    return {k:{"query_count":len(v),"aggregate":agg_subset(perq,v)} for k,v in sorted(g.items())}


def paired(ettin, nemo, rows, metric):
    strata=defaultdict(list)
    for r in rows: strata[r["query_type"]].append(r["query_id"])
    obs=statistics.fmean(float(ettin[r["query_id"]][metric])-float(nemo[r["query_id"]][metric]) for r in rows)
    rng=random.Random(SEED); boots=[]
    for _ in range(RESAMPLES):
        ds=[]
        for ids in strata.values():
            for _ in ids:
                q=ids[rng.randrange(len(ids))]; ds.append(float(ettin[q][metric])-float(nemo[q][metric]))
        boots.append(statistics.fmean(ds))
    lo,hi=(float(x) for x in np.percentile(boots,[2.5,97.5]))
    verdict="ETTIN_WINS" if lo>0 else "NEMOTRON_WINS" if hi<0 else "INCONCLUSIVE"
    return {"direction":"ettin_minus_nemotron","metric":metric,"mean_delta":obs,"ci95":{"low":lo,"high":hi},
            "verdict":verdict,"resamples":RESAMPLES,"stratified_by":"query_type"}


def fmt(x,n=1): return "N/A" if x is None else f"{x:.{n}f}"


def report(final):
    b=final["embeddinggemma_top50_baseline"]; n=final["models"]["nemotron_1b_v2"]; e=final["models"]["ettin_400m"]
    lines=["# Cut reranker microbenchmark — EmbeddingGemma top-50","",
           "This is a small second-stage test for scene/cut search. Embeddings are not rerun.","",
           "## Protocol","",f"- 150 PT-BR scene queries, 600 chunks, fixed top-{TOPK} from the existing EmbeddingGemma run.",
           "- Only Nemotron 1B v2 and Ettin 400M rerank the exact same 50 candidates.",
           "- Primary: pipeline NDCG@10 over all queries. Paired CI95: 10,000 bootstrap resamples stratified by query_type.",
           "- Telemetry after one warmup: Torch VRAM, nvidia-smi VRAM/GPU%/watts/temp, latency, throughput and approximate energy.","",
           "## First-stage coverage","",f"EmbeddingGemma put a relevant cut in top-50 for **{b['queries_with_positive_in_top50']}/{b['query_count']} ({100*b['positive_coverage_rate']:.2f}%)** queries.","",
           "## Quality","","| Model | NDCG@10 | MRR@10 | MAP | Hit@1 | R@10 | R@20 |","|---|---:|---:|---:|---:|---:|---:|"]
    for label,m in (("Nemotron 1B v2",n),("Ettin 400M",e)):
        a=m["aggregate"]; lines.append(f"| {label} | {a['ndcg@10']:.4f} | {a['mrr@10']:.4f} | {a['map']:.4f} | {a['hit@1']:.4f} | {a['recall@10']:.4f} | {a['recall@20']:.4f} |")
    lines += ["","Conditional (only queries with a relevant cut already in top-50):","","| Model | NDCG@10 | MRR@10 | Hit@1 |","|---|---:|---:|---:|"]
    for label,m in (("Nemotron 1B v2",n),("Ettin 400M",e)):
        a=m["conditional_positive_in_top50"]; lines.append(f"| {label} | {a['ndcg@10']:.4f} | {a['mrr@10']:.4f} | {a['hit@1']:.4f} |")
    lines += ["","## Paired decision",""]
    for metric,p in final["paired_comparison"].items():
        lines.append(f"- Ettin − Nemotron {metric}: **{p['mean_delta']:+.4f}**, CI95 [{p['ci95']['low']:+.4f}, {p['ci95']['high']:+.4f}] → **{p['verdict']}**")
    lines += ["","## Efficiency","","| Model | Torch alloc/reserved peak MiB | nvidia-smi VRAM max MiB | GPU avg/p95/max % | Power avg/p95/max W | Energy Wh | p50/p95 s | q/s | pairs/s | total s | load s | temp max C |","|---|---:|---:|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for label,m in (("Nemotron 1B v2",n),("Ettin 400M",e)):
        x=m["efficiency"]; t=m["gpu_telemetry"]
        lines.append(f"| {label} | {x['peak_gpu_allocated_mib']:.0f}/{x['peak_gpu_reserved_mib']:.0f} | {fmt(t['gpu_memory_used_mib_max'],0)} | {fmt(t['gpu_util_percent_avg'])}/{fmt(t['gpu_util_percent_p95'])}/{fmt(t['gpu_util_percent_max'])} | {fmt(t['power_w_avg'])}/{fmt(t['power_w_p95'])}/{fmt(t['power_w_max'])} | {fmt(t['energy_wh_approx'],3)} | {x['latency_p50_s']:.3f}/{x['latency_p95_s']:.3f} | {x['queries_per_second']:.3f} | {m['pairs_per_second']:.1f} | {x['total_time_s']:.1f} | {m['model_load_time_s']:.2f} | {fmt(t['temperature_c_max'])} |")
    lines += ["","## By query type","","| Type | Nemotron NDCG | Ettin NDCG | Ettin−Nemo |","|---|---:|---:|---:|"]
    for typ in sorted(n["by_query_type"]):
        nv=n["by_query_type"][typ]["aggregate"]["ndcg@10"]; ev=e["by_query_type"][typ]["aggregate"]["ndcg@10"]
        lines.append(f"| {typ} | {nv:.4f} | {ev:.4f} | {ev-nv:+.4f} |")
    p=final["paired_comparison"]["ndcg@10"]
    lines += ["","## Decision","",f"**{p['verdict']}** on pipeline NDCG@10. This decision is only for `EmbeddingGemma top-50 → reranker` on the scene/cut corpus.","",
              "Whole-GPU nvidia-smi telemetry can include desktop activity; Torch allocated/reserved peaks are process-local.",""]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--device",default="cuda"); ap.add_argument("--cpu-threads",type=int,default=8)
    ap.add_argument("--nemotron-batch-size",type=int,default=16); ap.add_argument("--telemetry-interval",type=float,default=.5)
    ap.add_argument("--out-dir",type=Path,default=OUT); ap.add_argument("--force",action="store_true"); a=ap.parse_args()
    os.environ.setdefault("OMP_NUM_THREADS",str(a.cpu_threads)); os.environ.setdefault("MKL_NUM_THREADS",str(a.cpu_threads)); os.environ.setdefault("TOKENIZERS_PARALLELISM","false")
    import torch
    torch.set_num_threads(a.cpu_threads); random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)
    if a.device.startswith("cuda") and not torch.cuda.is_available(): raise RuntimeError("CUDA requested but unavailable")

    corpus,rows,frozen,prov=build_data(); a.out_dir.mkdir(parents=True,exist_ok=True)
    freeze={"benchmark_id":"cut-reranker-micro-v1","provenance":prov,"candidates":frozen}
    fp=a.out_dir/"candidates_top50.json"
    if fp.exists() and not a.force:
        old=json.loads(fp.read_text());
        if old.get("provenance",{}).get("hashes")!=prov["hashes"]: raise RuntimeError("Existing candidate freeze hash mismatch")
    else: fp.write_text(json.dumps(freeze,indent=2,ensure_ascii=False,sort_keys=True)+"\n")

    baseq={r["query_id"]:rv2.per_query_metrics(r["candidate_ids"],r["relevant_doc_ids"]) for r in rows}
    pos=[r["query_id"] for r in rows if set(r["candidate_ids"]) & set(r["relevant_doc_ids"])]
    baseline={"query_count":len(rows),"queries_with_positive_in_top50":len(pos),"positive_coverage_rate":len(pos)/len(rows),"aggregate":rv2.aggregate(baseq),"per_query":baseq}
    results={}
    for key in ("nemotron_1b_v2","ettin_400m"):
        path=a.out_dir/f"{key}.json"
        if path.exists() and not a.force: results[key]=json.loads(path.read_text()); print("LOAD",key); continue
        if torch.cuda.is_available(): torch.cuda.empty_cache(); torch.cuda.synchronize()
        idle=idle_sample(); source=rv2.resolve_source(key,{}); print("RUN",key,"source=",source)
        t0=time.perf_counter(); adapter=rv2.build_adapter(key,source,a.device,a.nemotron_batch_size); load=time.perf_counter()-t0
        try:
            r0=rows[0]; adapter.rank(r0["query"],[corpus[x] for x in r0["candidate_ids"]])
            if torch.cuda.is_available(): torch.cuda.synchronize()
            mon=Monitor(a.telemetry_interval); mon.start()
            try: m=rv2.run_model(key,adapter,corpus,rows,warmup=False)
            finally: samples=mon.stop()
            m["model_load_time_s"]=load; m["pairs_per_second"]=len(rows)*TOPK/m["efficiency"]["total_time_s"]
            m["gpu_telemetry"]=summarize(samples); m["gpu_idle_before"]=idle; m["by_query_type"]=by_type(m["per_query"],rows)
            m["conditional_positive_in_top50"]=agg_subset(m["per_query"],pos); m["benchmark_id"]="cut-reranker-micro-v1"; m["first_stage"]=prov; m["measured"]=True; m["projected"]=False
            path.write_text(json.dumps(m,indent=2,ensure_ascii=False,sort_keys=True)+"\n"); results[key]=m
            print(f"DONE {key} NDCG={m['aggregate']['ndcg@10']:.4f} MRR={m['aggregate']['mrr@10']:.4f} VRAM={m['efficiency']['peak_gpu_allocated_mib']:.0f}MiB p50={m['efficiency']['latency_p50_s']:.3f}s")
        finally:
            adapter.close(); del adapter; gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache(); torch.cuda.synchronize()
            time.sleep(2)

    pair={x:paired(results["ettin_400m"]["per_query"],results["nemotron_1b_v2"]["per_query"],rows,x) for x in ("ndcg@10","mrr@10")}
    final={"benchmark_id":"cut-reranker-micro-v1","provenance":prov,"embeddinggemma_top50_baseline":baseline,"models":results,"paired_comparison":pair,"runtime":rv2.runtime_metadata(),"measured":True,"projected":False}
    (a.out_dir/"comparison.json").write_text(json.dumps(final,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    (a.out_dir/"REPORT.md").write_text(report(final),encoding="utf-8")
    p=pair["ndcg@10"]; print(f"FINAL Ettin-Nemotron NDCG delta={p['mean_delta']:+.4f} CI95=[{p['ci95']['low']:+.4f},{p['ci95']['high']:+.4f}] {p['verdict']}")

if __name__=="__main__": main()
