import json
import time
import requests

class LlamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8089"):
        self.base_url = base_url

    def generate(
        self,
        messages: list,
        tools: list = None,
        temperature: float = 0.2,
        top_p: float = 0.95,
        seed: int = 42,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> dict:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "seed": seed,
            "max_tokens": max_tokens,
            "stream": stream
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
            
        start_time = time.time()
        ttft = None
        full_content = ""
        tool_calls = []
        finish_reason = None
        data = {}
        
        try:
            res = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=180
            )
            res.raise_for_status()
            data = res.json()
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            full_content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            finish_reason = choice.get("finish_reason")
            
        except Exception as e:
            total_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "content": full_content,
                "tool_calls": tool_calls,
                "ttft": total_time,
                "wall_time": total_time,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "tok_per_sec": 0.0
            }
            
        total_time = time.time() - start_time
        timings = data.get("timings", {}) if isinstance(data, dict) else {}
        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Exact hardware speed and TTFT from llama.cpp engine
        if "predicted_per_second" in timings and timings["predicted_per_second"] is not None:
            tok_per_sec = float(timings["predicted_per_second"])
        else:
            decode_time = max(0.001, total_time - (ttft or 0))
            tok_per_sec = completion_tokens / decode_time if completion_tokens > 0 else 0.0
            
        if "prompt_ms" in timings and timings["prompt_ms"] is not None:
            ttft = float(timings["prompt_ms"]) / 1000.0
        else:
            ttft = total_time
            
        return {
            "success": True,
            "error": None,
            "content": full_content,
            "tool_calls": tool_calls,
            "finish_reason": finish_reason,
            "ttft": round(ttft, 4),
            "wall_time": round(total_time, 4),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tok_per_sec": round(tok_per_sec, 2)
        }
