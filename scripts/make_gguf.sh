#!/bin/bash
# Converte o modelo fundido (base + adaptador) para GGUF e gera as versões quantizadas.
#
#     bash scripts/make_gguf.sh [pasta do modelo fundido] [pasta de saída]
#
# Precisa do llama.cpp em ~/.local/opt/llama.cpp (clone raso, com `llama-quantize` compilado
# em build/bin) e do pacote Python `gguf`, trazido pelo `uv run --with gguf`.
set -euo pipefail
MERGED="${1:-outputs/train/merged/grpo-c-sft-cases}"   # the published model: base + supervised + reinforcement adapters
OUT="${2:-outputs/publish/gguf}"
LLAMA="${LLAMA_CPP:-$HOME/.local/opt/llama.cpp}"
NAME="causalista-4b"
mkdir -p "$OUT"
echo "== conversão para f16 $(date -Is)"
uv run --with gguf python "$LLAMA/convert_hf_to_gguf.py" "$MERGED" --outfile "$OUT/$NAME-f16.gguf" --outtype f16
for Q in Q4_K_M Q8_0; do
    echo "== quantização $Q $(date -Is)"
    "$LLAMA/build/bin/llama-quantize" "$OUT/$NAME-f16.gguf" "$OUT/$NAME-$Q.gguf" "$Q" > "$OUT/quantize-$Q.log" 2>&1
done
ls -la "$OUT"
echo "== fim $(date -Is)"
