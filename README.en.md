# Wait Without You

[![Wait Without You](guia/assets/banner-en.jpg)](https://inematds.github.io/espera-sem-voce/guia/en/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## What it is

**You want to hand a long job to the AI, go about your life, and get only the notice that it's done.** This free kit explains, with animated diagrams, the three ways INEMA's systems wait between one phase and the next: a **watcher** that checks from time to time and starts a new AI conversation when the work is ready, a **flow with a gate** that stops and waits for your "go ahead", and a **queue that resumes** the work after a crash. It also includes a ready-to-use watcher. To get started, just paste a request into Claude Code or Codex.

## 📖 User guide

Full guide (landing page + animated diagrams): **https://inematds.github.io/espera-sem-voce/guia/en/**

## How to start (without installing anything by hand)

Open Claude Code or Codex in your project folder and paste:

> Read the repository https://github.com/inematds/espera-sem-voce (the README and the vigia folder). Then look at my project and ask me which jobs take a long time (video, render, transcription, external generator) and how I wait for them today. Tell me, in plain language, which of the three ways fits each one (watcher, flow with a gate, or queue that resumes), how much time I would no longer have to keep the conversation open, and what the watcher would need in order to ask "is it ready?". Don't install or change anything before I say yes. Once I say yes: copy the example watcher, run its test, and set up the first handoff note and the first check for one of my jobs.

## The three ways of waiting

| | Watcher | Flow with a gate | Queue that resumes |
|---|---|---|---|
| Who waits | a separate program, no AI | the bot itself, phase by phase | the assistant itself, task by task |
| Good for | a one-off job started in a conversation with the AI | recurring production, with approval along the way | everyday requests that need to survive a restart |
| Checks | every 5 min | every 1 to 5 min (set per phase) | specialists every 15–20 s; heartbeat every 30 s |
| Gives up | 8 h without being ready (adjustable) | at each phase's limit (1 h to 40 h; 10 h in r7ex, 40 h for the promoavatar avatar) | chat/agent request: 1 attempt; if it dies → `failed` + notice, resume with `/job N`. Scheduled task: 2 attempts (retry after 30 s) |
| Approval along the way | no (instructions go in the handoff note) | yes, at the gate | no; resume later with `/job` |
| Source | `continua` watcher (internal, private project) → copy in [`vigia/`](vigia/) | [inemaccbot](https://github.com/inematds/inemaccbot) | [openpcbotv3](https://github.com/inematds/openpcbotv3) |

---

## Technical setup

### Prerequisites

- Linux or macOS with Python 3.9+ (standard library only). Timer: user systemd on Linux; on macOS, `cron` (`*/5 * * * * python3 …/vigia.py rodada`).
- The machine stays on and does not suspend while waiting (a laptop with the lid closed usually goes to sleep).
- For the default phase 2: `claude` (Claude Code) logged in through your subscription. You can swap it for any command with `VIGIA_FASE2` (e.g. `codex exec`).
- Optional: user systemd for the timer (or cron).

### Test the watcher (a few seconds, no AI)

```bash
git clone https://github.com/inematds/espera-sem-voce && cd espera-sem-voce
bash vigia/testar.sh        # 4 of 4 ok
```

The test covers: (1) not ready → keeps waiting; (2) ready → starts phase 2 → closes as done; (3) exceeded the time limit → stops and notifies; (4) phase 2 ran past 3 h → terminated and notified.

### Use it with a job of your own

```bash
# 1. in the job folder, the phase 2 handoff note (what's left, instructions, guardrails)
mkdir -p ~/trabalhos/video-x && cp vigia/CONTINUAR.exemplo.md ~/trabalhos/video-x/CONTINUAR.md

# 2. register: --confere is any command whose LAST line is "pronto" once the work is ready
python3 vigia/vigia.py add ~/trabalhos/video-x \
  --confere '[ -f saida/final.mp4 ] && echo pronto || echo aguardando' --teto-h 8

# 3. the timer triggers a check round every 5 min
mkdir -p ~/.config/systemd/user && cp vigia/systemd/vigia.service vigia/systemd/vigia.timer ~/.config/systemd/user/
# vigia.service assumes the kit is in ~/espera-sem-voce: adjust the path to vigia.py if you cloned it elsewhere
systemctl --user daemon-reload && systemctl --user enable --now vigia.timer

python3 vigia/vigia.py status
```

Variables: `VIGIA_ESTADO` (state file), `VIGIA_FASE2` (phase 2 command, receives `$PASTA`), `VIGIA_AVISO` (command that sends the notice, receives `$MSG`). Without `VIGIA_AVISO` the notice only goes to the log; to get it on your phone, connect your Telegram bot:

```bash
export VIGIA_AVISO='curl -s "https://api.telegram.org/bot$TG_TOKEN/sendMessage" --data-urlencode chat_id=$TG_CHAT --data-urlencode text="$MSG" > /dev/null'
```

The systemd timer does not see a terminal `export`: put the same line in `vigia.service` as `Environment=VIGIA_AVISO=...` (with `TG_TOKEN` and `TG_CHAT`), or in an `EnvironmentFile=`, then run `systemctl --user daemon-reload`.

**Phase 2 permissions:** the default is `claude -p --permission-mode bypassPermissions`, because with nobody in front of the screen it can't stop to ask for permission. The handoff note is the authorization: run it in a folder dedicated to that job and write the guardrails in `CONTINUAR.md`. Want another engine? `VIGIA_FASE2='codex exec --full-auto "Leia $PASTA/CONTINUAR.md …"'`.

### Files

| File | What it is |
|---|---|
| `vigia/vigia.py` | the watcher (add, rodada, status) |
| `vigia/testar.sh` | test without AI, 4 cases |
| `vigia/CONTINUAR.exemplo.md` | template for the phase 2 handoff note |
| `vigia/systemd/` | timer that runs every 5 min |
| `guia/` | the page with the animated diagrams (PT, `en/`, `es/`) |

### Watcher time limits

| What | Limit | If exceeded |
|---|---|---|
| Check | every 5 min (timer) | — |
| A single check | up to 25 min | counts as "not yet" |
| Waiting | 8 h (`--teto-h`) | 🟥 "waited N h" notice |
| Dead job (`--log` stalled and no process from the folder) | 20 min | 🟥 notice before the time limit |
| Phase 2 | up to 3 h (checked during the round) | 🟥 if it runs past 3 h or ends without `CONTINUAR.resultado` |

### Where each piece lives in the source projects

- **Flow with a gate (inemaccbot):** waiting phase = `espera: {intervalo, timeout}` in `src/dominio/flow.ts`; gate = `pausa_apos`; the phase that downloads the HeyGen video, finding it by title (which makes it possible to resume after a crash), in `src/fila/tarefas/heygen.ts`. How to plug in: `docs/plugar-fluxo.md`.
- **Queue that resumes (openpcbotv3):** states `queued | running | done | failed | canceled` in `src/fila/types.ts`; 120 s lease renewed every 30 s in `src/index.ts`; an expired lease goes back to `queued` if there are attempts left, otherwise `failed` with a notice (`recuperarLeasesVencidos` in `src/fila/store.ts`). Chat and agent requests are queued with `max_tentativas: 1` (`src/orquestrador/orquestrador.ts`); scheduled tasks with 2, and the retry waits 30 s × 2ⁿ⁻¹. The lead waits for the specialists using `aindaNao` every 15–20 s (`src/orquestrador/tarefas-fila.ts`); `/status` and `/job N continue de onde parou` in `src/orquestrador/comandos.ts`.
- **Watcher (continua):** private INEMA repository; the design is reproduced here in `vigia/vigia.py`, without the machine-specific parts (bot notices, serial queue, configurable AI engine).

## The process, start to finish

🧠 = session with you · ⚙️ = script/timer · 🤖 = `claude -p` (subscription)

| # | Step | Command / what happens | Who |
|---|---|---|---|
| 1 | Phase 1 | the AI does the thinking part (script, approval) and launches the long-running job | 🧠 |
| 2 | Handoff note | writes `<pasta>/CONTINUAR.md`: what's left, your instructions as quoted, the guardrails | 🧠 |
| 3 | Register | `vigia.py add <pasta> --confere "<cmd>" [--teto-h 8]` → notice "Phase 1 complete, you can close it" | 🧠 |
| 4 | Wait | the timer runs `vigia.py rodada` every 5 min; no AI running | ⚙️ |
| 5 | Ready | last line of `--confere` = `pronto` → starts phase 2 (up to 3 h) | ⚙️ |
| 6 | Phase 2 | the new AI reads only `CONTINUAR.md`, finishes the job and writes `CONTINUAR.resultado` | 🤖 |
| 7 | Close | the watcher reads the result and notifies you: ✅ done or 🟥 failed (also on time limit and dead job) | ⚙️ |

## License

MIT. Made by [INEMA.CLUB](https://inema.club): open and free content.
