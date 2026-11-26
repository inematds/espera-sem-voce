#!/usr/bin/env python3
"""vistoria — quem vigia o vigia. Confere se o vigia continua rodando e se algum trabalho se perdeu.

Um processo parado não avisa que parou. Então a vistoria roda num timer separado e lê o que o vigia deixa gravado:
  1. vigia parado   o arquivo `ultima-rodada` (ao lado do estado) não muda há mais de 15 min
                    (o vigia roda a cada 5 min: são três rodadas perdidas)
  2. esquecido      trabalho ainda "esperando" depois de passar do próprio teto (o vigia não agiu)
  3. fase 2 sumida  trabalho "rodando" cujo processo já morreu, e o vigia não fechou
Não usa IA.

uso:
  vistoria.py hora   avisa só se tiver problema (o mesmo problema repete no máx. a cada 6 h) e "voltou" quando some
  vistoria.py dia    relatório do dia, sempre. Se ele não chegar, a máquina caiu (a vistoria mora nela também)
  vistoria.py ver    imprime o relatório sem avisar
Usa as mesmas variáveis do vigia: VIGIA_ESTADO e VIGIA_AVISO.
"""
import json, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vigia import ESTADO, ULTIMA, avisar, ler, vivo  # noqa: E402

MEMO = ESTADO.with_name("vistoria-avisos.json")
PARADO_S = 15 * 60
FOLGA_TETO_H = 0.5      # o vigia só marca "parado" na rodada seguinte ao teto
REPETE_S = 6 * 3600


def conferir():
    agora, prob = time.time(), {}
    if not ULTIMA.exists():
        prob["parado"] = "o vigia nunca completou uma rodada (o timer está instalado?)"
    elif agora - ULTIMA.stat().st_mtime > PARADO_S:
        prob["parado"] = f"a última rodada do vigia foi há {(agora - ULTIMA.stat().st_mtime) / 60:.0f} min"
    for nome, it in ler().items():
        if it.get("estado") == "esperando":
            h = (datetime.now() - datetime.strptime(it["desde"], "%Y-%m-%d %H:%M")).total_seconds() / 3600
            if h > it["teto_h"] + FOLGA_TETO_H:
                prob[f"esquecido:{nome}"] = f"{nome}: esperando há {h:.1f} h, teto {it['teto_h']:g} h"
        elif it.get("estado") == "rodando" and not vivo(it.get("pid")):
            if agora - it.get("inicio_ts", agora) > PARADO_S:
                prob[f"sumida:{nome}"] = f"{nome}: rodando, mas a fase 2 já morreu e o vigia não fechou"
    return prob


def hora():
    prob = conferir()
    try:
        memo = json.loads(MEMO.read_text())
    except Exception:
        memo = {}
    agora = time.time()
    novos = {k: v for k, v in prob.items() if agora - memo.get(k, 0) > REPETE_S}
    if novos:
        avisar("🟥 vistoria do vigia:\n" + "\n".join(f"• {v}" for v in novos.values()))
        memo.update({k: agora for k in novos})
    sumiram = [k for k in memo if k not in prob]
    if sumiram:
        avisar("✅ vistoria do vigia: voltou ao normal (" + ", ".join(sumiram) + ")")
        for k in sumiram:
            memo.pop(k)
    MEMO.parent.mkdir(parents=True, exist_ok=True)
    MEMO.write_text(json.dumps(memo))


def relatorio():
    prob, d, agora = conferir(), ler(), time.time()
    cont = {}
    for it in d.values():
        cont[it["estado"]] = cont.get(it["estado"], 0) + 1
    ult = f"{(agora - ULTIMA.stat().st_mtime) / 60:.0f} min atrás" if ULTIMA.exists() else "nunca"
    linhas = [f"📋 vistoria do vigia — {datetime.now():%d/%m %H:%M}",
              f"vigia: {'⚠️' if 'parado' in prob else 'ok'} · última rodada {ult}",
              "trabalhos: " + (", ".join(f"{n} {e}" for e, n in sorted(cont.items())) or "nenhum"),
              f"perdidos: {sum(1 for k in prob if k != 'parado')}"]
    linhas += [f"• {v}" for v in prob.values()]
    return "\n".join(linhas)


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "ver"
    if modo == "hora":
        hora()
    elif modo == "dia":
        avisar(relatorio())
    else:
        print(relatorio())
