🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# How it works

## Game state

Home Assistant stores weekly mission completion in numeric helpers: each bit represents a day, from Monday (`1`) to Sunday (`64`). Sensors derive XP, progress, goals, and levels. `task_defaults.json` provides initial values, while `lf_tasks.yaml` merges them with editable metadata persisted in text helpers to publish `sensor.luf_task_catalog`.

Dashboards, calculations, and closing processes read that catalog. Configuration changes and mark, unmark, or toggle operations are serialized through `script.luf_task_mutate`. Before writing, it validates form revision, types, bounds, active week, player, and day. Changes to task rules are rejected once progress exists; the task name remains editable.

Reassignment preserves the mission's physical helper. Each weekly close resets only the tasks assigned to the player being closed, even if their entities retain an earlier name. This avoids clearing another player's missions. Legacy difficulty-based XP helpers remain for compatibility; task XP now comes from the catalog.

`lf_core.yaml` contains shared rules and access scripts. `lf_player1.yaml` and `lf_player2.yaml` group each player's helpers, sensors, actions, and daily closes. `lf_weekly.yaml` initializes and closes the week, including startup recovery. `lf_season.yaml` calculates status and dates for a 28-day season. `lf_themes.yaml` defines seasonal presentation.

## Persistence

`luf_db.py` stores players, days, weeks, years, and penalties in SQLite. Closing operations use unique keys and updates to avoid duplicating activity if run more than once. Individual missions are not stored in SQLite in this release.

`luf_history.py` and `luf_active_penalties.py` read the database for history and active-penalty sensors. Their JSON responses surface errors rather than fabricating results. `lf_database.yaml` connects script writes to Python commands; `lf_history.yaml` and `lf_admin.yaml` connect reads and penalty controls.

Writing scripts check the maintenance helper. The daily close also checks the season start date and the week to which mission data belongs. Season calculations report the current period; moving to another season and migrating its assets are not automatic.

## Dashboards

Player dashboards contain only their Level Up Family view. The parents' dashboard contains Control, History, Tasks & Rewards, and Family. The local `level-up-family-cards.js` module registers administration, mission, reward, and family cards using Home Assistant's `hass` object and text nodes for names and rewards. It contains no general home-automation tabs or references to household devices. Newly added players appear as views in the shared children's dashboard.

## Family management

`custom_components/level_up_family` loads version 2 of `family.json`, publishes `sensor.luf_family`, and registers `level_up_family.manage_family` with server-side administrator authorization. Its registry separates public player ID, display name, entity prefix, SQLite key, and dashboard path. Engine commands also accept the initial version 1 format; the UI requires version 2.

Operations are serialized with a lock and validate the registry revision. Renaming or retiring a player updates metadata, preserves numeric SQLite identities, and keeps activity tables. Retired children are excluded from the active task catalog and closes, but remain visible in history and any outstanding penalties can still be viewed. When dashboards are updated, game views are replaced with their templates; other views and general settings are preserved.

An addition is prepared with a token that expires after ten minutes. Applying it places the game in maintenance mode, waits for scripts to finish, backs up SQLite and helpers, generates the new player's package, and extends tasks and automations. It validates the HA configuration and saves `family_pending.json` before restarting. On startup, it restores helper values, checks the new player's entities, synchronizes SQLite, and updates dashboards before restoring the previous maintenance state. Incomplete recovery keeps maintenance enabled and reports the error.

`templates.json` contains generic templates used for dashboards and provisioning. Rebuild it with `python tools/build_family_templates.py`; a test verifies alignment with source YAML and initial values. Styling changes to managed views must update this generated file as well.

## Compatibility

Repository components consistently use the `luf_` prefix. Public keys are stable IDs such as `player1`, `player2`, and `player3`; `family.json` defines display names and active state. The `tools/configure_family.py` generator produces a complete setup from a private file, using the included two-player configuration as templates. Changing a display name preserves identity; changing an internal key in an existing installation requires migrating state. See [Repository Namespace](REPOSITORY_NAMESPACE.md) before updating an older setup.

---

<a id="español"></a>

# Funcionamiento

## Estado de juego

Home Assistant mantiene las misiones semanales en helpers numéricos: cada bit representa un día, del lunes (`1`) al domingo (`64`). Los sensores derivan XP, progreso, objetivos y nivel. `task_defaults.json` aporta los valores iniciales y `lf_tasks.yaml` los combina con los metadatos editables persistidos en helpers de texto para publicar `sensor.luf_task_catalog`.

Los paneles, cálculos y cierres consumen ese catálogo. Los cambios de configuración y las acciones de marcar, desmarcar o alternar se serializan en `script.luf_task_mutate`. Antes de escribir se comprueban la revisión del formulario, tipos, límites, semana activa, jugador y día. Cambiar reglas de una tarea con progreso se rechaza; su nombre sigue siendo editable.

La reasignación mantiene el helper físico de la misión. Cada cierre semanal reinicia únicamente las tareas asignadas al jugador que está cerrando, aunque sus entidades conservaran un nombre anterior. Así se evita borrar misiones del otro jugador. Los helpers antiguos de XP por dificultad se conservan por compatibilidad; los XP de cada tarea proceden ahora del catálogo.

`lf_core.yaml` contiene reglas compartidas y scripts de acceso. `lf_player1.yaml` y `lf_player2.yaml` reúnen los helpers, sensores, acciones y cierres diarios de cada jugador. `lf_weekly.yaml` inicializa la semana y programa su cierre, incluyendo recuperación al arrancar. `lf_season.yaml` calcula el estado y las fechas de una temporada de 28 días. `lf_themes.yaml` define la presentación de la temporada.

## Persistencia

`luf_db.py` mantiene jugadores, días, semanas, años y penalizaciones en SQLite. Los cierres usan claves únicas y actualizaciones para evitar duplicar actividad al repetirse. Las misiones no se guardan en SQLite en esta versión.

`luf_history.py` y `luf_active_penalties.py` leen la base para los sensores de histórico y penalizaciones activas. Sus respuestas JSON permiten mostrar errores sin inventar resultados. `lf_database.yaml` enlaza las escrituras de los scripts con los comandos Python; `lf_history.yaml` y `lf_admin.yaml` enlazan las lecturas y el control de penalizaciones.

Los scripts que escriben comprueban el helper de mantenimiento. El cierre diario comprueba además la fecha de inicio de temporada y la semana a la que pertenecen las misiones. El cálculo de temporada informa del período; no hay un cambio automático a una temporada nueva ni una migración de sus recursos.

## Paneles

Los paneles de jugador incluyen únicamente su pestaña Level Up Family. El panel de padres contiene Control, Histórico, Tareas y premios y Familia. El módulo local `level-up-family-cards.js` registra las tarjetas de administración, misiones, premio y familia, usando el objeto `hass` de Home Assistant y nodos de texto para los nombres y recompensas. No hay pestañas de domótica general ni referencias a dispositivos de la casa. Los nuevos jugadores aparecen como vistas del panel compartido de hijos.

## Gestión de familia

`custom_components/level_up_family` carga `family.json` de versión 2, publica `sensor.luf_family` y registra la acción `level_up_family.manage_family` con autorización de administrador en el servidor. Su registro mantiene separados el identificador público, el nombre visible, el prefijo de entidades, la clave SQLite y la ruta de panel. Los comandos del motor aceptan también el formato inicial de versión 1; la interfaz requiere la versión 2.

Las operaciones se serializan mediante un bloqueo y validan la revisión del registro. Cambiar nombre o retirar actualiza metadatos, conserva las identidades numéricas de SQLite y mantiene las tablas de actividad. Los hijos retirados quedan fuera del catálogo y los cierres activos, pero siguen en el histórico y sus multas pendientes continúan consultables. Al actualizar paneles se sustituyen las vistas del juego por sus plantillas; las otras vistas y los ajustes generales se conservan.

Una alta se prepara con un token que caduca a los diez minutos. Aplicarla pone el juego en mantenimiento, espera a que terminen los scripts, copia SQLite y los helpers, genera el paquete del nuevo jugador y amplía tareas y automatizaciones. Después valida la configuración de HA y guarda `family_pending.json` antes del reinicio. Al arrancar restaura helpers, comprueba las entidades del nuevo jugador, sincroniza SQLite y actualiza paneles antes de recuperar el estado previo de mantenimiento. Una recuperación incompleta mantiene el juego en mantenimiento y publica el error.

`templates.json` contiene las plantillas genéricas utilizadas para generar paneles y altas. Se reconstruye con `python tools/build_family_templates.py`; una prueba verifica que coincide con los YAML y valores iniciales de origen. El cambio de estilo de las vistas administradas debe actualizar también este archivo generado.

## Compatibilidad

Los componentes del repositorio utilizan el prefijo `luf_` de forma coherente. Las claves públicas son identificadores estables como `player1`, `player2` y `player3`; el nombre visible y estado activo se describen en `family.json`. El generador `tools/configure_family.py` prepara la configuración completa desde un archivo privado, usando los dos jugadores incluidos como plantillas. Cambiar un nombre visible conserva la identidad; cambiar una clave interna de una instalación existente requiere migrar el estado. Consulta [Nomenclatura](REPOSITORY_NAMESPACE.md) antes de actualizar una instalación anterior.
