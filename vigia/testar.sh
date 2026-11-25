#!/usr/bin/env bash
# Teste do vigia sem IA e sem esperar horas: um "trabalho" falso fica pronto quando o arquivo PRONTO aparece,
# e a fase 2 falsa só grava o resultado. Roda em ~2 s numa pasta temporária.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export VIGIA_ESTADO="$T/estado.json"
export VIGIA_FASE2='echo "FEITO: vídeo montado e publicado (teste)" > "$PASTA/CONTINUAR.resultado"'
V="python3 $AQUI/vigia.py"
falha=0; ok() { echo "ok   $1"; }; ruim() { echo "FALHA $1"; falha=1; }

# 1. espera enquanto não está pronto
mkdir -p "$T/job1"; echo "# monte o vídeo e publique" > "$T/job1/CONTINUAR.md"
$V add "$T/job1" --nome job1 --confere '[ -f PRONTO ] && echo pronto || echo aguardando' > /dev/null
$V rodada > /dev/null
grep -q '"estado": "esperando"' "$VIGIA_ESTADO" && ok "não pronto → continua esperando" || ruim "devia esperar"

# 2. ficou pronto → abre a fase 2 → fecha como feito
touch "$T/job1/PRONTO"; $V rodada > /dev/null; sleep 1; $V rodada > /dev/null
grep -q '"estado": "feito"' "$VIGIA_ESTADO" && ok "pronto → fase 2 → feito" || ruim "devia terminar feito"

# 3. passou do teto → para e avisa
mkdir -p "$T/job2"; echo "# nunca fica pronto" > "$T/job2/CONTINUAR.md"
$V add "$T/job2" --nome job2 --teto-h 0 --confere 'echo aguardando' > /dev/null
python3 - "$VIGIA_ESTADO" <<'EOF'
import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["job2"]["desde"]="2000-01-01 00:00"; json.dump(d,open(p,"w"))
EOF
saida=$($V rodada)
grep -q '"estado": "parado"' "$VIGIA_ESTADO" && echo "$saida" | grep -q "FALHOU job2" && ok "teto → parado + aviso" || ruim "devia parar no teto"

[ $falha = 0 ] && echo "3 de 3 ok" || { echo "teste falhou"; exit 1; }
