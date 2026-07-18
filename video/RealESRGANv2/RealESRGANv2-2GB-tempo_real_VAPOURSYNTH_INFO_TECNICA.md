# 🖼️ O Ampliador (RealESRGANv2-2GB-tempo_real-VapourSynth)

## Categoria
`04_🎨_ARTISTAS_IMAGEM_VIDEO`

## Descrição
Upscale de vídeo via RealESRGANv2 com inference em tempo real via VapourSynth.
Modelo animevideo de 2GB otimizado para conteúdo animado e live-action.

## Tipo
Upscale / Restauração (2x-4x)

## Stack
- ONNX Runtime (onnxruntime_directml ou onnxruntime-gpu)
- VapourSynth R66+
- Plugin vsOnnx (vapoursynth-onsr)

## Entrada
- Vídeo em qualquer formato legível pelo FFmpegInput
- Recomendado: 480p-720p source para melhor qualidade

## Saída
- Vídeo em upscale 2x ou 4x conforme variante
- Preserva detalhes de borda e texturas

## Uso em Pipeline Forja
```
clip = core.onmx.OnnxSR(clip, model="realesr-animevideov3-x2.onnx")
clip = core.onmx.OnnxSR(clip, model="realesr-animevideov3-x4.onnx")
```

## Modelos Disponíveis
- `realesr-animevideov3-x2.onnx` — 2x upscale, variante anime
- `realesr-animevideov3-x4.onnx` — 4x upscale, variante anime
- `RealESRGANv2-animevideo-xsx2.onnx` — 2x alternativo
- `RealESRGANv2-animevideo-xsx4.onnx` — 4x alternativo

## Performance
- Tempo real em GPU dedicada (RTX 3060+)
- ~2GB VRAM por instância
- 4x é mais pesado que 2x (~2.5x tempo)

## Limitações
- Pode gerar oversharpening em conteúdo live-action
- Textos podem ficar com halo
- Não faz denoise integrado (usar filtro separate)

## Pipeline Típico
```
Source → KNLMeansCL → RealESRGAN (2x) → Output
