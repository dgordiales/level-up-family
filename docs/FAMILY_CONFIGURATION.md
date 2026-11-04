🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# Configure one, two, or more children

The repository's two players are an example. The generator prepares your family's configuration from **a private file** containing names and active or retired players. It generates dashboards, helpers, initial task slots, rewards, penalties, and closing routines. You do not need to manually duplicate every player reference.

Once this version is installed, **Family** in the parents' dashboard allows you to rename, retire, and add children without editing files. The generator below is intended for preparing a new installation.

## Manage players from the parents' dashboard

- **Save name** updates the displayed name, including in history. It preserves IDs, completed missions, XP, and prior closes. HA does not need to restart.
- **Retire** first asks for confirmation. The child disappears from active controls and their dashboard indicates they are retired. Helpers, task checkmarks, rewards, and all SQLite rows remain. Family shows a progress summary at retirement, and History retains weeks and years. At least one child must remain active.
- **Prepare addition** validates the name and shows a proposal. **Apply addition and restart HA** creates a new identity, dashboard, and ten initially disabled tasks. It checks configuration, saves a backup, and restarts HA to load new entities. On startup it restores prior helper values before leaving maintenance mode. Parents then assign days and XP under Tasks & Rewards.

New children appear in the **Level Up Family · Children** dashboard. Existing dashboards retain their routes and other tabs. Retired IDs are never reused. This release does not include a reactivation action after weeks of absence; do not manually change `active` in a running installation.

The `level_up_family.manage_family` action checks administrator privileges on the server. Forms reject stale revisions when two sessions edit family settings simultaneously. Each operation creates a backup under `/config/level_up_family/backups/family_*`; retiring a player never deletes their data.

The frontend module is `/local/level_up_family/level-up-family-cards.js?v=2.6.0`. You must also install `config/custom_components/level_up_family`, `lf_family.yaml`, the version 2 family registry, and the shared children's dashboard. HA loads the integration on restart. Updating only the JavaScript card is insufficient.

## Update an older installation

Take a complete backup before replacing files. Do not overwrite `data/`, HA helper values, or `task_defaults.json` with repository examples. Do not overwrite an existing family registry with the example either.

An older installation must map `id`, `entity_prefix`, `db_key`, `dashboard_url`, and `dashboard_path` exactly once in its version 2 registry. For example, public ID `player1` can refer to `luf_legacy_one_*` entities and SQLite key `player_1`. Renaming the display name does not change these mappings. Set `parents_dashboard` in `lf_family.yaml` if it differs from the example. Keep the shared dashboard at `level-up-family-children`; additions generate this route. All linked dashboards, including those for retired players, must remain registered so family management can load their views.

Game views are rebuilt from distributed templates when the family changes. Back up customizations within those views before migration; unrelated tabs and general dashboard settings are preserved.

The generator's input uses `version: 1` with `id`, `name`, and `active`. Its runtime output uses `version: 2`, adding `revision` and the mappings above. After installation, HA's registry becomes authoritative: do not overwrite it with an outdated private initial file. Do not publish runtime registries containing real names or backups.

Dashboard operations update only game tabs. Backups contain the original dashboards for recovery. If an addition remains pending or HA cannot restore all helper values, the game stays in maintenance and Family reports the problem. Keep `family_pending.json` and its backup to resolve it. Do not run a reset to repair an installation.

## Player ID and display name

| Field | Example | Meaning |
| --- | --- | --- |
| `id` | `player3` | Stable identity for entities, tasks, and SQLite. Never change or reuse it. |
| `name` | `Luna` | Name shown on dashboards, controls, and history. It can be changed. |
| `active` | `true` | If `false`, the player is retired while retaining history and helpers. |

Names support accented letters, spaces, and quotation marks, up to 40 characters. IDs follow `player1`, `player2`, `player3`… without leading zeroes; they need not be consecutive. Reordering the file changes presentation, not identity.

## Prepare the files

With Python 3.12 or later and dependencies from `requirements-dev.txt`, copy `examples/family.yaml` to `family.local.yaml`. That filename and `build/` are ignored by Git to prevent publishing real names.

Example with three children:

```yaml
version: 1
players:
  - id: player1
    name: Luna
    active: true
  - id: player2
    name: Leo
    active: true
  - id: player3
    name: Mía
    active: true
```

For a new one-child installation, keep only `player1`. Generate and validate a new directory:

```sh
python tools/configure_family.py --family family.local.yaml --output build/family-v1
python tools/validate_config.py build/family-v1/config
python tools/validate_panels_js.py build/family-v1/config/panel/level_up_family
```

The output includes `config/`, a `generation.json` summary, and `configuration.fragment.yaml`, which must be merged with the existing HA configuration. Inside `config/level_up_family/`, `family.json` contains the generated runtime registry. Retain the input file as an initial reference; later dashboard changes are stored in HA's registry.

The output directory must be new. The generator does not install into HA, read databases, or overwrite a previous output directory. Never use HA's `/config` as the generator output.

## New installation

Follow [Installation](INSTALLATION.md) with the generated `config/` directory and configuration fragment. Merge includes; do not replace other device configuration. Keep the JavaScript resources described in the guide, including the custom card module and card-mod.

In the environment where the game runs:

```sh
python3 /config/level_up_family/python/luf_db.py init
python3 /config/level_up_family/python/luf_db.py players
```

`init` reads `/config/level_up_family/family.json`. Each active child gets a dashboard, reward, and ten initial task slots. `player1` retains the sleeping-alone task template; other players start with the personal-hygiene template. Tasks can be edited or disabled in **Tasks & Rewards**.

Set the season start date and check the configuration against your HA version before starting. Repository validators check files and templates, but HA configuration validation and visual inspection are still required.

## Offline workflow for stopped installations

For normal use, prefer the **Family** tab. The following process remains a migration tool for a stopped and reviewed installation; regenerating the example may overwrite customizations if copied without comparison.

1. Back up HA completely and retain the private family file.
2. Edit `name` while preserving `id`, or add an entry with a new ID. Never reuse a retired child's ID.
3. Generate and validate a new directory, such as `build/family-v2`.
4. With HA and game writers stopped, update game files. Replace only `packages/level_up_family/` and `panel/level_up_family/` with generated versions to avoid leftover old files. Update the code and JSON files under `level_up_family/` while **always preserving `data/`**, backups, and HA helper values. The generated output contains no databases.
5. Merge panel registrations from `configuration.fragment.yaml` into the existing configuration.
6. With writers stopped, synchronize the family to the existing database:

   ```sh
   python3 /config/level_up_family/python/luf_db.py sync_family
   python3 /config/level_up_family/python/luf_db.py players
   ```

7. Validate configuration, start HA, and review names, missions, rewards, and history. A new player starts without activity; existing players retain their entities and counters.

The generator preserves physical IDs and task slots when a child is renamed or reordered. Changes to tasks and rewards made in the parents' dashboard remain in persistent helpers and are not overwritten by JSON defaults.

## Offline retirement and reactivation

First close the player's current week and resolve outstanding penalties. Changing the family does not automatically settle weeks or award XP.

Keep the child in the file and change only their status:

```yaml
- id: player2
  name: Leo
  active: false
```

Follow the same generation, update, and `sync_family` process. The player disappears from selectors, new penalties, corrections, and automatic closes. Their tasks leave the active catalog. Helpers and metadata remain without being reset, and their scripts stop running.

The generator excludes a retired player's dashboard from the new navigation fragment; the view displays a notice and no mission buttons. If the Family integration is also used, keep its dashboard registration in HA because it remains linked to that player. On new installations, start with active players and retire them through Family after setup.

SQLite preserves days, weeks, years, and penalties. History continues to show the player's weeks and summaries in a retired section. Do not delete their row or helpers: SQLite relationships use cascading deletion, so physically removing a player could erase activity.

If an ID is omitted from the file, `sync_family` also deactivates it in SQLite. Keeping the entry with `active: false` is preferable to preserve helpers and display names across dashboards.

Changing back to `active: true` restores the same SQLite identity. If several weeks have passed, you must reconcile the active week, masks, and streaks before reactivating the game: this generator does not automate that progress migration. Never change a week date while masks still refer to another week. At least one player must remain active.

## Compatibility and recovery

Without `family.json`, the engine retains compatible initial behavior for `player1` and `player2`. Invalid family files produce errors rather than silently falling back to other names.

This procedure applies to the **generic repository distribution**. Installations with custom keys such as `player_1` or entities containing old names require a specific migration; copying these files directly would create different entities. The generator does not change the original installation from which the project evolved.

To roll back, restore configuration, SQLite, and helper state **together** from the previous backup. Restoring YAML files alone does not undo synchronized names or retirements in the database.

For manual recovery, first stop game writers and retain the entire backup directory. `helpers.json` stores prior values, `family.json` the former registry, and `luf.db` the SQLite copy; modified views are saved as `dashboard_*.json`. During additions, `files.json` preserves prior provisioned file contents and identifies files that did not exist before. Restore a consistent set or a full HA backup, validate configuration, and review counters and dashboards before resuming. Do not delete `family_pending.json` or turn off maintenance just to hide failed recovery: resolve the cause or restore the backup first.

---

<a id="español"></a>

# Configurar uno, dos o más hijos

Los dos jugadores del repositorio son un ejemplo. El generador prepara la configuración de tu familia desde **un archivo privado**: nombres, jugadores activos y jugadores retirados. Genera paneles, helpers, espacios iniciales de tareas, recompensas, multas y cierres. No hace falta duplicar manualmente todas las referencias de un jugador.

Una vez instalada esta versión, **Familia**, en el panel de padres, permite cambiar nombres, retirar hijos y dar de alta otros sin editar archivos. El generador que se explica después sirve para preparar una instalación nueva.

## Gestionar desde el panel de padres

- **Guardar nombre** actualiza el nombre visible y el mostrado en el histórico. Conserva los identificadores, las misiones completadas, los XP y los cierres anteriores. No necesita reiniciar HA.
- **Retirar** muestra primero una confirmación. El hijo desaparece de los controles activos y su panel muestra que está retirado. Se conservan sus helpers, las marcas de tareas, los premios y todas las filas de SQLite. Familia muestra un resumen de su progreso al retirarse; Histórico conserva sus semanas y años. Debe quedar al menos un hijo activo.
- **Preparar alta** valida el nombre y muestra una propuesta. **Aplicar alta y reiniciar HA** crea una identidad nueva, su panel y diez tareas inicialmente desactivadas. Comprueba la configuración, guarda una copia de seguridad y reinicia HA para cargar las nuevas entidades. Al arrancar restaura los valores anteriores de los helpers antes de quitar el mantenimiento. Después asigna los días y XP desde Tareas y recompensas.

Las altas nuevas aparecen en el panel **Level Up Family · Hijos**. Los paneles anteriores conservan sus rutas y sus otras pestañas. Los identificadores retirados nunca se reutilizan. Esta versión no incluye una acción de reactivación tras semanas de ausencia; no cambies `active` manualmente en una instalación en uso.

La acción `level_up_family.manage_family` comprueba en el servidor que quien la invoca es administrador. Los formularios rechazan revisiones antiguas si dos sesiones cambian la familia a la vez. Cada operación crea una copia en `/config/level_up_family/backups/family_*`; retirar nunca ejecuta un borrado de datos.

El módulo de interfaz es `/local/level_up_family/level-up-family-cards.js?v=2.6.0`. Es necesario instalar también `config/custom_components/level_up_family`, `lf_family.yaml`, el registro familiar de versión 2 y el panel compartido de hijos. La integración se carga al reiniciar HA. No basta con cambiar la tarjeta JavaScript.

## Actualizar una instalación anterior

Antes de sustituir archivos, realiza una copia completa. No reemplaces `data/`, los valores de los helpers ni `task_defaults.json` con el ejemplo del repositorio. Tampoco sustituyas el registro familiar existente por el ejemplo.

Una instalación antigua necesita vincular una sola vez `id`, `entity_prefix`, `db_key`, `dashboard_url` y `dashboard_path` en su registro de versión 2. Por ejemplo, el identificador público `player1` puede apuntar a entidades `luf_legacy_one_*` y a la clave SQLite `player_1`. Cambiar el nombre visible no cambia esas vinculaciones. Configura `parents_dashboard` en `lf_family.yaml` si difiere del ejemplo. Mantén el panel compartido en `level-up-family-children`: las altas generan esa ruta. Todos los paneles vinculados, incluidos los de jugadores retirados, deben seguir registrados para que la gestión pueda cargar sus vistas.

Las vistas del juego se reconstruyen desde las plantillas distribuidas al cambiar la familia. Conserva una copia de cualquier personalización dentro de esas vistas antes de migrar; las pestañas ajenas al juego y los ajustes generales del panel se mantienen.

El archivo de entrada del generador utiliza `version: 1` y campos `id`, `name` y `active`. Su salida de ejecución utiliza `version: 2`, añade `revision` y las vinculaciones anteriores. Después de instalar, el registro de HA es el vigente: no vuelvas a copiar sobre él un archivo privado inicial que ya esté desactualizado. No publiques registros de ejecución con nombres reales ni las copias de seguridad.

Las operaciones desde el panel actualizan solo las pestañas del juego. Las copias contienen los paneles originales para recuperación. Si un alta queda pendiente o HA no puede recuperar todos los helpers, el juego permanece en mantenimiento y Familia informa del problema; conserva `family_pending.json` y su copia de seguridad para resolverlo. No ejecutes un reset para corregir una instalación.

## Identificador y nombre

| Campo | Ejemplo | Significado |
| --- | --- | --- |
| `id` | `player3` | Identidad estable en entidades, tareas y SQLite. No se cambia ni reutiliza. |
| `name` | `Luna` | Nombre visible en paneles, controles e histórico. Puede cambiarse. |
| `active` | `true` | Con `false` el jugador queda retirado, conservando su histórico y helpers. |

Los nombres admiten tildes, espacios y comillas, hasta 40 caracteres. Los identificadores son `player1`, `player2`, `player3`… sin ceros iniciales; no necesitan ser consecutivos. Cambiar el orden del archivo cambia la presentación, no la identidad.

## Preparar los archivos

Con Python 3.12 o posterior y las dependencias de `requirements-dev.txt`, copia `examples/family.yaml` a `family.local.yaml`. Este nombre y `build/` están excluidos de Git para no publicar nombres reales.

Ejemplo de tres hijos:

```yaml
version: 1
players:
  - id: player1
    name: Luna
    active: true
  - id: player2
    name: Leo
    active: true
  - id: player3
    name: Mía
    active: true
```

Para una instalación nueva con un hijo, deja únicamente `player1`. Después genera y valida una carpeta nueva:

```sh
python tools/configure_family.py --family family.local.yaml --output build/family-v1
python tools/validate_config.py build/family-v1/config
python tools/validate_panels_js.py build/family-v1/config/panel/level_up_family
```

La salida contiene `config/`, un resumen `generation.json` y `configuration.fragment.yaml`, que se combina con la configuración existente de HA. Dentro de `config/level_up_family/`, `family.json` contiene el registro de ejecución generado. Conserva el archivo de entrada como referencia inicial; las modificaciones posteriores desde el panel se guardan en el registro de HA.

La carpeta de salida debe ser nueva. El generador no instala nada en HA, no lee bases de datos ni sobrescribe una carpeta anterior. No uses `/config` de HA como salida.

## Instalación nueva

Sigue [Instalación](INSTALLATION.md) usando la carpeta `config/` y el fragmento generados. Combina las inclusiones; no reemplaces la configuración de otros dispositivos. Mantén los recursos JavaScript descritos en la guía, incluido el módulo de tarjetas y card-mod.

En el entorno donde se ejecuta el juego:

```sh
python3 /config/level_up_family/python/luf_db.py init
python3 /config/level_up_family/python/luf_db.py players
```

`init` lee `/config/level_up_family/family.json`. Cada hijo activo tendrá su panel, premio y diez espacios iniciales de tareas. `player1` conserva la plantilla de dormir solo; los demás parten de la de higiene personal. Se pueden editar o desactivar desde **Tareas y premios**.

Configura el inicio de temporada y comprueba la configuración en tu versión de HA antes del arranque. Las validaciones del repositorio comprueban archivos y plantillas; la comprobación de configuración y la revisión visual en HA siguen siendo necesarias.

## Flujo offline para instalaciones detenidas

Para el uso habitual utiliza la pestaña **Familia**. El flujo siguiente queda como herramienta de migración para una instalación detenida y revisada; generar de nuevo el ejemplo puede sobrescribir personalizaciones si se copia sin compararlas.

1. Guarda una copia completa de HA y del archivo familiar privado.
2. Cambia `name`, manteniendo `id`, o añade una entrada con un identificador nuevo. Nunca reutilices el de otro hijo retirado.
3. Genera y valida otra carpeta, por ejemplo `build/family-v2`.
4. Con HA y los escritores del juego detenidos, actualiza los archivos del juego. Sustituye únicamente las carpetas `packages/level_up_family/` y `panel/level_up_family/` por sus versiones generadas para evitar archivos antiguos sobrantes. Actualiza el código y los JSON de `level_up_family/`, **conservando siempre `data/`**, las copias de seguridad y los valores de helpers de HA. La salida generada no contiene bases de datos.
5. Combina los registros de paneles de `configuration.fragment.yaml` con los existentes.
6. Sin escritores en ejecución, sincroniza la familia con la base existente:

   ```sh
   python3 /config/level_up_family/python/luf_db.py sync_family
   python3 /config/level_up_family/python/luf_db.py players
   ```

7. Comprueba la configuración, inicia HA y revisa nombres, misiones, premios e histórico. Un jugador nuevo empieza sin actividad; los demás mantienen entidades y contadores.

El generador conserva los identificadores físicos y espacios de tareas aunque cambien el nombre o el orden de un hijo. Los cambios de tareas y premios realizados desde padres continúan en los helpers persistentes; no se sustituyen por los valores iniciales del JSON.

## Retirada y reactivación offline

Termina primero el cierre de su semana y resuelve las multas pendientes. Cambiar la familia no liquida semanas ni reparte XP automáticamente.

Mantén al hijo en el archivo y cambia solo su estado:

```yaml
- id: player2
  name: Leo
  active: false
```

Aplica el mismo procedimiento de generación, actualización y `sync_family`. El jugador desaparece de selectores, multas nuevas, correcciones y cierres automáticos. Sus tareas dejan de participar en el catálogo activo. Se mantienen sus helpers y metadatos sin reiniciarlos y sus scripts quedan detenidos.

El generador no añade el panel retirado al nuevo fragmento de navegación; su archivo muestra un aviso y no ofrece botones de misiones. Si utilizas también la integración de Familia, conserva su registro de panel en HA, porque sigue vinculado al jugador. Para instalaciones nuevas, empieza con jugadores activos y realiza las retiradas desde Familia después de instalar.

SQLite conserva días, semanas, años y multas. El histórico sigue mostrando sus semanas y resúmenes, con una sección marcada como retirado. No borres su fila ni helpers: las relaciones de SQLite tienen borrado en cascada y una eliminación física podría borrar actividad.

Si se omite un identificador del archivo, `sync_family` también lo desactiva en SQLite, pero conviene mantenerlo con `active: false` para conservar sus helpers y nombre en todos los paneles.

Volver a `active: true` permite recuperar la misma identidad en SQLite. Si han pasado semanas desde la retirada, antes de reactivar el juego también hay que reconciliar su semana activa, máscaras y rachas: este generador no automatiza esa migración de progreso. No cambies una fecha de semana sobre máscaras que aún pertenecen a otra. Se requiere al menos un jugador activo.

## Compatibilidad y recuperación

Sin `family.json`, el motor conserva la inicialización compatible con `player1` y `player2`. Un archivo familiar inválido produce un error; no se reemplaza silenciosamente por otros nombres.

Este procedimiento corresponde a instalaciones de **la distribución genérica del repositorio**. Una instalación con claves propias, como `player_1`, o entidades que contienen nombres anteriores necesita una migración específica: copiar estos archivos directamente crearía entidades diferentes. El generador no cambia la instalación original que dio lugar al proyecto.

Para volver atrás, restaura conjuntamente configuración, SQLite y estado de helpers desde la copia anterior. Restaurar solo los YAML no revierte una sincronización de nombres o retiradas en la base.

Para una recuperación manual, detén primero los escritores del juego y conserva la carpeta de copia completa. `helpers.json` contiene los valores anteriores, `family.json` el registro anterior y `luf.db` la copia SQLite; las vistas que se modifican se guardan como `dashboard_*.json`. En un alta, `files.json` conserva el contenido anterior de los archivos aprovisionados y señala los que antes no existían. Restaura el conjunto compatible o una copia completa de HA, comprueba la configuración y revisa contadores y paneles antes de reanudar. No borres `family_pending.json` ni apagues mantenimiento para ocultar una recuperación fallida: primero resuelve la causa o restaura la copia.
