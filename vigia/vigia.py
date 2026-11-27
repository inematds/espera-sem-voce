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
  vigia.py add <pasta> --confere "<cmd que imprime pronto>" [--nome X] [--teto-h 8] [--log <arquivo>] [--mudou "<o quê>"]
  vigia.py rodada        (o timer chama este)
  vigia.py status
Tentativas: o mesmo --nome registrado de novo (depois de falhar, parar ou terminar) é a tentativa seguinte da
mesma CADEIA: guarda o ID da cadeia, soma 1 na tentativa, arquiva a anterior (estado, resultado e o que mudou)
e renomeia o CONTINUAR.resultado velho para CONTINUAR.resultado.tN. "O que mudou" sai do hash do CONTINUAR.md:
igual = "mesma entrada, nova chance"; diferente = o --mudou (ou "bilhete alterado, sem nota").
Quem vigia o vigia: vistoria.py (outro timer) confere de hora em hora se as rodadas continuam.
Variáveis:
  VIGIA_ESTADO   arquivo de estado            (padrão ~/.local/share/vigia/estado.json)
  VIGIA_FASE2    comando da fase 2; recebe a pasta em $PASTA  (padrão: claude -p lendo o CONTINUAR.md)
  VIGIA_AVISO    comando que avisa a pessoa; recebe a mensagem em $MSG (padrão: imprime)
"""
import argparse, hashlib, json, os, shlex, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ESTADO = Path(os.environ.get("VIGIA_ESTADO", Path.home() / ".local/share/vigia/estado.json"))
ULTIMA = ESTADO.with_name("ultima-rodada")   # a vistoria.py lê a hora deste arquivo: vigia parado = arquivo velho
TETO_FASE2_S = 3 * 3600          # a sessão nova tem até 3 h
TEMPO_CONFERE_S = 25 * 60        # uma conferência pode levar até 25 min
CADEIA_MORTA_S = 20 * 60         # log parado há 20 min e nenhum processo da pasta = morreu
# A fase 2 roda sem ninguém na frente da tela, então não pode parar para pedir licença: o bilhete
# (CONTINUAR.md) é a autorização. Use uma pasta só para o trabalho e escreva as travas no bilhete.
FASE2_PADRAO = ('claude -p --permission-mode bypassPermissions --max-turns 200 '
                '"Leia $PASTA/CONTINUAR.md e faça só o que está lá, até o fim, respeitando as travas. '
                'No fim grave $PASTA/CONTINUAR.resultado com FEITO: <o quê> ou FALHOU: <passo> — <motivo>. '
                'Se algum passo precisou de nova tentativa, acrescente uma linha por passo: '
                'REFEITO: <passo> — <o que trocou entre as tentativas> (ou "nada, só tentou de novo")."')


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


def rotulo(nome, it):
    """nome#tN: o mesmo em todo aviso e linha de log da tentativa; o ID da cadeia junta as tentativas."""
    return f"{nome}#t{it.get('tentativa', 1)}"


def hash_bilhete(pasta):
    return hashlib.sha256((Path(pasta) / "CONTINUAR.md").read_bytes()).hexdigest()[:12]


def add(a):
    pasta = Path(a.pasta).resolve()
    if not (pasta / "CONTINUAR.md").exists():
        sys.exit(f"falta {pasta}/CONTINUAR.md (o bilhete da fase 2)")
    nome = a.nome or pasta.name
    d = ler()
    velho = d.get(nome, {})
    if velho.get("estado") in ("esperando", "rodando"):
        sys.exit(f"{nome} já está no vigia")
    h = hash_bilhete(pasta)
    tentativas, n = velho.get("tentativas", []), velho.get("tentativa", 0) + 1
    if not velho:
        mudou = "primeira tentativa"
    elif velho.get("bilhete") == h:
        mudou = "mesma entrada, nova chance" + (f" ({a.mudou})" if a.mudou else "")
    else:
        mudou = f"bilhete alterado: {a.mudou}" if a.mudou else "bilhete alterado, sem nota"
    if velho:
        tentativas = tentativas + [{k: velho.get(k) for k in
                                    ("tentativa", "desde", "fim", "estado", "resultado", "bilhete", "mudou")}]
        res = pasta / "CONTINUAR.resultado"
        if res.exists():   # senão a tentativa nova, se morrer sem gravar, herdaria o resultado da anterior
            res.rename(pasta / f"CONTINUAR.resultado.t{velho.get('tentativa', 1)}")
    d[nome] = {"pasta": str(pasta), "confere": a.confere, "teto_h": a.teto_h, "log": a.log,
               "estado": "esperando", "desde": agora(),
               "cadeia": velho.get("cadeia") or f"{nome}-{datetime.now():%Y%m%d-%H%M}",
               "tentativa": n, "bilhete": h, "mudou": mudou, "tentativas": tentativas}
    gravar(d)
    extra = f" Tentativa {n} da cadeia {d[nome]['cadeia']}: {mudou}." if n > 1 else ""
    avisar(f"⏳ Fase 1 concluída: {rotulo(nome, d[nome])}. Esperando ficar pronto (até {a.teto_h:g} h).{extra} "
           "Pode fechar o terminal.")


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
    lg.write(f"\n=== {agora()} {rotulo(nome, it)} (cadeia {it.get('cadeia', nome)}; {it.get('mudou', '')})\n"); lg.flush()
    p = subprocess.Popen(["bash", "-c", cmd], cwd=it["pasta"],
                         env={**os.environ, "PASTA": it["pasta"]}, stdout=lg, stderr=lg, start_new_session=True)
    return p.pid   # o teto de 3 h é conferido na rodada (sem depender do `timeout`, que o macOS não tem)


def encerrar(pid):
    try:
        os.killpg(pid, 15)
    except OSError:
        pass


def vivo(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def rodada(_a=None):
    d = ler()
    for nome, it in d.items():
        r_ = rotulo(nome, it)
        if it["estado"] == "esperando":
            try:
                r = subprocess.run(it["confere"], shell=True, cwd=it["pasta"], capture_output=True, text=True,
                                   timeout=TEMPO_CONFERE_S)
                ult = (r.stdout.strip().splitlines() or [""])[-1].strip()
            except subprocess.TimeoutExpired:
                ult = "tempo esgotado"
            if ult == "pronto":
                it.update(estado="rodando", inicio=agora(), inicio_ts=time.time(), pid=abrir_fase2(nome, it))
                print(f"{r_}: pronto → fase 2")
            elif cadeia_morta(it):
                it.update(estado="parado", fim=agora(), resultado="trabalho morto (log parado há 20 min)")
                avisar(f"🟥 FALHOU {r_}: o trabalho morreu sem gravar resultado (log parado há 20 min).")
            elif (datetime.now() - datetime.strptime(it["desde"], "%Y-%m-%d %H:%M")).total_seconds() > it["teto_h"] * 3600:
                it.update(estado="parado", fim=agora(), resultado=f"teto: esperou {it['teto_h']:g} h")
                avisar(f"🟥 FALHOU {r_}: esperou {it['teto_h']:g} h e não ficou pronto.")
        elif it["estado"] == "rodando" and vivo(it.get("pid")) and time.time() - it.get("inicio_ts", time.time()) > TETO_FASE2_S:
            encerrar(it["pid"])
            it.update(estado="falhou", fim=agora(), resultado="passou de 3 h")
            avisar(f"🟥 FALHOU {r_}: a fase 2 passou de {TETO_FASE2_S // 3600} h e foi encerrada.")
        elif it["estado"] == "rodando" and not vivo(it.get("pid")):
            res = Path(it["pasta"]) / "CONTINUAR.resultado"
            txt = res.read_text().strip() if res.exists() else ""
            it.update(estado="feito" if txt.startswith("FEITO") else "falhou", fim=agora(), resultado=txt[:1000])
            if txt.startswith("FEITO"):
                avisar(f"✅ {r_}: {txt[:300]}")
            else:
                avisar(f"🟥 FALHOU {r_}: {txt[:300] or 'a fase 2 terminou sem CONTINUAR.resultado'}")
    gravar(d)
    ULTIMA.write_text(agora() + "\n")   # só no fim: rodada que quebrou no meio não conta como viva


def status(_a=None):
    if ULTIMA.exists():
        print(f"última rodada: {ULTIMA.read_text().strip()} (há {(time.time() - ULTIMA.stat().st_mtime) / 60:.0f} min)")
    for nome, it in ler().items():
        print(f"{rotulo(nome, it):30} {it['estado']:10} desde {it['desde']}  teto {it['teto_h']:g} h"
              f"  cadeia {it.get('cadeia', nome)}")
        for t in it.get("tentativas", []) + [it]:   # a cadeia inteira: o que mudou em cada tentativa e como acabou
            print(f"    t{t.get('tentativa', 1)} {t.get('estado') or '?':9} {t.get('mudou') or ''}"
                  f"  → {(t.get('resultado') or '').splitlines()[0][:90] if t.get('resultado') else '-'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("pasta"); p.add_argument("--confere", required=True)
    p.add_argument("--nome"); p.add_argument("--teto-h", type=float, default=8); p.add_argument("--log")
    p.add_argument("--mudou", help="o que mudou desde a tentativa anterior (vai no registro da cadeia)")
    p.set_defaults(f=add)
    sub.add_parser("rodada").set_defaults(f=rodada)
    sub.add_parser("status").set_defaults(f=status)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
