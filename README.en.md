# Wait Without You

[![Wait Without You](guia/assets/banner-en.jpg)](https://inematds.github.io/espera-sem-voce/guia/en/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## What it is

**You want to hand the AI a long job, go live your life and just get a message when it's done.** This free kit explains, with animated diagrams, the three ways INEMA's systems wait between one phase and the next: a **watcher** that checks every so often and starts a fresh AI conversation when the job is ready, a **gated flow** that stops and waits for your "go ahead", and a **queue that resumes** the work after a crash. It also comes with a ready-to-use watcher. To get started, just paste a request into Claude Code or Codex.

## 📖 User guide

Full guide (landing page + animated diagrams): **https://inematds.github.io/espera-sem-voce/guia/en/**

## How to start (nothing to install by hand)

Open Claude Code or Codex in your project folder and paste:

> Read the repository https://github.com/inematds/espera-sem-voce (the README and the vigia folder). Then look at my project and ask me which jobs take a long time (video, render, transcription, external generator) and how I wait for them today. Tell me, in plain language, which of the three ways fits each one (watcher, gated flow or queue that resumes), how much time I would no longer spend keeping the conversation open, and what the watcher would need in order to ask "is it ready?". Don't install or change anything before I say yes. Once I say yes: copy the example watcher, run its test, and set up the first handoff note and the first check for one of my jobs.

## The three ways to wait

| | Watcher | Gated flow | Queue that resumes |
|---|---|---|---|
| Who waits | a separate program, no AI | the bot itself, phase by phase | the assistant itself, task by task |
| Good for | a one-off job started in a conversation with the AI | recurring production, with approval along the way | everyday requests, with transient errors |
| Checks | every 5 min | every 1 to 5 min (set per phase) | heartbeat every 30 s |
| Gives up | after 8 h without being ready (adjustable) | at the phase limit (10 h in r7ex, 40 h for the long avatar) | after the retries run out (30 s × 2ⁿ between them) |
| Approval along the way | no (your instructions go in the note) | yes, at the gate | no; resume later with `/job` |
| Source | `continua` watcher (internal, private project) → copy in [`vigia/`](vigia/) | [inemaccbot](https://github.com/inematds/inemaccbot) | [openpcbotv3](https://github.com/inematds/openpcbotv3) |

---

## Technical setup

### Prerequisites

- Linux or macOS with Python 3.9+ (standard library only).
- For the default phase 2: `claude` (Claude Code) logged in with your subscription. You can swap it for any command with `VIGIA_FASE2` (e.g. `codex exec`).
- Optional: a systemd user timer (or cron).

### Test the watcher (2 s, no AI)

```bash
git clone https://github.com/inematds/espera-sem-voce && cd espera-sem-voce
bash vigia/testar.sh        # 3 de 3 ok
```

The test covers: (1) not ready → keeps waiting; (2) ready → starts phase 2 → closes as done; (3) past the time limit → stops and notifies you.

### Use it with a job of your own

```bash
# 1. na pasta do trabalho, o bilhete da fase 2 (o que falta, ordens, travas)
cp vigia/CONTINUAR.exemplo.md ~/trabalhos/video-x/CONTINUAR.md

# 2. registrar: o --confere é qualquer comando cuja ÚLTIMA linha seja "pronto" quando ficar pronto
python3 vigia/vigia.py add ~/trabalhos/video-x \
  --confere '[ -f saida/final.mp4 ] && echo pronto || echo aguardando' --teto-h 8

# 3. o timer chama a rodada a cada 5 min
cp vigia/systemd/vigia.service vigia/systemd/vigia.timer ~/.config/systemd/user/
# ajuste o caminho do vigia.py no vigia.service
systemctl --user daemon-reload && systemctl --user enable --now vigia.timer

python3 vigia/vigia.py status
```

Variables: `VIGIA_ESTADO` (state file), `VIGIA_FASE2` (phase 2 command, receives `$PASTA`), `VIGIA_AVISO` (notification command, receives `$MSG`, for example a `curl` to your Telegram bot).

### Files

| File | What it is |
|---|---|
| `vigia/vigia.py` | the watcher (add, rodada, status) |
| `vigia/testar.sh` | test with no AI, 3 cases |
| `vigia/CONTINUAR.exemplo.md` | template for the phase 2 handoff note |
| `vigia/systemd/` | timer that runs every 5 min |
| `guia/` | the page with the animated diagrams (PT, `en/`, `es/`) |

### Watcher time limits

| What | Time limit | If exceeded |
|---|---|---|
| Checking | every 5 min (timer) | — |
| A single check | up to 25 min | counts as "not yet" |
| Waiting | 8 h (`--teto-h`) | 🟥 "waited N h" alert |
| Dead job (`--log` stalled and no process from the folder) | 20 min | 🟥 alert before the time limit |
| Phase 2 | up to 3 h | 🟥 if it ends without `CONTINUAR.resultado` |

### Where each piece lives in the source projects

- **Gated flow (inemaccbot):** waiting phase = `espera: {intervalo, timeout}` in `src/dominio/flow.ts`; gate = `pausa_apos`; the phase that downloads the HeyGen video, finding it by title (which is what makes it possible to resume after a crash), in `src/fila/tarefas/heygen.ts`. How to plug in: `docs/plugar-fluxo.md`.
- **Queue that resumes (openpcbotv3):** states `queued | running | done | failed | canceled` in `src/fila/types.ts`; 120 s lease renewed every 30 s and a new attempt after a 30 s × 2ⁿ wait in `src/fila/store.ts`; `aindaNao` reschedules without using up an attempt; `/status` and `/job N continue` in `src/orquestrador/comandos.ts`.
- **Watcher (continua):** private INEMA repository; the design is reproduced here in `vigia/vigia.py`, without the machine-specific parts (bot notification, serial queue, configurable AI engine).

## The process, start to finish

🧠 = session with you · ⚙️ = script/timer · 🤖 = `claude -p` (subscription)

| # | Step | Command / what happens | Who |
|---|---|---|---|
| 1 | Phase 1 | the AI does the part that takes thinking (script, approval) and kicks off the slow job | 🧠 |
| 2 | Handoff note | writes `<pasta>/CONTINUAR.md`: what's left, your instructions quoted, the guardrails | 🧠 |
| 3 | Register | `vigia.py add <pasta> --confere "<cmd>" [--teto-h 8]` → message "Phase 1 complete, you can close" | 🧠 |
| 4 | Wait | the timer runs `vigia.py rodada` every 5 min; no AI running | ⚙️ |
| 5 | Ready | last line of `--confere` = `pronto` → starts phase 2 (up to 3 h) | ⚙️ |
| 6 | Phase 2 | the new AI reads only `CONTINUAR.md`, finishes the job and writes `CONTINUAR.resultado` | 🤖 |
| 7 | Close | the watcher reads the result and notifies you: ✅ done or 🟥 failed (also on the time limit and on a dead job) | ⚙️ |

## License

MIT. Made by [INEMA.CLUB](https://inema.club): open and free content.
