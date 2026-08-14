# Comandos locais

Atualizado em: 2026-07-21 23:00:00

## Ajuda e documentação

| Comando | Função |
|---|---|
| `comandos` | Mostra help no terminal. Use `comandos doc` para catálogo completo e `comandos edit` para editar. |
| `mpvh` | Mostra no terminal o help dos atalhos e arquivos principais do MPV. |

## Áudio e Bluetooth

| Comando | Função |
|---|---|
| `moon` | Reinicia PipeWire/WirePlumber, reconecta o Moondrop Space Travel e define como sink padrão. Use quando o fone desconectar ou o áudio não aparecer no seletor. |

## IA, modelos e Hugging Face

| Comando | Função |
|---|---|
| `hf` | CLI do Hugging Face Hub (pipx). |
| `huggingface-cli` | Mesmo que `hf`. |
| `ollama create` | Registra modelo GGUF no Ollama a partir de um Modelfile (`ollama create -f Modelfile`). Faz cópia, não reflink COW. Antigo `modelblob`/`forja_importar.sh`. |
| `tiny-agents` | Agentes tiny do Hugging Face (pipx). |

## Mídia, MPV e IPTV

| Comando | Função |
|---|---|
| `ff2mpv-mpv-vivaldi` | Wrapper para abrir links do Vivaldi no MPV. |
| `iptvup` | Atualiza/repara IPTVnator e reaplica o patch A-Z no seletor de playlists. |
| `pik` | Reinicia o mount PikPak (rclone) e encerra mpv/dolphin antes, evitando travamento em estado D. Sem watchdog automático. |
| `flixpatrol` | Busca Top 10 da FlixPatrol (Brasil) e adiciona magnets ao PikPak por gênero (cascata 1337x→torrentio→jackett→solidtorrents). |

## Sistema, manutenção e armazenamento

| Comando | Função |
|---|---|
| `libvirtfix` | Corrige rede libvirt/virbr0 quando VM der problema. |
| `zelador` | Auditoria/manutenção do sistema Btrfs e pool bcachefs. |
| `zelador-pool` | Atalho para `zelador` (só pool bcachefs). |
| `zelador-sistema` | Atalho para `zelador` (só sistema Btrfs). |

## Utilitários

| Comando | Função |
|---|---|
| `email_validator` | Wrapper do validador de email (Python). |

## Virtualização

| Comando | Função |
|---|---|
| `clone` | Clona VM qcow2 em `/home/alpha/VMs`. |
