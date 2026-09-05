# MODEL_HISTORY.md — histórico compacto de modelos avaliados

Este arquivo é o índice canônico de modelos já avaliados e removidos/rejeitados no workspace. Ele existe para impedir downloads e benchmarks repetidos sem necessidade.

## Regra de uso

Antes de baixar, converter, quantizar ou benchmarkar qualquer modelo, consulte este arquivo e os summaries de benchmark já existentes.

Se o mesmo modelo, revisão, quantização ou uma variante materialmente equivalente já tiver sido testado, **não faça download nem reteste automaticamente**. Informe primeiro o resultado anterior e peça confirmação explícita do usuário.

Um reteste sem confirmação prévia só é justificável quando houver mudança material capaz de alterar o resultado, por exemplo: nova revisão/peso treinado, quantização substancialmente diferente, correção relevante de runtime/template, novo benchmark que mede outra capacidade ou mudança de hardware relevante. Nesse caso, registre no novo benchmark por que o histórico anterior não é suficiente.

Modelos rejeitados podem ter os artefatos volumosos compactados do branch atual. O commit original da execução permanece como fonte recuperável pelo Git.

## Modelos rejeitados / removidos

| Modelo | Variante testada | Resultado local principal | Status | Data / hardware | Evidência canônica | Ação em pedido futuro |
|---|---|---|---|---|---|---|
| `logic65/Qwen3.8-Whittle-16B` | `Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`, HF rev `d18db969059b15423be91f5d4fd119c8c907801c` | `coding-mini-v1`: **0/6**; mediana **19.83 tok/s** `AUTHOR_RECIPE`; pico **11076 MiB** | `WHITTLE16B_REJECT`; pesos removidos | 2026-09-04 / RTX 5060 Ti 16 GB | `benchmarks/whittle16b-candidate-v1/`; execução `c9823c3952666ae054610a404b3d4a2cafd4e553`; remoção `5563f043c6e4b99a6f937399f76975508350bed8` | Avisar que já foi testado e rejeitado. Não baixar de novo sem confirmação explícita ou versão/revisão materialmente nova. |
| `logic65/Qwen3.8-Whittle-MoE-27B-A17.8B-GGUF` | `Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M.gguf` | `coding-mini-v1`: **1/6**; **19.39 tok/s**; pico **15194 MiB** | `NÃO_COMPENSA`; pesos removidos | 2026-09 / RTX 5060 Ti 16 GB | `benchmarks/coding-mini-v1/results/CANDIDATES_ROUND_JACK_WHITTLE_SUMMARY.md` | Avisar que o MoE antigo já foi testado e não confundir com outras variantes Whittle. |
| `JackAgentLead/Jack-3.8-27B-Coder-16GB-VRAM` | `Jack-3.8-27B-Coder-16GB-VRAM.gguf` | `coding-mini-v1`: **4/6**; **7.92 tok/s**; pico **13049 MiB** | `NÃO_COMPENSA`; pesos removidos | 2026-09 / RTX 5060 Ti 16 GB | `benchmarks/coding-mini-v1/results/CANDIDATES_ROUND_JACK_WHITTLE_SUMMARY.md` | Avisar que já foi testado. Só repetir com mudança material ou confirmação explícita. |

## Política de compactação

Para candidato **decisivamente rejeitado** e removido, o branch atual deve preservar no mínimo:

- identificação exata do modelo/revisão/quantização;
- resultado e classificação principais;
- `SPEC.md` e `SUMMARY.md` do benchmark quando existirem;
- `RUN_MANIFEST.json` quando útil para reproduzir o ambiente;
- SHA do commit que continha os artefatos completos.

Após isso, podem ser removidos do branch atual, sem perda histórica do Git: GGUF/pesos, symlinks, perfil da pasta ativa, raw JSONL grande, logs de servidor, snapshots de preflight e runner exclusivo daquele candidato.

Não compactar automaticamente resultados de modelos aceitos, modelos próximos do gate ou campanhas ainda em análise.