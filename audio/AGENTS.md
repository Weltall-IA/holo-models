Regra para esta categoria:
- Novos modelos baixados vêm para esta pasta.
- Criar Modelfile com configuração recomendada da página do modelo.
- Registrar via `ollama create -f Modelfile` (GGUF/LLM). Modelos safetensors ficam para uso direto via transformers (sem registro Ollama). Obs: o Ollama faz cópia, não reflink COW.
- Ao remover um modelo desta pasta, também removê-lo do Ollama para não deixar registros órfãos.
Após remover um modelo, usar `ollama rm <modelo>` e apagar manualmente SÓ os blobs em `ollama/blobs/` não referenciados por nenhum manifest em `ollama/manifests/` (não usar `modelblob clean-orphans`, que marca blobs usados como órfãos). Nunca deixar blobs sem arquivo de modelo correspondente na pasta de categoria.
