# Espera sin ti

[![Espera sin ti](guia/assets/banner-es.jpg)](https://inematds.github.io/espera-sem-voce/guia/es/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## Qué es

**Quieres pedirle un trabajo largo a la IA, ocuparte de tus cosas y recibir solo el aviso de que terminó.** Este kit gratuito explica, con diagramas animados, las tres formas que usan los sistemas de INEMA para esperar entre una fase y otra: un **vigía** que revisa cada cierto tiempo y abre una conversación nueva con la IA cuando el trabajo está listo, un **flujo con compuerta** que se detiene y espera tu "puedes seguir", y una **cola que retoma** el trabajo después de una caída. También incluye un vigía listo para que lo uses. Para empezar, basta con pegar un pedido en Claude Code o en Codex.

## 📖 Guía de uso

Guía completa (landing + diagramas animados): **https://inematds.github.io/espera-sem-voce/guia/es/**

## Cómo empezar (sin instalar nada a mano)

Abre Claude Code o Codex en la carpeta de tu proyecto y pega:

> Lee el repositorio https://github.com/inematds/espera-sem-voce (el README y la carpeta vigia). Después revisa mi proyecto y pregúntame qué trabajos tardan (video, render, transcripción, generador externo) y cómo espero hoy. Dime, en lenguaje sencillo, cuál de las tres formas sirve para cada uno (vigía, flujo con compuerta o cola que retoma), cuánto tiempo dejaría de tener la conversación abierta y qué haría falta para que el vigía sepa preguntar "¿ya está listo?". No instales ni cambies nada antes de que te diga que sí. Cuando te diga que sí: copia el vigía de ejemplo, ejecuta su prueba y arma la primera nota y la primera comprobación para un trabajo mío.

## Las tres formas de esperar

| | Vigía | Flujo con compuerta | Cola que retoma |
|---|---|---|---|
| Quién espera | un programa aparte, sin IA | el propio bot, fase por fase | el propio asistente, tarea por tarea |
| Sirve para | un trabajo puntual iniciado en una conversación con la IA | producción que se repite, con aprobación en el medio | pedidos del día a día, con errores pasajeros |
| Revisa | cada 5 min | cada 1 a 5 min (definido por fase) | señal de vida cada 30 s |
| Se rinde | 8 h sin estar listo (ajustable) | en el límite de la fase (10 h en r7ex, 40 h en el avatar largo) | después de los intentos (30 s × 2ⁿ entre ellos) |
| Aprobación en el medio | no (las órdenes van en la nota) | sí, en la compuerta | no; se retoma después con `/job` |
| Origen | vigía `continua` (proyecto interno, privado) → copia en [`vigia/`](vigia/) | [inemaccbot](https://github.com/inematds/inemaccbot) | [openpcbotv3](https://github.com/inematds/openpcbotv3) |

---

## Instalación técnica

### Requisitos previos

- Linux o macOS con Python 3.9+ (solo biblioteca estándar).
- Para la fase 2 por defecto: `claude` (Claude Code) con sesión iniciada mediante la suscripción. Puedes cambiarlo por cualquier comando con `VIGIA_FASE2` (ej.: `codex exec`).
- Opcional: systemd de usuario para el timer (o cron).

### Probar el vigía (2 s, sin IA)

```bash
git clone https://github.com/inematds/espera-sem-voce && cd espera-sem-voce
bash vigia/testar.sh        # 3 de 3 ok
```

La prueba cubre: (1) no está listo → sigue esperando; (2) listo → abre la fase 2 → cierra como hecho; (3) superó el tope → se detiene y avisa.

### Usarlo con un trabajo tuyo

```bash
# 1. en la carpeta del trabajo, la nota de la fase 2 (lo que falta, órdenes, candados)
cp vigia/CONTINUAR.exemplo.md ~/trabalhos/video-x/CONTINUAR.md

# 2. registrar: --confere es cualquier comando cuya ÚLTIMA línea sea "pronto" cuando esté listo
python3 vigia/vigia.py add ~/trabalhos/video-x \
  --confere '[ -f saida/final.mp4 ] && echo pronto || echo aguardando' --teto-h 8

# 3. el timer ejecuta la ronda cada 5 min
cp vigia/systemd/vigia.service vigia/systemd/vigia.timer ~/.config/systemd/user/
# ajusta la ruta de vigia.py en vigia.service
systemctl --user daemon-reload && systemctl --user enable --now vigia.timer

python3 vigia/vigia.py status
```

Variables: `VIGIA_ESTADO` (archivo de estado), `VIGIA_FASE2` (comando de la fase 2, recibe `$PASTA`), `VIGIA_AVISO` (comando que avisa, recibe `$MSG`, por ejemplo un `curl` hacia tu bot de Telegram).

### Archivos

| Archivo | Qué es |
|---|---|
| `vigia/vigia.py` | el vigía (add, rodada, status) |
| `vigia/testar.sh` | prueba sin IA, 3 casos |
| `vigia/CONTINUAR.exemplo.md` | modelo de la nota de la fase 2 |
| `vigia/systemd/` | timer cada 5 min |
| `guia/` | la página con los diagramas animados (PT, `en/`, `es/`) |

### Plazos del vigía

| Qué | Plazo | Si se pasa |
|---|---|---|
| Revisar | cada 5 min (timer) | — |
| Una comprobación | hasta 25 min | cuenta como "todavía no" |
| Espera | 8 h (`--teto-h`) | 🟥 aviso "esperó N h" |
| Trabajo muerto (`--log` detenido y ningún proceso de la carpeta) | 20 min | 🟥 aviso antes del tope |
| Fase 2 | hasta 3 h | 🟥 si termina sin `CONTINUAR.resultado` |

### Dónde está cada pieza en los proyectos de origen

- **Flujo con compuerta (inemaccbot):** fase de espera = `espera: {intervalo, timeout}` en `src/dominio/flow.ts`; compuerta = `pausa_apos`; la fase que descarga el video de HeyGen, encontrándolo por el título (lo que permite retomar después de una caída), en `src/fila/tarefas/heygen.ts`. Cómo conectarlo: `docs/plugar-fluxo.md`.
- **Cola que retoma (openpcbotv3):** estados `queued | running | done | failed | canceled` en `src/fila/types.ts`; lease de 120 s renovado cada 30 s y nuevo intento con espera de 30 s × 2ⁿ en `src/fila/store.ts`; `aindaNao` reprograma sin gastar un intento; `/status` y `/job N continue` en `src/orquestrador/comandos.ts`.
- **Vigía (continua):** repositorio privado de INEMA; el diseño está reproducido aquí en `vigia/vigia.py`, sin las partes propias de la máquina (aviso en el bot, cola en serie, motor de IA configurable).

## El proceso, de principio a fin

🧠 = sesión contigo · ⚙️ = script/timer · 🤖 = `claude -p` (suscripción)

| # | Paso | Comando / qué sucede | Quién |
|---|---|---|---|
| 1 | Fase 1 | la IA hace la parte que requiere pensar (guion, aprobación) y lanza el trabajo que tarda | 🧠 |
| 2 | Nota | escribe `<pasta>/CONTINUAR.md`: lo que falta, tus órdenes citadas, los candados | 🧠 |
| 3 | Registrar | `vigia.py add <pasta> --confere "<cmd>" [--teto-h 8]` → aviso "Fase 1 concluida, puedes cerrar" | 🧠 |
| 4 | Esperar | el timer ejecuta `vigia.py rodada` cada 5 min; ninguna IA encendida | ⚙️ |
| 5 | Listo | última línea de `--confere` = `pronto` → abre la fase 2 (hasta 3 h) | ⚙️ |
| 6 | Fase 2 | la IA nueva lee solo `CONTINUAR.md`, termina y guarda `CONTINUAR.resultado` | 🤖 |
| 7 | Cerrar | el vigía lee el resultado y avisa: ✅ hecho o 🟥 falló (también al llegar al tope y ante un trabajo muerto) | ⚙️ |

## Licencia

MIT. Hecho por [INEMA.CLUB](https://inema.club): contenido abierto y gratuito.
