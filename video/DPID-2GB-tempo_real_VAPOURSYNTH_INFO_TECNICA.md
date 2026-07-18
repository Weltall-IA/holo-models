# 4.16 💎 O Restaurador (DPID-2GB-tempo_real-VapourSynth)

## Categoria
`04_🎨_ARTISTAS_IMAGEM_VIDEO`

## Descrição
Restauração de vídeo via DPID (Deep Prior-aware Detail) com inference em tempo real via VapourSynth.
Modelo onnx de 2GB otimizado para restauração de qualidade em vídeos degradados.

## Tipo
Restauração / Upscale (2x max)

## Stack
- ONNX Runtime (onnxruntime_directml ou onnxruntime-gpu)
- VapourSynth R66+
- Plugin vsOnnx (vapoursynth-onsr)

## Entrada
- Vídeo em qualquer formato legível pelo FFmpegInput
- Recomendado: 480p-1080p source

## Saída
- Vídeo restaurado com detalhes realçados
- Preserva resolução original (sem upscale)

## Uso em Pipeline Forja
```
clip = core.onmx.OnnxSR(clip, model="dpid-up2x.onnx")
```

## Modelos Disponíveis
- `dpid-up2x.onnx` — 2x upscale, conservador (recomendado para conteúdo rápido)
- `dpid-up3x.onnx` — 3x upscale
- `dpid-denoise-up2x.onnx` — denoise + upscale 2x
- `dpid-denoise-up3x.onnx` — denoise + upscale 3x
- `dpid-no-denoise-up2x.onnx` — upscale sem denoise
- `dpid-no-denoise-up3x.onnx` — upscale sem denoise

## Performance
- Tempo real em GPU dedicada (RTX 3060+)
- ~2GB VRAM por instância
- Para múltiplas instâncias: considerar tensorrt ou onnx-gpu

## Limitações
- Não faz interpolação de frames
- Não aumenta resolução além do 3x nativo
- Conteúdo muito ruidoso pode gerar artefatos

## Pipeline Típico
```
Source → Deblock_QED → SMDegrain → DPID (2x) → Output
