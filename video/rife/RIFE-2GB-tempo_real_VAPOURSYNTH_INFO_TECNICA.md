# 🎬 O Interpolador (RIFE-2GB-tempo_real-VapourSynth)

## Categoria
`04_🎨_ARTISTAS_IMAGEM_VIDEO`

## Descrição
Interpolação de frames via RIFE (Real-Time Intermediate Flow Estimation) com inference em tempo real via VapourSynth.
Modelo de 2GB para inserção de frames intermediários, convertendo 24fps em 48fps ou 60fps.

## Tipo
Interpolação / Frame Rate Conversion

## Stack
- ONNX Runtime (onnxruntime_directml ou onnxruntime-gpu)
- VapourSynth R66+
- Plugin vsOnnx (vapoursynth-onsr)

## Entrada
- Vídeo com framerate base (24fps, 30fps, 60fps)
- Recomendado: 1080p max para tempo real

## Saída
- Vídeo com framerate interpolado (2x ou mais)
- Frames intermediários gerados por optical flow

## Uso em Pipeline Forja
```
clip = core.onmx.OnnxFlow(clip, model="rife-v4.10.onnx")
```

## Modelos Disponíveis
- `rife_v4.0.onnx` — v4 base
- `rife_v4.2.onnx` — v4.2, melhor qualidade
- `rife_v4.3.onnx` — v4.3
- `rife_v4.4.onnx` — v4.4
- `rife_v4.5.onnx` — v4.5
- `rife_v4.6.onnx` — v4.6
- `rife_v4.7.onnx` — v4.7
- `rife_v4.8.onnx` — v4.8
- `rife_v4.9.onnx` — v4.9
- `rife_v4.10.onnx` — v4.10, mais recente

## Performance
- Tempo real em GPU dedicada (RTX 3060+)
- ~2GB VRAM por instância
- v4.x é mais rápido que v3.x com mesma qualidade

## Limitações
- Não funciona bem com scene cuts (gera ghosting)
- Textos em movimento podem ficar borrados
- 4x interpolation é muito pesado para tempo real

## Pipeline Típico
```
Source → Interpolation(2x) → Output
# Para 24fps → 48fps
