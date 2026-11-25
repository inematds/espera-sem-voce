# Espera sem você

[![Espera sem você](guia/assets/banner.jpg)](https://inematds.github.io/espera-sem-voce/guia/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## O que é

**Você quer pedir um trabalho longo à IA, ir cuidar da vida e receber só o aviso de que terminou.** Este kit gratuito explica, com diagramas animados, os três jeitos que os sistemas da INEMA usam para esperar entre uma fase e outra: um **vigia** que confere de tempos em tempos e chama uma conversa nova da IA quando fica pronto, um **fluxo com portão** que para e espera o seu "pode seguir", e uma **fila que retoma** o trabalho depois de uma queda. Traz também um vigia pronto para você usar. Para começar, basta colar um pedido no Claude Code ou no Codex.

## 📖 Guia de uso

Guia completo (landing + diagramas animados): **https://inematds.github.io/espera-sem-voce/guia/**

## Como começar (sem instalar nada à mão)

Abra o Claude Code ou o Codex na pasta do seu projeto e cole:

> Leia o repositório https://github.com/inematds/espera-sem-voce (o README e a pasta vigia). Depois olhe o meu projeto e me pergunte quais trabalhos demoram (vídeo, render, transcrição, gerador externo) e como eu espero hoje. Me diga, em linguagem simples, qual dos três jeitos serve para cada um (vigia, fluxo com portão ou fila que retoma), quanto tempo eu deixaria de ficar com a conversa aberta e o que precisaria para o vigia saber perguntar "ficou pronto?". Não instale nem mude nada antes do meu sim. Com o meu sim: copie o vigia de exemplo, rode o teste dele, e monte o primeiro bilhete e a primeira conferência para um trabalho meu.

## Os três jeitos de esperar

| | Vigia | Fluxo com portão | Fila que retoma |
|---|---|---|---|
| Quem espera | um programa à parte, sem IA | o próprio bot, fase por fase | o próprio assistente, tarefa por tarefa |
| Bom para | trabalho de uma vez começado numa conversa com a IA | produção que se repete, com aprovação no meio | pedidos do dia a dia que precisam sobreviver a um reinício |
| Confere | a cada 5 min | a cada 1 a 5 min (definido por fase) | especialistas a cada 15–20 s; sinal de vida a cada 30 s |
| Desiste | 8 h sem ficar pronto (ajustável) | no limite de cada fase (1 h a 40 h; 10 h no r7ex, 40 h no avatar do promoavatar) | pedido de chat/agente: 1 tentativa; caiu → `failed` + aviso, retoma com `/job N`. Tarefa agendada: 2 tentativas (nova após 30 s) |
| Aprovação no meio | não (as ordens vão no bilhete) | sim, no portão | não; retomar depois com `/job` |
| Origem | vigia `continua` (projeto interno, privado) → cópia em [`vigia/`](vigia/) | [inemaccbot](https://github.com/inematds/inemaccbot) | [openpcbotv3](https://github.com/inematds/openpcbotv3) |

---

## Instalação técnica

### Pré-requisitos

- Linux ou macOS com Python 3.9+ (só biblioteca padrão). Timer: systemd do usuário no Linux; no macOS, `cron` (`*/5 * * * * python3 …/vigia.py rodada`).
- A máquina fica ligada e sem suspender enquanto espera (notebook com a tampa fechada costuma dormir).
- Para a fase 2 padrão: o `claude` (Claude Code) logado pela assinatura. Dá para trocar por qualquer comando com `VIGIA_FASE2` (ex.: `codex exec`).
- Opcional: systemd do usuário para o timer (ou cron).

### Testar o vigia (poucos segundos, sem IA)

```bash
git clone https://github.com/inematds/espera-sem-voce && cd espera-sem-voce
bash vigia/testar.sh        # 4 de 4 ok
```

O teste cobre: (1) não pronto → continua esperando; (2) pronto → abre a fase 2 → fecha como feito; (3) passou do teto → para e avisa; (4) fase 2 passou de 3 h → encerrada e avisada.

### Usar com um trabalho seu

```bash
# 1. na pasta do trabalho, o bilhete da fase 2 (o que falta, ordens, travas)
mkdir -p ~/trabalhos/video-x && cp vigia/CONTINUAR.exemplo.md ~/trabalhos/video-x/CONTINUAR.md

# 2. registrar: o --confere é qualquer comando cuja ÚLTIMA linha seja "pronto" quando ficar pronto
python3 vigia/vigia.py add ~/trabalhos/video-x \
  --confere '[ -f saida/final.mp4 ] && echo pronto || echo aguardando' --teto-h 8

# 3. o timer chama a rodada a cada 5 min
cp vigia/systemd/vigia.service vigia/systemd/vigia.timer ~/.config/systemd/user/
# o vigia.service supõe o kit em ~/espera-sem-voce: ajuste o caminho do vigia.py se clonou em outro lugar
systemctl --user daemon-reload && systemctl --user enable --now vigia.timer

python3 vigia/vigia.py status
```

Variáveis: `VIGIA_ESTADO` (arquivo de estado), `VIGIA_FASE2` (comando da fase 2, recebe `$PASTA`), `VIGIA_AVISO` (comando que avisa, recebe `$MSG`). Sem `VIGIA_AVISO` o aviso só vai para o log; para chegar no celular, ligue o seu bot do Telegram:

```bash
export VIGIA_AVISO='curl -s "https://api.telegram.org/bot$TG_TOKEN/sendMessage" --data-urlencode chat_id=$TG_CHAT --data-urlencode text="$MSG" > /dev/null'
```

**Permissão da fase 2:** o padrão é `claude -p --permission-mode bypassPermissions`, porque sem ninguém na frente da tela ela não pode parar para pedir licença. O bilhete é a autorização: rode numa pasta só do trabalho e escreva as travas no `CONTINUAR.md`. Quer outro motor? `VIGIA_FASE2='codex exec --full-auto "Leia $PASTA/CONTINUAR.md …"'`.

### Arquivos

| Arquivo | O que é |
|---|---|
| `vigia/vigia.py` | o vigia (add, rodada, status) |
| `vigia/testar.sh` | teste sem IA, 4 casos |
| `vigia/CONTINUAR.exemplo.md` | modelo do bilhete da fase 2 |
| `vigia/systemd/` | timer de 5 em 5 min |
| `guia/` | a página com os diagramas animados (PT, `en/`, `es/`) |

### Prazos do vigia

| O quê | Prazo | Se passar |
|---|---|---|
| Conferir | a cada 5 min (timer) | — |
| Uma conferência | até 25 min | conta como "ainda não" |
| Espera | 8 h (`--teto-h`) | 🟥 aviso "esperou N h" |
| Trabalho morto (`--log` parado e nenhum processo da pasta) | 20 min | 🟥 aviso antes do teto |
| Fase 2 | até 3 h (conferido na rodada) | 🟥 se passar de 3 h ou acabar sem `CONTINUAR.resultado` |

### Onde está cada peça nos projetos de origem

- **Fluxo com portão (inemaccbot):** fase de espera = `espera: {intervalo, timeout}` em `src/dominio/flow.ts`; portão = `pausa_apos`; a fase que baixa o vídeo do HeyGen, achando-o pelo título (o que permite retomar depois de uma queda), em `src/fila/tarefas/heygen.ts`. Como plugar: `docs/plugar-fluxo.md`.
- **Fila que retoma (openpcbotv3):** estados `queued | running | done | failed | canceled` em `src/fila/types.ts`; lease de 120 s renovado a cada 30 s em `src/index.ts`; lease vencido volta para `queued` se ainda há tentativa, senão `failed` com aviso (`recuperarLeasesVencidos` em `src/fila/store.ts`). Pedidos de chat e agente entram com `max_tentativas: 1` (`src/orquestrador/orquestrador.ts`); tarefas agendadas com 2, e a nova tentativa espera 30 s × 2ⁿ⁻¹. O líder espera os especialistas com `aindaNao` a cada 15–20 s (`src/orquestrador/tarefas-fila.ts`); `/status` e `/job N continue de onde parou` em `src/orquestrador/comandos.ts`.
- **Vigia (continua):** repositório privado da INEMA; o desenho está reproduzido aqui em `vigia/vigia.py`, sem as partes da máquina (aviso no bot, fila em série, motor de IA configurável).

## O processo, do início ao fim

🧠 = sessão com você · ⚙️ = script/timer · 🤖 = `claude -p` (assinatura)

| # | Passo | Comando / o que acontece | Quem |
|---|---|---|---|
| 1 | Fase 1 | a IA faz a parte que pensa (roteiro, aprovação) e dispara o trabalho demorado | 🧠 |
| 2 | Bilhete | escreve `<pasta>/CONTINUAR.md`: o que falta, as suas ordens citadas, as travas | 🧠 |
| 3 | Registrar | `vigia.py add <pasta> --confere "<cmd>" [--teto-h 8]` → aviso "Fase 1 concluída, pode fechar" | 🧠 |
| 4 | Esperar | o timer roda `vigia.py rodada` a cada 5 min; nenhuma IA ligada | ⚙️ |
| 5 | Pronto | última linha do `--confere` = `pronto` → abre a fase 2 (até 3 h) | ⚙️ |
| 6 | Fase 2 | a IA nova lê só o `CONTINUAR.md`, termina e grava `CONTINUAR.resultado` | 🤖 |
| 7 | Fechar | o vigia lê o resultado e avisa: ✅ feito ou 🟥 falhou (também no teto e no trabalho morto) | ⚙️ |

## Licença

MIT. Feito pela [INEMA.CLUB](https://inema.club): conteúdo aberto e gratuito.
