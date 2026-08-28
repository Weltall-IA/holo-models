import random

def generate_long_context_retrieval_case(target_tokens: int = 25000):
    # Generates a large document with 20 distinct synthetic records scattered across filler text
    records = [
        {"id": f"REC_{i:03d}", "key": f"alpha_key_{i}", "value": f"VAL_SECRET_{i * 37 + 109}", "category": f"cat_{i % 5}"}
        for i in range(20)
    ]
    
    # 5 targets to query: near beginning (0, 3), middle (9, 11), end (17, 19)
    query_indices = [0, 4, 9, 14, 19]
    targets = [records[idx] for idx in query_indices]
    
    # Generate filler paragraphs
    filler_templates = [
        "In the ongoing development of distributed high-throughput database systems, consensus protocols play a critical role in ensuring partition tolerance and transactional serializability across divergent cluster topologies.",
        "Resource allocation in virtualized compute environments requires proactive predictive telemetry to mitigate thread starvation and latency jitter during peak load scenarios.",
        "Cryptographic key rotation policies dictate that ephemeral session descriptors be invalidated and purged from non-volatile storage immediately upon transaction finalization.",
        "System telemetry monitors memory fragmentation, cache hit ratios, and network socket buffer exhaustion across all active ingestion pipelines."
    ]
    
    # We build the document
    paragraphs = []
    # Calculate how many filler paragraphs per slot
    # Each paragraph is ~30 tokens. For 25k tokens, we need ~800 paragraphs.
    paras_per_record = target_tokens // (20 * 30)
    
    for i, rec in enumerate(records):
        for _ in range(paras_per_record):
            paragraphs.append(random.choice(filler_templates))
        paragraphs.append(f"[RECORD ENTRY: id={rec['id']}, key={rec['key']}, value={rec['value']}, category={rec['category']}]")
        
    for _ in range(paras_per_record):
        paragraphs.append(random.choice(filler_templates))
        
    doc_text = "\n\n".join(paragraphs)
    
    query_text = (
        "Based on the text above, find the exact values for the following 5 keys:\n"
        + "\n".join(f"- {t['key']}" for t in targets)
        + "\n\nReturn your answer as a JSON object mapping each key to its exact value, e.g. {\"alpha_key_0\": \"VAL_...\"}."
    )
    
    full_prompt = f"### REFERENCE DOCUMENT\n\n{doc_text}\n\n### INSTRUCTIONS\n\n{query_text}"
    
    expected = {t['key']: t['value'] for t in targets}
    
    return {
        "id": "L01",
        "name": "long_context_retrieval_20x5",
        "prompt": full_prompt,
        "expected": expected,
        "targets": targets
    }

def eval_long_context(response_text: str, expected: dict) -> dict:
    import json
    import re
    # Try parsing json
    cleaned = response_text.strip()
    match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        data = json.loads(cleaned)
    except Exception:
        data = {}
        
    matches = 0
    for k, v in expected.items():
        if data.get(k) == v or v in response_text:
            matches += 1
            
    success = 1 if matches == len(expected) else (matches / len(expected))
    return {
        "success": 1 if matches == len(expected) else 0,
        "partial_score": matches / len(expected),
        "matches": matches,
        "total": len(expected),
        "error": None if matches == len(expected) else f"Matched {matches}/{len(expected)} keys"
    }
