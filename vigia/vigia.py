#!/usr/bin/env python3
"""vigia — espera um trabalho demorado ficar pronto e chama uma SESSÃO NOVA para seguir.

Versão de exemplo, sem dependências, do vigia `continua` que roda na máquina do INEMA
(original num repositório privado; este aqui é o mesmo desenho, enxuto).

A ideia em 3 tempos:
  FASE 1  a sessão com a pessoa dispara o trabalho demorado (avatar, render, transcrição),
          escreve <pasta>/CONTINUAR.md (o que falta) e registra:  vigia.py add <pasta> --confere "<cmd>"
  VIGIA   um timer roda `vigia.py rodada` a cada 5 min. Para cada trabalho esperando, roda o
          --confere. Última linha "pronto" → abre a fase 2. Passou do teto → avisa a falha.
          Não usa IA: é só um script, custo zero enquanto espera.
  FASE 2  uma sessão nova (por padrão `claude -p`) lê SÓ o CONTINUAR.md e segue até o fim,
          gravando <pasta>/CONTINUAR.resultado ("FEITO: ..." ou "FALHOU: ...").

uso:
  vigia.py add <pasta> --confere "<cmd que imprime pronto>" [--nome X] [--teto-h 8] [--log <arquivo>]
  vigia.py rodada        (o timer chama este)
  vigia.py status
Variáveis:
  VIGIA_ESTADO   arquivo de estado            (padrão ~/.local/share/vigia/estado.json)
  VIGIA_FASE2    comando da fase 2; recebe a pasta em $PASTA  (padrão: claude -p lendo o CONTINUAR.md)
  VIGIA_AVISO    comando que avisa a pessoa; recebe a mensagem em $MSG (padrão: imprime)
"""
import argparse, json, os, shlex, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ESTADO = Path(os.environ.get("VIGIA_ESTADO", Path.home() / ".local/share/vigia/estado.json"))
TETO_FASE2_S = 3 * 3600          # a sessão nova tem até 3 h
TEMPO_CONFERE_S = 25 * 60        # uma conferência pode levar até 25 min
CADEIA_MORTA_S = 20 * 60         # log parado há 20 min e nenhum processo da pasta = morreu
FASE2_PADRAO = ('claude -p --max-turns 200 "Leia $PASTA/CONTINUAR.md e faça só o que está lá, até o fim. '
                'No fim grave $PASTA/CONTINUAR.resultado com FEITO: <o quê> ou FALHOU: <passo> — <motivo>."')


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def ler():
    try:
        return json.loads(ESTADO.read_text())
    except Exception:
        return {}


def gravar(d):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    tmp.replace(ESTADO)


def avisar(msg):
    cmd = os.environ.get("VIGIA_AVISO")
    if not cmd:
        print(f"[aviso] {msg}")
        return
    subprocess.run(cmd, shell=True, env={**os.environ, "MSG": msg}, timeout=60)


def add(a):
    pasta = Path(a.pasta).resolve()
    if not (pasta / "CONTINUAR.md").exists():
        sys.exit(f"falta {pasta}/CONTINUAR.md (o bilhete da fase 2)")
    nome = a.nome or pasta.name
    d = ler()
    if d.get(nome, {}).get("estado") in ("esperando", "rodando"):
        sys.exit(f"{nome} já está no vigia")
    d[nome] = {"pasta": str(pasta), "confere": a.confere, "teto_h": a.teto_h, "log": a.log,
               "estado": "esperando", "desde": agora()}
    gravar(d)
    avisar(f"⏳ Fase 1 concluída: {nome}. Esperando ficar pronto (até {a.teto_h:g} h). Pode fechar o terminal.")


def cadeia_morta(it):
    """o trabalho morreu sem dizer nada: o log não muda há 20 min e nenhum processo cita a pasta."""
    if not it.get("log"):
        return False
    lg = Path(it["log"])
    if not lg.exists() or time.time() - lg.stat().st_mtime < CADEIA_MORTA_S:
        return False
    return subprocess.run(["pgrep", "-f", it["pasta"]], capture_output=True).returncode != 0


def abrir_fase2(nome, it):
    cmd = os.environ.get("VIGIA_FASE2", FASE2_PADRAO)
    lg = open(Path(it["pasta"]) / "vigia-fase2.log", "a")
    p = subprocess.Popen(["timeout", str(TETO_FASE2_S), "bash", "-c", cmd], cwd=it["pasta"],
                         env={**os.environ, "PASTA": it["pasta"]}, stdout=lg, stderr=lg, start_new_session=True)
    return p.pid


def vivo(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def rodada(_a=None):
    d = ler()
    for nome, it in d.items():
        if it["estado"] == "esperando":
            try:
                r = subprocess.run(it["confere"], shell=True, cwd=it["pasta"], capture_output=True, text=True,
                                   timeout=TEMPO_CONFERE_S)
                ult = (r.stdout.strip().splitlines() or [""])[-1].strip()
            except subprocess.TimeoutExpired:
                ult = "tempo esgotado"
            if ult == "pronto":
                it.update(estado="rodando", inicio=agora(), pid=abrir_fase2(nome, it))
                print(f"{nome}: pronto → fase 2")
            elif cadeia_morta(it):
                it["estado"] = "parado"
                avisar(f"🟥 FALHOU {nome}: o trabalho morreu sem gravar resultado (log parado há 20 min).")
            elif (datetime.now() - datetime.strptime(it["desde"], "%Y-%m-%d %H:%M")).total_seconds() > it["teto_h"] * 3600:
                it["estado"] = "parado"
                avisar(f"🟥 FALHOU {nome}: esperou {it['teto_h']:g} h e não ficou pronto.")
        elif it["estado"] == "rodando" and not vivo(it.get("pid")):
            res = Path(it["pasta"]) / "CONTINUAR.resultado"
            txt = res.read_text().strip() if res.exists() else ""
            it.update(estado="feito" if txt.startswith("FEITO") else "falhou", fim=agora(), resultado=txt[:400])
            if txt.startswith("FEITO"):
                avisar(f"✅ {nome}: {txt[:300]}")
            else:
                avisar(f"🟥 FALHOU {nome}: {txt[:300] or 'a fase 2 terminou sem CONTINUAR.resultado'}")
    gravar(d)


def status(_a=None):
    for nome, it in ler().items():
        print(f"{nome:30} {it['estado']:10} desde {it['desde']}  teto {it['teto_h']:g} h")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("pasta"); p.add_argument("--confere", required=True)
    p.add_argument("--nome"); p.add_argument("--teto-h", type=float, default=8); p.add_argument("--log")
    p.set_defaults(f=add)
    sub.add_parser("rodada").set_defaults(f=rodada)
    sub.add_parser("status").set_defaults(f=status)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
