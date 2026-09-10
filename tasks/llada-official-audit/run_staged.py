#!/usr/bin/env python3
"""Staged low-memory runner for official LLaDA-Image-Turbo-FP8.

FASE A: prompt encoding with ONLY tokenizer + text_encoder + queryformer + text_projection.
FASE B: diffusion with ONLY scheduler + transformer FP8 + VAE, using precomputed embeds.
Never loads the full stack simultaneously. No RealRebel/ComfyUI, no Q4/INT8.
"""
import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

# ---- hard thread + tmp guards (must be set before torch import) ----
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "8")
os.environ["TMPDIR"] = "/home/alpha/Playstoria/models/tasks/llada-official-audit/tmp"
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ["HF_HUB_CACHE"] = os.path.expanduser("~/.cache/huggingface")
Path("/home/alpha/Playstoria/models/tasks/llada-official-audit/tmp").mkdir(parents=True, exist_ok=True)

import torch

REPO_ROOT = Path("/home/alpha/Playstoria/models/tasks/llada-official-audit/LLaDA-Image")
sys.path.insert(0, str(REPO_ROOT))
AUDIT_DIR = Path("/home/alpha/Playstoria/models/tasks/llada-official-audit")
OUT_DIR = AUDIT_DIR / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

torch.set_num_threads(8)
torch.set_num_interop_threads(8)


def mem_snapshot(tag: str) -> dict:
    import psutil
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    gpu_used = gpu_free = -1
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"],
            text=True, timeout=10,
        ).strip().split(",")
        gpu_used, gpu_free = int(out[0]), int(out[1])
    except Exception:
        pass
    rss = psutil.Process().memory_info().rss / (1024 ** 3)
    snap = {
        "tag": tag, "rss_gib": round(rss, 2),
        "mem_available_gib": round(vm.available / (1024 ** 3), 2),
        "swap_used_gib": round(sm.used / (1024 ** 3), 2),
        "gpu_used_mib": gpu_used, "gpu_free_mib": gpu_free,
    }
    print(json.dumps(snap), flush=True)
    return snap


def phase_a_encode(model_dir: Path, prompt: str, do_cfg: bool, neg_prompt: str = "") -> dict:
    """Load ONLY text stack, encode, save embeds, free everything."""
    from transformers import AutoModel, AutoTokenizer
    from src.models import LLaDAImageQueryFormerModel, LLaDAImageTextProjectionModel

    t0 = time.time()
    mem_snapshot("phaseA_start")
    max_mem = {0: "8GiB", "cpu": "24GiB"}
    print("PhaseA: loading tokenizer...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_dir / "tokenizer", trust_remote_code=False)
    print("PhaseA: loading text_encoder (device_map=auto, max_memory cuda 12GiB)...", flush=True)
    text_encoder = AutoModel.from_pretrained(
        model_dir / "text_encoder", dtype=torch.bfloat16,
        trust_remote_code=True, device_map="auto", max_memory=max_mem,
    )
    print(f"PhaseA: text_encoder device map: {getattr(text_encoder, 'hf_device_map', 'n/a')}", flush=True)
    queryformer = LLaDAImageQueryFormerModel.from_pretrained(
        model_dir / "queryformer", torch_dtype=torch.bfloat16).to("cuda")
    text_projection = LLaDAImageTextProjectionModel.from_pretrained(
        model_dir / "text_projection", torch_dtype=torch.bfloat16).to("cuda")
    mem_snapshot("phaseA_loaded")

    # replicate official _encode_text
    def encode_one(p_list):
        formatted = [
            "<role>HUMAN</role> Generate an image.\n<role>ASSISTANT</role>\n<IMAGE1>"
            if p is None else f"<role>HUMAN</role> Generate an image: {p.strip()}\n<role>ASSISTANT</role>\n<IMAGE1>"
            for p in p_list
        ]
        toks = tokenizer(formatted, add_special_tokens=True, padding=True,
                         truncation=True, max_length=2048, return_tensors="pt")
        te_dev = text_encoder.device if hasattr(text_encoder, "device") else "cuda"
        input_ids = toks.input_ids.to(te_dev)
        attn = toks.attention_mask.to(te_dev).bool()
        inputs_embeds = text_encoder.get_input_embeddings()(input_ids)
        query_embeds = queryformer(
            inputs_embeds.to(device=queryformer.device, dtype=queryformer.dtype),
            attn.to(queryformer.device)).query_embeds.to(device=inputs_embeds.device, dtype=inputs_embeds.dtype)
        text_len = inputs_embeds.shape[1]
        inputs_embeds = torch.cat([inputs_embeds, query_embeds], dim=1)
        attn = torch.cat([attn, attn.new_ones(attn.shape[0], query_embeds.shape[1])], dim=1)
        position_ids = attn.long().cumsum(dim=1) - 1
        position_ids.masked_fill_(position_ids < 0, 0)
        mask_value = torch.finfo(inputs_embeds.dtype).min
        te_dev2 = inputs_embeds.device
        bmask = attn[:, None, None, :].expand(-1, 1, attn.shape[1], -1)
        bmask = torch.where(bmask, torch.zeros((), dtype=inputs_embeds.dtype, device=te_dev2),
                            torch.full((), mask_value, dtype=inputs_embeds.dtype, device=te_dev2))
        bmask[:, :, :text_len, text_len:] = mask_value
        hidden = text_encoder.model(inputs_embeds=inputs_embeds, attention_mask=bmask,
                                    position_ids=position_ids, return_dict=True).last_hidden_state
        proj = text_projection(hidden.to(device=text_projection.device, dtype=text_projection.dtype)).hidden_states
        return proj.cpu(), attn.cpu()

    with torch.no_grad():
        pos_emb, pos_mask = encode_one([prompt])
        neg_emb, neg_mask = (None, None)
        if do_cfg:
            neg_emb, neg_mask = encode_one([neg_prompt])

    out = {"pos_emb": pos_emb, "pos_mask": pos_mask, "neg_emb": neg_emb, "neg_mask": neg_mask}
    emb_path = OUT_DIR / "phaseA_embeds.pt"
    torch.save(out, emb_path)
    print(f"PhaseA: embeds saved to {emb_path} pos={tuple(pos_emb.shape)}", flush=True)

    del text_encoder, queryformer, text_projection, tokenizer, out, pos_emb, pos_mask, neg_emb, neg_mask
    gc.collect()
    torch.cuda.empty_cache()
    time.sleep(2)
    snap = mem_snapshot("phaseA_freed")
    return {"emb_path": str(emb_path), "elapsed_s": round(time.time() - t0, 1), "snap": snap}


@torch.no_grad()
def phase_b_diffuse(model_dir: Path, emb_path: str, seed: int, out_png: str,
                    steps: int = 4, guidance: float = 1.0, h: int = 1024, w: int = 1024,
                    transformer_dir: Path | None = None) -> dict:
    """Load ONLY scheduler+transformer+vae, run diffusion from precomputed embeds.

    NOTE (loader compat, math-preserving): the Turbo-FP8 transformer checkpoint was
    saved with diffusers 0.40.0.dev0 using quantization_config quant_method 'fp8',
    which no public diffusers (0.39.0 pinned, 0.40.0, 0.41.0.dev0 tested) recognizes,
    and its fused weight layout (to_qkv/w13) does not match the model code's split
    layout (to_q/to_k/to_v, w1/w3). Loading it without the author's internal fork
    would silently random-init weights. Therefore Phase B uses the official BF16
    Turbo transformer (same architecture/training, strictly higher precision) while
    Phase A embeddings come from the official FP8 text encoder. This isolates the
    suspect Q4 encoder variable without altering model math.
    """
    from diffusers.schedulers import FlowMatchEulerDiscreteScheduler
    from diffusers.models import AutoencoderKLFlux2
    from src.models import LLaDAImageTransformer2DModel
    from diffusers.utils.torch_utils import randn_tensor

    t0 = time.time()
    mem_snapshot("phaseB_start")
    tdir = transformer_dir or (model_dir / "transformer")
    print(f"PhaseB: transformer source dir: {tdir}", flush=True)
    sched = FlowMatchEulerDiscreteScheduler.from_pretrained(model_dir / "scheduler")
    # Upstream Turbo note: stochastic_sampling=false may produce sharper details.
    # Enforce explicitly and log (do not rely on repo default which is true).
    try:
        sched.config["stochastic_sampling"] = False
        sched.register_to_config(stochastic_sampling=False)
    except Exception as e:
        print(f"PhaseB: could not override stochastic_sampling: {e}", flush=True)
    stoch = sched.config.get("stochastic_sampling", "n/a")
    print(f"PhaseB: scheduler stochastic_sampling={stoch} (enforced false for Turbo)", flush=True)
    # GPU has ~12GB free (desktop holds ~3.7GB); 13GB BF16 transformer needs split.
    try:
        transformer = LLaDAImageTransformer2DModel.from_pretrained(
            tdir, torch_dtype=torch.bfloat16, device_map="auto",
            max_memory={0: "10GiB", "cpu": "26GiB"})
        print(f"PhaseB: transformer device_map={getattr(transformer, 'hf_device_map', 'n/a')}", flush=True)
    except Exception as e:
        print(f"PhaseB: device_map load failed ({e}), falling back to CPU", flush=True)
        transformer = LLaDAImageTransformer2DModel.from_pretrained(
            tdir, torch_dtype=torch.bfloat16).to("cpu")
    vae = AutoencoderKLFlux2.from_pretrained(model_dir / "vae", torch_dtype=torch.bfloat16).to("cuda")
    mem_snapshot("phaseB_loaded")
    print(f"PhaseB: transformer.device={transformer.device} vae.device={vae.device}", flush=True)

    data = torch.load(emb_path, map_location="cpu", weights_only=False)
    do_cfg = guidance > 1.0
    pos_emb, pos_mask = data["pos_emb"], data["pos_mask"]
    neg_emb, neg_mask = data["neg_emb"], data["neg_mask"]

    # Compute device is cuda:0; accelerate hooks stream split transformer layers.
    device, dtype = torch.device("cuda:0"), torch.bfloat16
    gen = torch.Generator("cuda").manual_seed(seed)
    in_ch = transformer.config.in_channels
    # latent_scale_factor = 16 for flux2 VAE (8*2)
    lsf = 16
    shape = (1, in_ch, h // lsf, w // lsf)
    latents = randn_tensor(shape, generator=gen, device=device, dtype=torch.float32).to(dtype).float()

    schedule_steps = steps + 1
    schedule = torch.linspace(0.001, 1.0, schedule_steps, dtype=torch.float64)[:-1]
    schedule = (1 - (1 - schedule ** 1.17) ** 0.8) ** 1.1
    sigmas = (1 - schedule).tolist()
    sched.set_timesteps(sigmas=sigmas, device=device)
    timesteps = sched.timesteps

    def to_dev(embeds, mask):
        feats = [e[m].to(device=device, dtype=dtype) for e, m in zip(embeds, mask.bool())]
        return feats

    cond = to_dev(pos_emb, pos_mask)
    if do_cfg:
        uncond = to_dev(neg_emb, neg_mask)
        cap_feats_all = cond + uncond
    else:
        cap_feats_all = cond

    peak_vram = 0
    import subprocess
    with torch.no_grad():
        for si, ts in enumerate(timesteps):
            t0s = time.time()
            lin = torch.cat([latents, latents], dim=0) if do_cfg else latents
            llist = [l.unsqueeze(1).to(dtype) for l in lin]
            mts = (ts / sched.config.num_train_timesteps).expand(lin.shape[0]).to(dtype)
            out = transformer(x=llist, t=mts, cap_feats=cap_feats_all,
                              glm_cap_feats=None, source_latents=None).sample
            out = -torch.stack(out, dim=0).squeeze(2).float()
            if do_cfg:
                co, uo = out.chunk(2)
                out = uo + guidance * (co - uo)
            latents = sched.step(out, ts, latents, return_dict=False)[0]
            try:
                gu = int(subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    text=True, timeout=10).strip().splitlines()[0])
                peak_vram = max(peak_vram, gu)
            except Exception:
                pass
            print(f"PhaseB: step {si+1}/{len(timesteps)} {time.time()-t0s:.1f}s", flush=True)

    # Free transformer VRAM before VAE decode (memory management only; math unchanged).
    # Official code keeps both resident (assumes large GPU); staged runner releases it.
    try:
        transformer.to("cpu")
    except Exception as e:
        print(f"PhaseB: transformer to cpu: {e}", flush=True)
    del transformer
    gc.collect()
    torch.cuda.empty_cache()
    mem_snapshot("phaseB_transformer_freed")
    latents = latents.to(device=vae.device, dtype=vae.dtype)
    # exact official order: denorm on patchified latents, then unpatchify, then decode
    latent_mean = vae.bn.running_mean.view(1, -1, 1, 1).to(latents)
    latent_std = torch.sqrt(vae.bn.running_var.view(1, -1, 1, 1) + vae.config.batch_norm_eps).to(latents)
    latents = latents * latent_std + latent_mean
    B, C, H, W = latents.shape
    lat = latents.reshape(B, C // 4, 2, 2, H, W).permute(0, 1, 4, 2, 5, 3).reshape(B, C // 4, H * 2, W * 2)
    img = vae.decode(lat, return_dict=False)[0]
    from diffusers.image_processor import VaeImageProcessor
    proc = VaeImageProcessor(vae_scale_factor=16)
    pil = proc.postprocess(img, output_type="pil")[0]
    pil.save(out_png)
    print(f"PhaseB: saved {out_png}", flush=True)
    elapsed = round(time.time() - t0, 1)
    snap = mem_snapshot("phaseB_done")
    return {"elapsed_s": elapsed, "peak_vram_mib": peak_vram, "snap": snap, "out": out_png}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--seed", type=int, default=63001)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--guidance", type=float, default=1.0)
    ap.add_argument("--neg", default="")
    ap.add_argument("--phase", choices=["A", "B", "AB"], default="AB")
    ap.add_argument("--emb", default="")
    ap.add_argument("--transformer-dir", default="")
    args = ap.parse_args()
    md = Path(args.model_dir)
    if args.phase in ("A", "AB"):
        do_cfg = args.guidance > 1.0
        r = phase_a_encode(md, args.prompt, do_cfg, args.neg)
        print("PHASE_A_RESULT " + json.dumps(r))
        emb = r["emb_path"]
    else:
        emb = args.emb
    if args.phase in ("B", "AB"):
        tdir = Path(args.transformer_dir) if args.transformer_dir else None
        r = phase_b_diffuse(md, emb, args.seed, args.out, steps=args.steps,
                            guidance=args.guidance, transformer_dir=tdir)
        print("PHASE_B_RESULT " + json.dumps(r))
