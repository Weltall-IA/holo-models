# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.12.1

## Objetivo

Retomar a v2.2.12 após o bloqueio falso `BLOCKED_REPOS_NOT_FOUND`.

O bloqueio ocorreu porque foram consultados IDs incorretos que incluíam a quantização no nome do repositório. Os dois repositórios corretos existem.

Esta instrução substitui somente a resolução de identidade e download da v2.2.12. Todo o restante da v2.2.12 permanece obrigatório.

## Repositórios exatos

Use exclusivamente:

- Abiray: `Abiray/Nemotron-3-Embed-8B-GGUF`
- Aqua00: `Aqua00/Nemotron-3-Embed-8B-GGUF`

Não consultar nem usar como `repo_id`:

- `Abiray/Nemotron-3-Embed-8B-Q4_K_M`
- `Aqua00/Nemotron-3-Embed-8B-Q4_K_M`
- qualquer ID que acrescente `Q4_K_M` ao nome do repositório.

A quantização pertence ao nome do arquivo, não ao `repo_id`.

## Arquivo obrigatório

Em cada repositório, resolva exatamente um arquivo cujo nome seja:

`Nemotron-3-Embed-8B-Q4_K_M.gguf`

Pare somente se esse arquivo não existir no repositório correto.

## Resolução obrigatória por API

Use `huggingface_hub.HfApi().model_info(repo_id, files_metadata=True)` para cada repositório correto.

Para cada um, registre antes do download:

- `repo_id` exato;
- `info.sha` com 40 caracteres;
- nome exato do arquivo;
- tamanho remoto informado;
- licença declarada;
- modelo-base/linhagem declarada.

Não usar resultado de busca textual, alias `:Q4_K_M`, página em cache ou `main` como revisão de execução.

Exemplo de inspeção autorizada:

```bash
"$PYTHON" - <<'PY'
from huggingface_hub import HfApi

repos = [
    "Abiray/Nemotron-3-Embed-8B-GGUF",
    "Aqua00/Nemotron-3-Embed-8B-GGUF",
]
filename = "Nemotron-3-Embed-8B-Q4_K_M.gguf"
api = HfApi()
for repo in repos:
    info = api.model_info(repo, files_metadata=True)
    matches = [s for s in info.siblings if s.rfilename == filename]
    assert len(info.sha) == 40, (repo, info.sha)
    assert len(matches) == 1, (repo, [s.rfilename for s in info.siblings])
    item = matches[0]
    assert isinstance(item.size, int) and item.size > 0, (repo, item.size)
    print(repo, info.sha, filename, item.size, getattr(info.card_data, "license", None))
PY
```

## Pesos locais antigos

Os pesos locais reportados anteriormente:

- Abiray: `4896390039` bytes, SHA-256 iniciando em `a2aa29c6`;
- Aqua00: `4896389984` bytes, SHA-256 iniciando em `1352d929`;

não possuem metadados locais suficientes para provar revisão imutável. Portanto:

- não usá-los na nova auditoria;
- não apagá-los;
- não renomeá-los;
- não copiá-los para os diretórios novos;
- preservá-los como evidência histórica não rastreada.

A divergência em relação aos valores planejados antigos não é bloqueio. O valor válido será o tamanho e SHA-256 do arquivo baixado diretamente do repositório correto, fixado na revisão imutável resolvida nesta execução.

## Download limpo

Baixe novamente os dois arquivos, um por vez, em diretórios novos e separados:

- `runtimes/nemotron-8b-audit/abiray/<REVISAO>/`
- `runtimes/nemotron-8b-audit/aqua00/<REVISAO>/`

Use a revisão imutável retornada pela API:

```bash
hf download Abiray/Nemotron-3-Embed-8B-GGUF \
  Nemotron-3-Embed-8B-Q4_K_M.gguf \
  --revision "$ABIRAY_REVISION" \
  --local-dir "runtimes/nemotron-8b-audit/abiray/$ABIRAY_REVISION"

hf download Aqua00/Nemotron-3-Embed-8B-GGUF \
  Nemotron-3-Embed-8B-Q4_K_M.gguf \
  --revision "$AQUA00_REVISION" \
  --local-dir "runtimes/nemotron-8b-audit/aqua00/$AQUA00_REVISION"
```

Depois do download, compute tamanho e SHA-256 local completos. Eles passam a ser os valores esperados enviados ao runner.

Os dois arquivos precisam ter SHA-256 distintos. Se forem idênticos, reportar `BLOCKED_IDENTICAL_WEIGHTS_PROVEN` com a prova completa.

## Execução

Após resolver, baixar e validar os dois pesos, retome a v2.2.12 a partir de “Protocolo de embedding obrigatório”.

Execute primeiro Abiray e depois Aqua00, em processos separados, usando:

- os `repo_id` corretos desta instrução;
- as revisões imutáveis resolvidas;
- os arquivos recém-baixados;
- os tamanhos e SHA-256 completos recém-calculados.

Não reutilize qualquer output antigo.

## Resultado esperado desta retomada

A execução não pode retornar novamente `BLOCKED_REPOS_NOT_FOUND` para os IDs incorretos.

Um bloqueio legítimo só será aceito se ocorrer contra um dos dois repositórios corretos e incluir:

- chamada realmente realizada;
- status HTTP ou exceção completa sanitizada;
- `repo_id` exato;
- data/hora;
- tentativa por `HfApi.model_info`;
- tentativa de localizar o arquivo exato.

Se os repositórios e arquivos forem resolvidos, a execução deve continuar até os benchmarks raw, candidates e Qwen previstos na v2.2.12.

Nenhuma chamada Voyage é autorizada além das condições já definidas na v2.2.12.

## Git

Não editar código, testes, configuração ou instruções.

Ao concluir a execução real, commitar somente os novos artefatos autorizados pela v2.2.12 e fazer push na mesma branch.

PR #20 permanece aberto, draft e sem merge.
