🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# 🎮 Level Up Family

**Turn household routines into missions, and progress into a shared adventure.**

Level Up Family is a household chores game for **Home Assistant**. Each child gets a personal dashboard, completes missions, earns experience points (XP), and follows their progress through **28-day seasons**. Parents manage chores, monitor progress, and choose weekly rewards. It supports one or more children, with customizable names, missions, and prizes.

![Level Up Family Season 1](config/www/level_up_family/season_01/banner.png)

## ✨ Features

### A dashboard for each player

- Seasonal header, background, and visual theme.
- Today's missions, their XP values, and completion checkboxes.
- Weekly XP, level, daily streak, and weekly streak.
- Weekly target, bonuses, penalties, and the reward selected by parents.

Corrections for previous days are made in the parents' dashboard.

### Parents' dashboard

| Tab | What it does |
| --- | --- |
| **Control** | Monitor progress, correct missions in the active week, apply penalties, and cancel them by ID. |
| **History** | View closed weeks and annual summaries stored in SQLite. |
| **Tasks & Rewards** | Edit task name, difficulty, XP, player, days, frequency, and weekly rewards. |
| **Family** | Change display names, prepare new players, and retire players without deleting their history. |

Family management checks administrator status on the server. Other scripts and helpers remain subject to Home Assistant permissions; there is no separate per-child permissions system.

## 🗓️ How a week works

1. Parents configure tasks with a name, assigned player, XP, and applicable days. Some tasks can be completed once across several selected days.
2. Children complete missions and see their progress on their personal dashboards.
3. The default weekly target is **75%** of scheduled missions, and it can be adjusted. Parents choose the weekly reward description.
4. Daily and weekly closing processes calculate results, consolidate XP, update streaks, and store history.

Perfect days and consecutive successful weeks may award bonuses. Penalties subtract XP from the current week, **not** from the consolidated lifetime total; cancelling a penalty retains its record and marks it as cancelled. Weekly and lifetime XP serve different purposes: lifetime XP is consolidated at weekly close.

### Safe task editing

- Task names may be changed even after progress has been recorded.
- XP, scheduled days, frequency, or assigned player may change only if that task has no progress in the active week.
- A task with no selected days is disabled.
- Stale forms are rejected if another session has already saved changes.
- Once-per-week tasks count only once and do not qualify for perfect-day bonuses.

See [Tasks & Rewards](docs/TASKS_AND_REWARDS.md) for details.

## 🚀 Installation

Level Up Family combines **YAML packages, Python scripts, a local integration, and frontend cards**. Installation requires copying files and merging configuration into an existing Home Assistant setup.

### Requirements

- Home Assistant with access to `/config` and support for YAML packages.
- Python 3 and SQLite in the environment running Home Assistant.
- [button-card](https://github.com/custom-cards/button-card) and [card-mod](https://github.com/thomasloven/lovelace-card-mod), installed and registered.
- The included local integration at `config/custom_components/level_up_family`.
- `/local/level_up_family/level-up-family-cards.js?v=2.6.0`, registered as a **JavaScript module**.
- A full backup before changing an existing installation.

**This is not a HACS installation.** HACS can be used for the external frontend cards, but the included local integration must be installed manually.

### Getting started

1. Use the two-player example or the [family configuration generator](docs/FAMILY_CONFIGURATION.md) to set up one or more children.
2. Copy the contents of `config/` into `/config/`, preserving the directory structure. Merge the includes from `examples/configuration.yaml` or the generated snippet into your existing configuration.
3. **For a brand-new installation only**, initialize the database:

   ```sh
   python3 /config/level_up_family/python/luf_db.py init
   ```

4. Register the cards, check Home Assistant's configuration, and restart if validation succeeds.
5. Set `input_number.luf_season_number` and `input_datetime.luf_season_start`.
6. Configure tasks and rewards in the parents' dashboard. Make sure `input_boolean.luf_maintenance` is off when the game is ready.

Read the [full installation guide](docs/INSTALLATION.md). Merge files carefully to preserve existing devices and unrelated dashboard views.

## 👨‍👩‍👧‍👦 Family configuration

Players have stable generic IDs (`player1`, `player2`, etc.), separate from their display names. The **Family** tab supports:

| Action | Result |
| --- | --- |
| **Save name** | Changes the displayed name without resetting points. |
| **Retire** | Removes a player from active controls while keeping history, tasks, and helpers. |
| **Prepare addition** | Shows a proposed new player configuration. |
| **Apply addition and restart HA** | Creates the dashboard and ten initially disabled tasks, checks configuration, and restarts to load new entities. |

Adding players creates backups and restores previous helper values after restart. At least one player must remain active. Retired IDs are never reused. **Reactivation from the dashboard has not yet been implemented.** See [Family Configuration](docs/FAMILY_CONFIGURATION.md) before migrating an installation with existing progress.

## 🌌 Seasons and artwork

The first season is **THE ORIGIN**, stored in `season_01`. Every season lasts 28 calendar days: from its configured start date through the following 27 days. The dashboard indicates whether a season is upcoming, active, or finished. Changing artwork or titles does not automatically start a new season.

```text
config/www/level_up_family/
├── level-up-family-cards.js
├── season_01/
│   ├── banner.png
│   ├── fondo_vertical.png
│   ├── recompensa.png
│   ├── icono_xp.png
│   ├── icono_nivel.png
│   ├── icono_mision.png
│   ├── icono_penalizacion.png
│   ├── icono_racha.png
│   ├── icono_semana.png
│   ├── icono_temporada.png
│   └── icono_bonus.png
└── season_XX/
    └── ...
```

`season_XX` illustrates the naming convention for future seasons; it is not a literal directory you need to create. `banner.png` is the season header; `fondo_vertical.png` is the child's dashboard background; `icono_*.png` supplies metric icons; and `recompensa.png` is displayed as the weekly reward image at **80 × 80 px**, preserving aspect ratio. A gift icon is shown if the reward image cannot load. Optional artwork may include `emblema.png`, `estela.png`, and `elementos_flotantes.png`.

Home Assistant exposes `config/www/level_up_family/season_01` under `/local/level_up_family/season_01`. For a new season, review `lf_themes.yaml`, UI strings, and artwork, then rebuild provisioning templates:

```sh
python tools/build_family_templates.py
```

Artwork updates and season renames do not change the active season, its start date, or counters. Season transitions are configured separately.

## 💾 Data, backups, and updates

| Data | Location |
| --- | --- |
| Mission checkmarks, counters, and edited settings | Home Assistant helpers. |
| Players, daily/weekly closes, yearly summaries, and penalties | `/config/level_up_family/data/luf.db` (SQLite). |
| Player identities and family mappings | `/config/level_up_family/family.json`. |
| Initial task definitions | `/config/level_up_family/task_defaults.json`. |

Include all of these in backups. Do not delete game data when updating code or artwork. Older installations with different entity IDs or database names require coordinated migration; see the [repository naming guide](docs/REPOSITORY_NAMESPACE.md).

This repository distributes generic example configuration. **Never publish real databases, backups, credentials, private names, or screenshots containing personal information.** Files under `www` are accessible from the Home Assistant frontend and should contain only public game assets.

## 🛠️ Development and contributions

```text
config/
├── custom_components/level_up_family/  Local integration and family management
├── level_up_family/                    Python engine and initial data
├── packages/level_up_family/           Rules, helpers, and automations
├── panel/level_up_family/              Child and parent dashboards
└── www/level_up_family/                Cards and seasonal artwork
docs/                                   Guides and design decisions
examples/                               Example configuration
tests/                                  Isolated tests
tools/                                  Generators and validators
```

With **Python 3.12 or later** and Node.js available:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/validate_config.py config
python tools/validate_panels_js.py config/panel/level_up_family
node --check config/www/level_up_family/level-up-family-cards.js
```

Tests use temporary data and do not need a live HA connection; they cover the engine, rules, history, and recovery behavior. Static checks **do not replace** Home Assistant configuration validation or visual testing. If you change dashboard or provisioning sources, rebuild `templates.json` before testing. Check artwork filenames and paths as well.

Contributions are reviewed through pull requests. Describe the change, tests performed, included seasonal assets, and any migration or deployment steps. Keep content updates separate from operations that modify stored progress.

## 📚 Guides and FAQ

### Planned improvements

- **Language customization and translations:** move user-facing strings into a separate translation catalog so the interface can be localized without editing the game logic.
- **Optional allowance bonus:** support families who give children a weekly allowance, with an optional monetary bonus linked to the game's weekly results. This is a planned feature, not part of the current release.

See the [roadmap](docs/ROADMAP.md) for additional plans and implementation status.

| I want to… | Document |
| --- | --- |
| Install the game | [Installation](docs/INSTALLATION.md) |
| Adapt it for my family | [Family Configuration](docs/FAMILY_CONFIGURATION.md) |
| Edit tasks and rewards | [Tasks & Rewards](docs/TASKS_AND_REWARDS.md) |
| Understand stored data | [Architecture](docs/ARCHITECTURE.md) |
| Migrate older identifiers | [Repository Namespace](docs/REPOSITORY_NAMESPACE.md) |
| Review delivered features | [Changes](docs/CHANGES.md) |
| See planned improvements | [Roadmap](docs/ROADMAP.md) |

**Does it work with one child?** Yes. Start with one and add more later.

**Must I edit configuration files to change tasks or rewards?** After installation, normal changes can be made through the parents' dashboard, subject to progress-protection rules.

**Is a reward delivered automatically?** No. The game displays the reward and goal status; parents handle delivery.

**Can I create unlimited tasks in the dashboard?** Not yet. Existing slots can be edited, and each newly added player receives ten. Adding more slots for an existing player is planned.

**Will uploading artwork start the next season?** No. Artwork and the active season are managed separately.

**What if adding a player fails?** Keep the backup and inspect the error in Family. If recovery cannot finish, the game remains in maintenance mode. Follow the recovery guide before resuming.

---

<a id="español"></a>

🌐 **Language / Idioma:** [English](#english) · [Español](#español)

# 🎮 Level Up Family

**Las rutinas de casa se convierten en misiones. El progreso, en una aventura compartida.**

Level Up Family es un juego de tareas domésticas para **Home Assistant**. Cada hijo tiene su propio panel, completa misiones, gana experiencia (XP) y sigue su evolución durante temporadas de **28 días**. Los padres gestionan las tareas, supervisan el progreso y eligen las recompensas semanales. Funciona con uno o varios hijos y permite personalizar nombres, misiones y premios.

![Temporada 1 de Level Up Family](config/www/level_up_family/season_01/banner.png)

## ✨ Funcionalidades

### Panel de cada jugador

- Cabecera, fondo y gráficos de la temporada activa.
- Misiones del día, XP asignados y casillas de finalización.
- XP acumulados durante la semana, nivel, racha diaria y racha semanal.
- Objetivo semanal, bonificaciones, multas y recompensa elegida por los padres.

Las correcciones de días anteriores se realizan desde el panel de padres.

### Panel de padres

| Pestaña | Funciones |
| --- | --- |
| **Control** | Seguimiento, corrección de misiones de la semana activa, aplicación y anulación de multas por identificador. |
| **Histórico** | Semanas cerradas y resúmenes anuales guardados en SQLite. |
| **Tareas y premios** | Edición de nombre, dificultad, XP, jugador, días, frecuencia y premio semanal. |
| **Familia** | Cambio de nombres, preparación de altas y retirada de hijos sin borrar su histórico. |

La gestión de la familia comprueba en el servidor que el usuario sea administrador. El resto de scripts y helpers depende de los permisos de Home Assistant; no existe un sistema independiente de permisos por hijo.

## 🗓️ Cómo funciona una semana

1. Los padres configuran las tareas con nombre, jugador, XP y días. Algunas tareas se realizan una sola vez dentro de varios días seleccionados.
2. Los hijos completan sus misiones y ven el progreso en tiempo real.
3. El objetivo semanal predeterminado es completar el **75 %** de las misiones previstas, pero puede ajustarse. La recompensa es una descripción del premio que deciden los padres.
4. Los cierres diarios y semanales calculan resultados, consolidan XP, actualizan rachas y guardan el histórico.

Los días perfectos y las semanas consecutivas que alcanzan el objetivo pueden generar bonificaciones. Las multas descuentan XP de la semana, **no** del total histórico consolidado; al anular una multa se conserva su registro marcado como cancelado. Los XP semanales y los históricos tienen funciones distintas: el total se consolida al cierre semanal.

### Edición segura de tareas

- Se puede cambiar el nombre de una tarea que ya tiene progreso.
- Los XP, días, frecuencia o jugador solo pueden modificarse si esa tarea aún no registra progreso en la semana activa.
- Una tarea sin días seleccionados queda desactivada.
- Se rechazan formularios desactualizados si otra sesión ya guardó cambios.
- Las tareas de una vez por semana cuentan una sola vez y no participan en el bonus de día perfecto.

Más detalles: [Tareas y premios](docs/TASKS_AND_REWARDS.md).

## 🚀 Instalación

La instalación combina **paquetes YAML, scripts Python, una integración local y tarjetas de interfaz**; requiere copiar archivos y combinar la configuración existente de Home Assistant.

### Requisitos

- Home Assistant con acceso a `/config` y soporte para paquetes YAML.
- Python 3 y SQLite en el entorno donde se ejecuta Home Assistant.
- [button-card](https://github.com/custom-cards/button-card) y [card-mod](https://github.com/thomasloven/lovelace-card-mod), instalados y registrados.
- Integración local incluida en `config/custom_components/level_up_family`.
- Recurso `/local/level_up_family/level-up-family-cards.js?v=2.6.0`, registrado como **módulo JavaScript**.
- Copia de seguridad completa antes de modificar una instalación existente.

**No es una instalación mediante HACS.** HACS puede utilizarse para las tarjetas externas, pero la integración local se instala manualmente.

### Primeros pasos

1. Utiliza la configuración de ejemplo para dos jugadores o el [generador familiar](docs/FAMILY_CONFIGURATION.md) para uno o varios hijos.
2. Copia `config/` a `/config/` conservando las rutas y combina las inclusiones de `examples/configuration.yaml` o del fragmento generado con tu archivo actual.
3. **Solo en instalaciones nuevas**, inicializa la base de datos:

   ```sh
   python3 /config/level_up_family/python/luf_db.py init
   ```

4. Registra las tarjetas, comprueba la configuración de HA y reinicia si es válida.
5. Configura `input_number.luf_season_number` e `input_datetime.luf_season_start`.
6. Ajusta tareas y premios desde el panel de padres. Comprueba que `input_boolean.luf_maintenance` esté apagado cuando el juego esté listo.

Consulta la [guía completa de instalación](docs/INSTALLATION.md). Combina los archivos con cuidado para conservar tus dispositivos y otras vistas de los paneles.

## 👨‍👩‍👧‍👦 Configurar la familia

Se usan identificadores estables y genéricos (`player1`, `player2`, etc.), separados del nombre visible. El panel **Familia** permite:

| Acción | Resultado |
| --- | --- |
| **Guardar nombre** | Cambia el nombre visible sin reiniciar puntos. |
| **Retirar** | Excluye al jugador de los controles activos, conservando historial, tareas y helpers. |
| **Preparar alta** | Presenta una propuesta para añadir otro jugador. |
| **Aplicar alta y reiniciar HA** | Crea el panel y diez tareas desactivadas; comprueba la configuración y reinicia para cargar las entidades. |

Las altas preparan copias y recuperan los valores anteriores de los helpers después del reinicio. Debe quedar al menos un jugador activo. Los identificadores retirados no se reutilizan. **La reactivación desde el panel todavía está pendiente.** Consulta [Configuración familiar](docs/FAMILY_CONFIGURATION.md) antes de migrar una instalación con actividad.

## 🌌 Temporadas y recursos gráficos

La primera temporada se llama **THE ORIGIN** y utiliza `season_01`. Cada temporada dura 28 días naturales: desde la fecha de inicio hasta 27 días después. El panel muestra si está pendiente, activa o finalizada. Cambiar archivos o títulos no inicia automáticamente una temporada nueva.

```text
config/www/level_up_family/
├── level-up-family-cards.js
├── season_01/
│   ├── banner.png
│   ├── fondo_vertical.png
│   ├── recompensa.png
│   ├── icono_xp.png
│   ├── icono_nivel.png
│   ├── icono_mision.png
│   ├── icono_penalizacion.png
│   ├── icono_racha.png
│   ├── icono_semana.png
│   ├── icono_temporada.png
│   └── icono_bonus.png
└── season_XX/
    └── ...
```

`season_XX` representa el patrón de carpetas futuras, no una carpeta que debas crear literalmente. `banner.png` se usa como cabecera; `fondo_vertical.png`, como fondo infantil; `icono_*.png`, como iconos de métricas; y `recompensa.png`, como imagen de premio de **80 × 80 px**, respetando proporciones. Si falta la imagen del premio, se muestra un icono alternativo. Pueden añadirse otros recursos complementarios como `emblema.png`, `estela.png` y `elementos_flotantes.png`.

En HA, `config/www/level_up_family/season_01` se sirve bajo `/local/level_up_family/season_01`. Para una temporada nueva, revisa `lf_themes.yaml`, textos y recursos; después regenera las plantillas:

```sh
python tools/build_family_templates.py
```

Las imágenes y los cambios de nombre no modifican la temporada activa, su fecha de inicio ni los contadores. La transición de temporada se configura por separado.

## 💾 Datos, copias y actualizaciones

| Datos | Ubicación |
| --- | --- |
| Misiones marcadas, contadores y ajustes | Helpers de Home Assistant. |
| Jugadores, cierres, resúmenes anuales y multas | `/config/level_up_family/data/luf.db` (SQLite). |
| Identidades y vínculos familiares | `/config/level_up_family/family.json`. |
| Definiciones iniciales de tareas | `/config/level_up_family/task_defaults.json`. |

Incluye todos estos elementos en tus copias de seguridad. No borres datos al actualizar código o imágenes. Las versiones anteriores con otra base de datos o identificadores necesitan una migración coordinada: consulta la [nomenclatura](docs/REPOSITORY_NAMESPACE.md).

Este repositorio ofrece datos genéricos. **No publiques bases de datos reales, copias de seguridad, credenciales, nombres privados ni capturas con información personal.** Los archivos en `www` son accesibles desde el frontend de HA y deben contener únicamente recursos públicos del juego.

## 🛠️ Desarrollo y contribuciones

```text
config/
├── custom_components/level_up_family/  Integración y gestión familiar
├── level_up_family/                    Motor Python y datos iniciales
├── packages/level_up_family/           Reglas, helpers y automatizaciones
├── panel/level_up_family/              Vistas de niños y padres
└── www/level_up_family/                Tarjetas y gráficos
docs/                                   Guías y decisiones
examples/                               Configuración de ejemplo
tests/                                  Pruebas aisladas
tools/                                  Generadores y validadores
```

Con **Python 3.12 o posterior** y Node.js disponibles:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/validate_config.py config
python tools/validate_panels_js.py config/panel/level_up_family
node --check config/www/level_up_family/level-up-family-cards.js
```

Las pruebas usan datos temporales sin conectarse a HA; revisan motor, reglas, histórico y recuperación. Las validaciones estáticas **no sustituyen** la comprobación de configuración ni la revisión visual dentro de Home Assistant. Si cambias fuentes de paneles o aprovisionamiento, regenera `templates.json` antes de probar. Comprueba también nombres y rutas de gráficos.

Se aceptan propuestas mediante pull requests. Explica qué cambia, cómo se probó, qué recursos de temporada incluye y si requiere migración o despliegue. Mantén independientes los cambios de contenido y las operaciones que alteren el progreso.

## 📚 Guías y preguntas frecuentes

### Próximas mejoras

- **Personalización de idioma y traducciones:** trasladar los textos visibles a un catálogo independiente para poder traducir la interfaz sin modificar la lógica del juego.
- **Bonus económico opcional:** permitir que las familias que dan paga semanal a sus hijos puedan configurar un incentivo monetario adicional ligado a los resultados semanales. Es una funcionalidad prevista, todavía no incluida.

Consulta la [hoja de ruta](docs/ROADMAP.md) para conocer otras mejoras y su estado.

| Necesitas… | Documento |
| --- | --- |
| Instalar el juego | [Instalación](docs/INSTALLATION.md) |
| Adaptarlo a tus hijos | [Configuración familiar](docs/FAMILY_CONFIGURATION.md) |
| Editar tareas y premios | [Tareas y premios](docs/TASKS_AND_REWARDS.md) |
| Comprender el almacenamiento | [Arquitectura](docs/ARCHITECTURE.md) |
| Migrar identificadores anteriores | [Nomenclatura](docs/REPOSITORY_NAMESPACE.md) |
| Revisar funcionalidades entregadas | [Cambios](docs/CHANGES.md) |
| Ver próximas mejoras | [Hoja de ruta](docs/ROADMAP.md) |

**¿Sirve para un solo hijo?** Sí; puedes empezar con uno y añadir otros más tarde.

**¿Debo editar archivos para cambiar tareas o recompensas?** Después de instalar, puedes editarlas desde el panel de padres, con las restricciones que protegen el progreso.

**¿El premio se entrega automáticamente?** No; el juego registra el objetivo y muestra el premio, pero los padres gestionan la entrega.

**¿Puedo crear tareas ilimitadas desde el panel?** Aún no. Puedes editar los espacios actuales y cada nuevo jugador recibe diez; añadir más espacios para un jugador existente está pendiente.

**¿Subir nuevas imágenes activa otra temporada?** No; los recursos y el inicio de temporada son independientes.

**¿Qué pasa si falla un alta?** Conserva la copia de seguridad y consulta el error en Familia. Si la recuperación falla, el juego permanece en mantenimiento. Sigue la guía de recuperación antes de reanudarlo.
