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

# 4. fase 2 que passa de 3 h → encerrada e avisada (sem depender do comando `timeout`)
mkdir -p "$T/job3"; echo "# demora demais" > "$T/job3/CONTINUAR.md"
$V add "$T/job3" --nome job3 --confere 'echo pronto' > /dev/null
VIGIA_FASE2='sleep 30' $V rodada > /dev/null
python3 - "$VIGIA_ESTADO" <<'EOF'
import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["job3"]["inicio_ts"]=0; json.dump(d,open(p,"w"))
EOF
saida=$($V rodada)
python3 -c "import json,sys;d=json.load(open('$VIGIA_ESTADO'));sys.exit(0 if d['job3']['estado']=='falhou' else 1)" && echo "$saida" | grep -q "FALHOU job3" && ok "fase 2 passou de 3 h → encerrada + aviso" || ruim "devia encerrar a fase 2"

# 5. vistoria: vigia rodando → nada a avisar; vigia parado há 1 h → avisa; voltou → avisa que voltou
S="python3 $AQUI/vistoria.py"
$V rodada > /dev/null
s1=$($S hora)
touch -d '1 hour ago' "$T/ultima-rodada"
s2=$($S hora); s3=$($S hora)
$V rodada > /dev/null; s4=$($S hora)
[ -z "$s1" ] && echo "$s2" | grep -q "última rodada do vigia foi há 60 min" && [ -z "$s3" ] && echo "$s4" | grep -q "voltou" \
  && ok "vistoria: vigia parado → aviso uma vez, voltou → aviso" || ruim "a vistoria devia ver o vigia parado"

[ $falha = 0 ] && echo "5 de 5 ok" || { echo "teste falhou"; exit 1; }
