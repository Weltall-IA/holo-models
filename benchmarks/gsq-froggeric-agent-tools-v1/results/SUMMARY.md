# GSQ Froggeric Agent / Tool-Calling Benchmark v1 — Summary

## 1. Overview

Direct side-by-side evaluation of **Tool-Calling & Agentic Multi-Turn Interaction** on `Qwen3.8-27B GSQ-RCO IQ2_S` comparing **Native GGUF Chat Template** vs **Froggeric v22.5** across 8 canonical cases.

- **Target Model**: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- **Froggeric Template**: `chat_template.jinja` (`4ea21db`, SHA256: `e57684ba...`, version: `qwen3.8-froggeric-v22.5`)
- **Runtime**: llama.cpp build 10752, `-c 8192 -ngl 999 -fa on --fit off -ctk q8_0 -ctv q4_0`
- **Tool Protocol**: OpenAI-compatible `/v1/chat/completions` with `tools`, `tool_choice=auto`, `tool_call_format=json`, deterministic sampling (`temp=0.0, top_p=1.0, seed=9137`).

## 2. Aggregate Scorecard

| Metric | Arm N (Native Template) | Arm F (Froggeric v22.5) | Delta (F vs N) |
|---|:---:|:---:|:---:|
| **STRICT PASS (/8)** | **7/8** | **4/8** | **-3** |
| **Total Component Score (/80)** | **70/80** | **49/80** | **-21** |
| Tool Selection / Sequence Accuracy | 87.5% | 87.5% | +0.0% |
| Arguments & Schema Accuracy | 87.5% | 50.0% | -37.5% |
| Grounded Final Answer Accuracy | 87.5% | 50.0% | -37.5% |
| Protocol Hygiene | 87.5% | 50.0% | -37.5% |
| **T07 Error Recovery** | SCORE 0/10 | SCORE 0/10 | — |
| Total Benchmark Wall Time | 69.52 s | 113.32 s | +43.80 s |
| Peak VRAM | 11624 MiB | 11744 MiB | +120 MiB |

## 3. Case-by-Case Side-by-Side Breakdown

| Case | Title | Native Pass | Froggeric Pass | Native Score | Froggeric Score | Native Sequence | Froggeric Sequence | Loss Reasons (if any) |
|---|---|:---:|:---:|:---:|:---:|---|---|---|
| **T01** | `single_tool_exact_file` | **PASS** | **PASS** | 10/10 | 10/10 | `read_file` | `read_file` | *None (Perfect 10/10)* |
| **T02** | `choose_symbol_tool_over_text_search` | **PASS** | **PASS** | 10/10 | 10/10 | `find_symbol` | `find_symbol` | *None (Perfect 10/10)* |
| **T03** | `exact_schema_and_line_range` | **PASS** | **FAIL** | 10/10 | 3/10 | `read_file` | `read_file` | **Froggeric**: Call 0 param 'path' failed rule {'equals': 'src/config.py'}: got None; Call 0 param 'start_line' failed rule {'equals': 40}: got None; Call 0 param 'end_line' failed rule {'equals': 45}: got None; Final answer missing required content: ['30']; Raw tool tag leaked into final content; Malformed JSON arguments in read_file |
| **T04** | `do_not_call_tool_when_not_needed` | **PASS** | **PASS** | 10/10 | 10/10 | `*(none)*` | `*(none)*` | *None (Perfect 10/10)* |
| **T05** | `search_then_read_dependency` | **PASS** | **FAIL** | 10/10 | 3/10 | `search_repo -> read_file` | `search_repo -> read_file` | **Froggeric**: Call 1 param 'path' failed rule {'equals': 'src/settings/embedding.py'}: got None; Final answer missing required content: ['False']; Raw tool tag leaked into final content; Malformed JSON arguments in read_file |
| **T06** | `list_then_select_latest_then_read` | **PASS** | **FAIL** | 10/10 | 3/10 | `list_dir -> read_file` | `list_dir -> read_file` | **Froggeric**: Call 1 param 'path' failed rule {'equals': 'configs/agents/holo-2026-09-03.json'}: got None; Final answer missing required content: ['gemini-3.7-flash']; Raw tool tag leaked into final content; Malformed JSON arguments in read_file |
| **T07** | `recover_from_tool_error` | **FAIL** | **FAIL** | 0/10 | 0/10 | `read_file -> search_repo -> search_repo -> search_repo -> read_file -> read_file -> read_file -> read_file -> read_file -> read_file` | `read_file -> search_repo -> search_repo -> read_file` | **Native**: Sequence mismatch: expected ['read_file', 'search_repo', 'read_file'], observed ['read_file', 'search_repo', 'search_repo', 'search_repo', 'read_file', 'read_file', 'read_file', 'read_file', 'read_file', 'read_file']; Call 1 param 'query' failed rule {'contains_all_ci': ['deploy', 'timeout']}: got timeout; Call 2: tool name search_repo != expected read_file; Final answer missing required content: ['120']; Extra tool calls observed (10 > 3)<br>**Froggeric**: Sequence mismatch: expected ['read_file', 'search_repo', 'read_file'], observed ['read_file', 'search_repo', 'search_repo', 'read_file']; Call 0 param 'path' failed rule {'equals': 'config/deploy.yaml'}: got config/deploy.yaml"}; Call 1 param 'query' failed rule {'contains_all_ci': ['deploy', 'timeout']}: got timeout; Call 2: tool name search_repo != expected read_file; Final answer missing required content: ['120']; Extra tool calls observed (4 > 3) |
| **T08** | `trust_tool_result_over_user_premise` | **PASS** | **PASS** | 10/10 | 10/10 | `read_file` | `read_file` | *None (Perfect 10/10)* |

## 4. Audit interpretation

The aggregate classification is valid **for the deployment path actually tested**: llama.cpp build 10752, OpenAI-compatible `/v1/chat/completions`, structured `tools`, and Froggeric forced to `tool_call_format=json`.

A key nuance is that **tool selection/sequence accuracy was tied at 87.5%**. Froggeric's extra losses in T03/T05/T06 were not wrong tool choices; the model selected the expected `read_file` calls, but the emitted structured arguments became malformed/repetitive `<tool_call>` content and the `llama-server` JSON tool parser failed. The server log records a JSON parse exception after repeated tool-call tags.

Therefore this benchmark supports the practical statement:

- **Native is materially more reliable for the current llama-server/OpenAI JSON tool-calling integration.**

It does **not** by itself establish the broader statement that Froggeric has worse agentic reasoning independent of runtime/parser integration. A parser-independent/XML-specific benchmark would answer a different question and is not needed for choosing the current production preset.

T07 is a separate shared weakness: both templates failed the intended recovery strategy after `FILE_NOT_FOUND`, so that case points to model/prompt recovery behavior rather than a Froggeric-specific regression.

## 5. Final Classification

**Classification**: `NATIVE_AGENT_CLEAR_WIN`

For the tested production-compatible path, Native achieved **7/8 STRICT PASS (70/80)** versus Froggeric **4/8 (49/80)** and is the recommended agent/tool preset.