# Espera sin ti

[![Espera sin ti](guia/assets/banner-es.jpg)](https://inematds.github.io/espera-sem-voce/guia/es/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## Qué es

**Quieres pedirle un trabajo largo a la IA, irte a hacer tu vida y recibir solo el aviso de que terminó.** Este kit gratuito explica, con diagramas animados, las tres formas que usan los sistemas de INEMA para esperar entre una fase y otra: un **vigía** que revisa cada cierto tiempo y abre una conversación nueva con la IA cuando todo está listo, un **flujo con compuerta** que se detiene y espera tu "puedes seguir", y una **cola que retoma** el trabajo después de una caída. También incluye un vigía listo para que lo uses. Para empezar, basta con pegar un pedido en Claude Code o en Codex.

## 📖 Guía de uso

Guía completa (landing + diagramas animados): **https://inematds.github.io/espera-sem-voce/guia/es/**

## Cómo empezar (sin instalar nada a mano)

Abre Claude Code o Codex en la carpeta de tu proyecto y pega:

> Lee el repositorio https://github.com/inematds/espera-sem-voce (el README y la carpeta vigia). Después revisa mi proyecto y pregúntame qué trabajos tardan (video, render, transcripción, generador externo) y cómo los espero hoy. Dime, en lenguaje sencillo, cuál de las tres formas sirve para cada uno (vigía, flujo con compuerta o cola que retoma), cuánto tiempo dejaría de estar con la conversación abierta y qué haría falta para que el vigía sepa preguntar "¿ya está listo?". No instales ni cambies nada antes de mi sí. Con mi sí: copia el vigía de ejemplo, ejecuta su prueba y arma la primera nota y la primera verificación para un trabajo mío.

## Las tres formas de esperar

| | Vigía | Flujo con compuerta | Cola que retoma |
|---|---|---|---|
| Quién espera | un programa aparte, sin IA | el propio bot, fase por fase | el propio asistente, tarea por tarea |
| Sirve para | trabajo de una sola vez iniciado en una conversación con la IA | producción que se repite, con aprobación en el medio | pedidos del día a día que deben sobrevivir a un reinicio |
| Revisa | cada 5 min | cada 1 a 5 min (definido por fase) | especialistas cada 15–20 s; señal de vida cada 30 s |
| Se rinde | 8 h sin estar listo (ajustable) | en el límite de cada fase (1 h a 40 h; 10 h en r7ex, 40 h en el avatar de promoavatar) | pedido de chat/agente: 1 intento; si se cae → `failed` + aviso, se retoma con `/job N`. Tarea programada: 2 intentos (nuevo intento tras 30 s) |
| Aprobación en el medio | no (las órdenes van en la nota) | sí, en la compuerta | no; retomar después con `/job` |
| Origen | vigía `continua` (proyecto interno, privado) → copia en [`vigia/`](vigia/) | [inemaccbot](https://github.com/inematds/inemaccbot) | [openpcbotv3](https://github.com/inematds/openpcbotv3) |

---

## Instalación técnica

### Requisitos previos

- Linux o macOS con Python 3.9+ (solo biblioteca estándar). Timer: systemd de usuario en Linux; en macOS, `cron` (`*/5 * * * * python3 …/vigia.py rodada`).
- La máquina permanece encendida y sin suspenderse mientras espera (una laptop con la tapa cerrada suele dormirse).
- Para la fase 2 por defecto: `claude` (Claude Code) con sesión iniciada mediante la suscripción. Puedes cambiarlo por cualquier comando con `VIGIA_FASE2` (ej.: `codex exec`).
- Opcional: systemd de usuario para el timer (o cron).

### Probar el vigía (pocos segundos, sin IA)

```bash
git clone https://github.com/inematds/espera-sem-voce && cd espera-sem-voce
bash vigia/testar.sh        # 5 de 5 ok
```

La prueba cubre: (1) no está listo → sigue esperando; (2) listo → abre la fase 2 → cierra como hecho; (3) superó el límite → se detiene y avisa; (4) la fase 2 superó las 3 h → se termina y se avisa.

### Usarlo con un trabajo tuyo

```bash
# 1. en la carpeta del trabajo, la nota de la fase 2 (lo que falta, órdenes, candados)
mkdir -p ~/trabalhos/video-x && cp vigia/CONTINUAR.exemplo.md ~/trabalhos/video-x/CONTINUAR.md

# 2. registrar: --confere es cualquier comando cuya ÚLTIMA línea sea "pronto" cuando esté listo
python3 vigia/vigia.py add ~/trabalhos/video-x \
  --confere '[ -f saida/final.mp4 ] && echo pronto || echo aguardando' --teto-h 8

# 3. el timer llama a la ronda cada 5 min
mkdir -p ~/.config/systemd/user && cp vigia/systemd/vigia.service vigia/systemd/vigia.timer ~/.config/systemd/user/
# vigia.service supone que el kit está en ~/espera-sem-voce: ajusta la ruta de vigia.py si lo clonaste en otro lugar
systemctl --user daemon-reload && systemctl --user enable --now vigia.timer

# 4. quién vigila al vigía: inspección cada hora (solo avisa si hay un problema) + informe a las 08:00
cp vigia/systemd/vistoria-*.service vigia/systemd/vistoria-*.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now vistoria-hora.timer vistoria-dia.timer

python3 vigia/vigia.py status      # última ronda + la cadena de intentos de cada trabajo
python3 vigia/vistoria.py ver      # el informe, sin avisar
```

**Nuevo intento = misma cadena.** Registrar de nuevo el mismo `--nome` después de fallar, detenerse o terminar abre el siguiente intento de la misma cadena: el ID de la cadena se mantiene, el intento recibe un número (`video-x#t2` en todos los avisos y en el log), el anterior pasa al historial con su resultado, y el `CONTINUAR.resultado` antiguo pasa a ser `CONTINUAR.resultado.t1` (el intento nuevo nunca hereda el resultado del otro). Lo que cambió se anota automáticamente mediante el hash de `CONTINUAR.md`: igual = "mesma entrada, nova chance" (misma entrada, nueva oportunidad); distinto = el texto de `--mudou "<qué>"`. `status` muestra la cadena completa, una línea por intento. Dentro de la fase 2, cada paso rehecho se convierte en una línea `REFEITO: <paso> — <qué cambió>` en el resultado. Las revisiones también acompañan: la de cada hora cita el intento (`nome#tN`) en cada problema, y el informe del día cuenta todos los intentos que terminaron en las últimas 24 h y lista las cadenas con un intento nuevo, con lo que cambió en cada una, avisando cuando la misma entrada volvió a fallar.

Variables: `VIGIA_ESTADO` (archivo de estado), `VIGIA_FASE2` (comando de la fase 2, recibe `$PASTA`), `VIGIA_AVISO` (comando que avisa, recibe `$MSG`). Sin `VIGIA_AVISO` el aviso solo va al log; para que llegue a tu celular, conecta tu bot de Telegram:

```bash
export VIGIA_AVISO='curl -s "https://api.telegram.org/bot$TG_TOKEN/sendMessage" --data-urlencode chat_id=$TG_CHAT --data-urlencode text="$MSG" > /dev/null'
```

El timer de systemd no ve el `export` de la terminal: pon la misma línea en `vigia.service` (y en los dos `vistoria-*.service`) como `Environment=VIGIA_AVISO=...` (con `TG_TOKEN` y `TG_CHAT`), o en un `EnvironmentFile=`, y ejecuta `systemctl --user daemon-reload`.

**Permiso de la fase 2:** el valor por defecto es `claude -p --permission-mode bypassPermissions`, porque sin nadie frente a la pantalla no puede detenerse a pedir permiso. La nota es la autorización: ejecútalo en una carpeta exclusiva del trabajo y escribe los candados en `CONTINUAR.md`. ¿Quieres otro motor? `VIGIA_FASE2='codex exec --full-auto "Leia $PASTA/CONTINUAR.md …"'`.

### Archivos

| Archivo | Qué es |
|---|---|
| `vigia/vigia.py` | el vigía (add, rodada, status) |
| `vigia/vistoria.py` | quién vigila al vigía (hora, dia, ver) |
| `vigia/testar.sh` | prueba sin IA, 5 casos |
| `vigia/CONTINUAR.exemplo.md` | modelo de la nota de la fase 2 |
| `vigia/systemd/` | timer cada 5 min + inspección cada hora y a las 08:00 |
| `guia/` | la página con los diagramas animados (PT, `en/`, `es/`) |

### Plazos del vigía

| Qué | Plazo | Si se supera |
|---|---|---|
| Revisar | cada 5 min (timer) | — |
| Una verificación | hasta 25 min | cuenta como "todavía no" |
| Espera | 8 h (`--teto-h`) | 🟥 aviso "esperó N h" |
| Trabajo muerto (`--log` detenido y ningún proceso de la carpeta) | 20 min | 🟥 aviso antes del límite |
| Fase 2 | hasta 3 h (revisado en la ronda) | 🟥 si supera las 3 h o termina sin `CONTINUAR.resultado` |
| Vigía detenido (`ultima-rodada` sin cambios) | 15 min, revisado cada hora por `vistoria.py` | 🟥 aviso de la inspección (se repite como máximo cada 6 h) y ✅ cuando vuelve |
| Trabajo olvidado / fase 2 desaparecida | tope + 30 min / proceso muerto hace 15 min | 🟥 aviso de la inspección |
| Informe del día | 08:00 | si no llega, se cayó la máquina |

### Dónde está cada pieza en los proyectos de origen

- **Flujo con compuerta (inemaccbot):** fase de espera = `espera: {intervalo, timeout}` en `src/dominio/flow.ts`; compuerta = `pausa_apos`; la fase que descarga el video de HeyGen, encontrándolo por el título (lo que permite retomar después de una caída), en `src/fila/tarefas/heygen.ts`. Cómo conectarlo: `docs/plugar-fluxo.md`.
- **Cola que retoma (openpcbotv3):** estados `queued | running | done | failed | canceled` en `src/fila/types.ts`; lease de 120 s renovado cada 30 s en `src/index.ts`; un lease vencido vuelve a `queued` si todavía quedan intentos; si no, pasa a `failed` con aviso (`recuperarLeasesVencidos` en `src/fila/store.ts`). Los pedidos de chat y agente entran con `max_tentativas: 1` (`src/orquestrador/orquestrador.ts`); las tareas programadas con 2, y el nuevo intento espera 30 s × 2ⁿ⁻¹. El líder espera a los especialistas con `aindaNao` cada 15–20 s (`src/orquestrador/tarefas-fila.ts`); `/status` y `/job N continue de onde parou` en `src/orquestrador/comandos.ts`.
- **Vigía (continua):** repositorio privado de INEMA; el diseño está reproducido aquí en `vigia/vigia.py`, sin las partes propias de la máquina (aviso en el bot, cola en serie, motor de IA configurable). La inspección de allá (`continua/vistoria.py`, desde el 25/11/2026) lee el journal de systemd en lugar del archivo `ultima-rodada`; la de aquí usa el archivo para funcionar también con cron en macOS.

## El proceso, de principio a fin

🧠 = sesión contigo · ⚙️ = script/timer · 🤖 = `claude -p` (suscripción)

| # | Paso | Comando / qué sucede | Quién |
|---|---|---|---|
| 1 | Fase 1 | la IA hace la parte que requiere pensar (guion, aprobación) y lanza el trabajo que tarda | 🧠 |
| 2 | Nota | escribe `<pasta>/CONTINUAR.md`: lo que falta, tus órdenes citadas, los candados | 🧠 |
| 3 | Registrar | `vigia.py add <pasta> --confere "<cmd>" [--teto-h 8] [--mudou "…"]` → aviso "Fase 1 concluída, pode fechar" | 🧠 |
| 4 | Esperar | el timer ejecuta `vigia.py rodada` cada 5 min; ninguna IA encendida | ⚙️ |
| 5 | Listo | última línea de `--confere` = `pronto` → abre la fase 2 (hasta 3 h) | ⚙️ |
| 6 | Fase 2 | la IA nueva lee solo `CONTINUAR.md`, termina y guarda `CONTINUAR.resultado` | 🤖 |
| 7 | Cerrar | el vigía lee el resultado y avisa: ✅ hecho o 🟥 falló (también al llegar al límite y con trabajo muerto) | ⚙️ |
| 8 | Inspección | `vistoria.py hora` cada hora: vigía detenido, trabajo olvidado, fase 2 desaparecida → 🟥; `vistoria.py dia` a las 08:00 manda el informe | ⚙️ |

## Licencia

MIT. Hecho por [INEMA.CLUB](https://inema.club): contenido abierto y gratuito.
