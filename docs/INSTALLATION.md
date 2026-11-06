🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# Installation

## Requirements

- Home Assistant with YAML packages, templates, `command_line`, and `shell_command`.
- Python 3 in the environment running Home Assistant; SQLite is included with Python.
- [button-card](https://github.com/custom-cards/button-card), installed and registered as a JavaScript resource, for the existing dashboard design.
- [card-mod](https://github.com/thomasloven/lovelace-card-mod), installed and registered as a JavaScript resource, to style native cards in the parents' dashboard.
- Local module `/local/level_up_family/level-up-family-cards.js?v=2.7.0`, which registers the cards included in this repository.
- Access to `/config` and write permissions for Home Assistant in `/config/level_up_family/data`.

The game uses YAML packages and a small local integration for family management. Copy `custom_components/level_up_family` as well; this integration is **not installed through HACS**. Local validation checks syntax and references. You must still validate configuration against your installed HA version and visually check its cards.

## New installation

To configure one or more children and their names, first use the [family generator](FAMILY_CONFIGURATION.md). In the steps below, use its generated `config/` folder and `configuration.fragment.yaml` instead of the fixed two-player example.

1. Create a Home Assistant backup.
2. Copy the contents of `config/` into `/config/`, keeping the directory structure. Do not replace your `configuration.yaml`.
3. Merge the includes from `examples/configuration.yaml` into existing sections. If you already use `homeassistant.packages`, retain a single include covering `packages/level_up_family`. Weekly closes are in `lf_weekly.yaml`; do not duplicate them in `automations.yaml`.
4. Initialize the new database inside the HA environment:

   ```sh
   python3 /config/level_up_family/python/luf_db.py init
   ```

   This creates `/config/level_up_family/data/luf.db` using the players in `family.json`. The example includes `player1` and `player2` with 20 tasks; the generator creates ten slots per registered child. Edit them afterwards in the parents' dashboard.

5. Check configuration using Home Assistant's tools, then restart only if validation succeeds. Make sure the Python commands run in the same environment as HA; an add-on terminal may have a different interpreter or permissions.
6. Set `input_number.luf_season_number` to `1` and `input_datetime.luf_season_start` to your chosen date. Adjust XP and penalty rules through their helpers. Set each child's weekly XP goal from the parents' Control tab; see [Weekly goals](WEEKLY_GOALS.md). The start date counts as the first of 28 calendar days; the last day is start + 27 days.
7. Verify that `input_boolean.luf_maintenance` is off. Each active player's dashboard should display level 1, XP 0, and pending missions on a new installation. Test seasons, missions, penalties, and history using test data, with a backup, before regular use.

The example dashboard URLs are `/level-up-family-player1/player1-luf`, `/level-up-family-player2/player2-luf`, and `/level-up-family-parents/control-luf`. The second parents' tab is `historico-luf`. `require_admin` restricts navigation to the parents' dashboard; it does not turn scripts and helpers into a per-player permissions system.

Family management is at `/level-up-family-parents/family` in the example. Register `/level-up-family-children` even when it has no views yet; it is used for future additions. The family management action checks administrator status on the server, but does not add individual permissions to older game scripts.

The prior functionality was checked on **HA 2026.10.4**, integration **0.4.1**, and cards **2.5.1**. This revision uses integration **0.6.0** with individual weekly XP goals. The example uses the `luf` namespace; existing installations can retain their legacy entity bindings when applying this feature. See [Repository Namespace](REPOSITORY_NAMESPACE.md) and validate your own configuration before installing.

## Resets and cleanup

`prepare_reset.py` first generates a plan and requires an explicit apply operation before deleting activity. Read `--help` before using it. It preserves players, validates the schema, creates an SQLite backup, and clears days, weeks, years, and penalties.

The utility affects SQLite only. It does not reset HA helpers, task bitmasks, or activate a new season. A complete reset must also reset counters, weekly checkmarks, and closing dates while retaining task definitions and rules. Stop Home Assistant and all other writers during offline cleanup; closing the browser is insufficient. Keep a complete backup to restore the combined state.

## Current customization

Names, additions, and retirements are managed in **Family**. Reactivation is not available in this version. The [family generator](FAMILY_CONFIGURATION.md) prepares the initial installation while preserving internal identities.

Open **Tasks & Rewards** in the parents' dashboard to edit names, XP, assigned player, days, and weekly reward. See [Tasks & Rewards](TASKS_AND_REWARDS.md) for progress-protection rules. Personal phone notifications have been removed from this distribution. Player names are generic in SQLite keys and entity IDs as well.

Files in `www/level_up_family/season_01` are served at `/local/level_up_family/season_01`. Do not store private data in `www`.

---

<a id="español"></a>

# Instalación

## Requisitos

- Home Assistant con paquetes YAML, plantillas, command_line y shell_command.
- Python 3 en el entorno donde se ejecuta Home Assistant; SQLite forma parte de Python.
- La tarjeta [button-card](https://github.com/custom-cards/button-card), instalada y registrada como recurso JavaScript, para el diseño existente de los paneles.
- [card-mod](https://github.com/thomasloven/lovelace-card-mod), instalado y registrado como recurso JavaScript, para aplicar el estilo de Level Up Family a las tarjetas nativas del panel de padres.
- El módulo local `/local/level_up_family/level-up-family-cards.js?v=2.7.0`, que registra las tarjetas incluidas en este repositorio.
- Acceso al directorio `/config` y permisos de escritura para Home Assistant en `/config/level_up_family/data`.

El juego utiliza paquetes YAML y una pequeña integración local para administrar la familia. Copia también `custom_components/level_up_family`; no se instala desde HACS. La validación local comprueba sintaxis y referencias; la comprobación de configuración de la versión de Home Assistant instalada y la revisión visual de sus tarjetas siguen siendo necesarias.

## Instalación nueva

Para configurar uno o más hijos y sus nombres, utiliza primero el [generador familiar](FAMILY_CONFIGURATION.md). En los pasos siguientes, usa su carpeta `config/` y su `configuration.fragment.yaml` en lugar del ejemplo fijo de dos jugadores.

1. Haz una copia de seguridad de Home Assistant.
2. Copia el contenido de `config/` en `/config/`, conservando las carpetas. No reemplaces tu `configuration.yaml`.
3. Combina las inclusiones de `examples/configuration.yaml` con las secciones existentes. Si ya usas `homeassistant.packages`, conserva una sola inclusión que alcance `packages/level_up_family`. Los cierres semanales están en `lf_weekly.yaml`; no debes duplicarlos en `automations.yaml`.
4. En el entorno de Home Assistant, inicializa la base nueva:

   ```sh
   python3 /config/level_up_family/python/luf_db.py init
   ```

   Se crea `/config/level_up_family/data/luf.db` con los jugadores de `family.json`. La copia de ejemplo contiene `player1` y `player2`, con 20 tareas; el generador prepara diez espacios por hijo registrado. Después se editan desde padres.

5. Comprueba la configuración con las herramientas de Home Assistant y reinícialo si es válida. Asegúrate de que los comandos Python se ejecutan en el mismo entorno que Home Assistant; una terminal de un complemento puede tener otro intérprete o permisos.
6. Establece `input_number.luf_season_number` en `1` y `input_datetime.luf_season_start` en la fecha elegida. Ajusta las reglas de XP y penalizaciones desde sus helpers. El objetivo semanal de XP de cada hijo se guarda desde Control en el panel de padres; consulta [Objetivos semanales](WEEKLY_GOALS.md). La fecha determina 28 días naturales, incluyendo el inicio; el último día es inicio + 27 días.
7. Revisa que `input_boolean.luf_maintenance` esté apagado. Cada panel activo debe mostrar nivel 1, XP 0 y misiones pendientes en una instalación nueva. Comprueba temporada, misiones, penalizaciones e histórico con datos de prueba y una copia de seguridad antes de usarlos de forma habitual.

Los enlaces de paneles son `/level-up-family-player1/player1-luf`, `/level-up-family-player2/player2-luf` y `/level-up-family-parents/control-luf`. La segunda pestaña de padres es `historico-luf`. `require_admin` restringe la navegación al panel de padres; no convierte los scripts o helpers en un sistema de permisos por jugador.

En el ejemplo, la gestión de hijos está en `/level-up-family-parents/family`. Debe estar registrado también `/level-up-family-children`, aunque todavía no tenga vistas: se utilizará para las altas futuras. La acción de gestión de familia exige administrador en el servidor; esto no añade permisos individuales a los scripts antiguos del juego. La funcionalidad previa se comprobó en HA 2026.10.4, integración 0.4.1 y tarjetas 2.5.1. Esta revisión usa integración 0.6.0 y objetivos semanales de XP por hijo. El ejemplo utiliza el prefijo `luf`; una instalación existente puede conservar sus identificadores anteriores al aplicar esta función. Consulta [Nomenclatura](REPOSITORY_NAMESPACE.md) y comprueba la configuración antes de instalar.

## Reinicios y limpieza

`prepare_reset.py` genera primero un plan y requiere una aplicación explícita para borrar actividad. Consulta `--help` antes de usarlo. Conserva los jugadores y valida el esquema, crea una copia SQLite y limpia días, semanas, años y penalizaciones.

La utilidad actúa únicamente sobre SQLite. No reinicia los helpers de Home Assistant, no cambia los bitmasks de misiones y no pone una temporada en producción por sí sola. Para un reinicio completo hay que guardar y reiniciar también los contadores, las marcas semanales y las fechas de cierre, manteniendo las definiciones de misiones y las reglas. Detén Home Assistant y cualquier otro escritor durante la limpieza offline; no basta con cerrar el navegador. Conserva una copia completa para poder restaurar el estado conjunto.

## Personalización actual

Los nombres, las altas y las retiradas se gestionan desde **Familia**. No hay una acción de reactivación en esta versión. El [generador familiar](FAMILY_CONFIGURATION.md) prepara la instalación inicial y conserva las identidades internas.

Abre **Tareas y premios** en el panel de padres para cambiar nombres, XP, jugador, días y premio semanal. Consulta [Tareas y premios](TASKS_AND_REWARDS.md) para las reglas de protección del progreso. Las notificaciones a teléfonos personales se han retirado de esta distribución. Los nombres de jugador son genéricos también en las claves SQLite y en los identificadores de entidades.

Los recursos de `www/level_up_family/season_01` se sirven en `/local/level_up_family/season_01`. No guardes datos privados en `www`.
