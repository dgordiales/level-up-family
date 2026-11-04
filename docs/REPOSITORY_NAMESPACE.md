🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# Level Up Family namespace

This revision consolidates the current repository under the Level Up Family name and the technical prefix `luf`. It covers source code, files, tests, documentation, generated templates, entity IDs, actions, and paths. Player identifiers remain `player1`, `player2`, and so on.

| Component | Current name |
| --- | --- |
| SQLite engine | `config/level_up_family/python/luf_db.py` |
| History reader | `config/level_up_family/python/luf_history.py` |
| Penalty reader | `config/level_up_family/python/luf_active_penalties.py` |
| Runtime database | `/config/level_up_family/data/luf.db` |
| Game helpers and actions | `luf_*` |
| Task catalog | `sensor.luf_task_catalog` |
| Family registry | `sensor.luf_family` |
| Child dashboard view | `playerN-luf` |
| Parents' control and history | `control-luf`, `historico-luf` |

The integration domain, folder, and frontend cards remain `level_up_family` and `level-up-family-*`. The integration version changes to 0.5.0 to flag the identifier changes. The card resource uses `?v=2.6.0` to refresh the cache; reload the browser as well. User-facing titles use Level Up Family.

## Scope and updating

**This change only affects the repository. It does not modify, deploy, or restart the Home Assistant installation currently in use.** Previous real-world HA checks refer to the earlier functional release; this naming revision was verified using repository tests and validators.

For a new installation, use all the files from this revision together. For an older installation, replacing only the three Python scripts is not enough: packages, scripts, entities, routes, the database, and references also change. This revision does not include an automatic migration for those names.

Before migrating an installation with existing activity:

1. Back up the entire HA installation, SQLite, the family registry, customized tasks, and helper values. Stop the game's writers.
2. Make an explicit mapping of current entity IDs, unique IDs, actions, and paths to their counterparts in this revision. Preserve player identities and progress; do not create new players for the same children.
3. Coordinate the `luf.db` location, Python commands, and `family.json` mappings. Do not replace an active database by initializing a blank one.
4. Validate configuration in a copy and compare activity, counters, and dashboards before deployment. Retain a complete backup for rollback.

Commit history preserves earlier versions of the project. This cleanup changes the current files without rewriting that history.

---

<a id="español"></a>

# Nomenclatura de Level Up Family

Esta revisión unifica el contenido actual del repositorio bajo Level Up Family y el prefijo técnico `luf`. Incluye código, archivos, pruebas, documentación, plantillas generadas, nombres de entidades, acciones y rutas. Los identificadores personales siguen siendo `player1`, `player2`, etc.

| Componente | Nombre actual |
| --- | --- |
| Motor SQLite | `config/level_up_family/python/luf_db.py` |
| Lectura del histórico | `config/level_up_family/python/luf_history.py` |
| Lectura de multas | `config/level_up_family/python/luf_active_penalties.py` |
| Base de datos de ejecución | `/config/level_up_family/data/luf.db` |
| Helpers y acciones del juego | `luf_*` |
| Catálogo de misiones | `sensor.luf_task_catalog` |
| Registro familiar | `sensor.luf_family` |
| Vista de cada hijo | `playerN-luf` |
| Control e histórico de padres | `control-luf`, `historico-luf` |

El nombre del dominio de integración, la carpeta y las tarjetas siguen siendo `level_up_family` y `level-up-family-*`. La integración pasa a versión 0.5.0 para señalar el cambio de identificadores. El recurso de tarjetas usa `?v=2.6.0` para renovar la caché al instalar esta revisión; recarga también el navegador. Los títulos visibles usan Level Up Family.

## Alcance y actualización

**El cambio afecta únicamente al repositorio. No modifica, despliega ni reinicia la instalación de Home Assistant en uso.** Las comprobaciones reales en HA descritas en documentos anteriores corresponden a la revisión funcional previa; esta nomenclatura se verifica con las pruebas y validadores del repositorio.

Para una instalación nueva utiliza todos los archivos de esta revisión conjuntamente. Para una instalación anterior no basta con sustituir los tres archivos Python: los paquetes, scripts, entidades, rutas, base de datos y referencias también cambian. Esta revisión no incorpora una migración automática de esos nombres.

Antes de migrar una instalación con actividad:

1. Guarda una copia completa de HA, de SQLite, del registro familiar, de las tareas personalizadas y de los valores de helpers. Detén los escritores del juego.
2. Prepara un mapa explícito entre entidades, identificadores únicos, acciones y rutas existentes y sus equivalentes de esta revisión. Conserva las identidades de jugadores y los valores de progreso; no crees jugadores nuevos para los mismos hijos.
3. Coordina la ubicación de la base de datos `luf.db`, los comandos Python y las vinculaciones de `family.json`. No inicialices una base vacía para sustituir la que contiene actividad.
4. Valida la configuración en una copia y compara actividad, contadores y paneles antes de desplegar. Conserva la copia conjunta para volver atrás.

El historial de commits conserva las versiones anteriores del proyecto; esta limpieza se realiza sobre los archivos vigentes, sin reescribir ese historial.
