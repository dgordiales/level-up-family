# Funcionamiento

## Estado de juego

Home Assistant mantiene las misiones semanales en helpers numéricos: cada bit representa un día, del lunes (`1`) al domingo (`64`). Los sensores derivan XP, progreso, objetivos y nivel. `task_defaults.json` aporta los valores iniciales y `lf_tasks.yaml` los combina con los metadatos editables persistidos en helpers de texto para publicar `sensor.champ_task_catalog`.

Los paneles, cálculos y cierres consumen ese catálogo. Los cambios de configuración y las acciones de marcar, desmarcar o alternar se serializan en `script.champ_task_mutate`. Antes de escribir se comprueban la revisión del formulario, tipos, límites, semana activa, jugador y día. Cambiar reglas de una tarea con progreso se rechaza; su nombre sigue siendo editable.

La reasignación mantiene el helper físico de la misión. Cada cierre semanal reinicia únicamente las tareas asignadas al jugador que está cerrando, aunque sus entidades conservaran un nombre anterior. Así se evita borrar misiones del otro jugador. Los helpers antiguos de XP por dificultad se conservan por compatibilidad; los XP de cada tarea proceden ahora del catálogo.

`lf_core.yaml` contiene reglas compartidas y scripts de acceso. `lf_player1.yaml` y `lf_player2.yaml` reúnen los helpers, sensores, acciones y cierres diarios de cada jugador. `lf_weekly.yaml` inicializa la semana y programa su cierre, incluyendo recuperación al arrancar. `lf_season.yaml` calcula el estado y las fechas de una temporada de 28 días. `lf_themes.yaml` define la presentación de la temporada.

## Persistencia

`champion_db.py` mantiene jugadores, días, semanas, años y penalizaciones en SQLite. Los cierres usan claves únicas y actualizaciones para evitar duplicar actividad al repetirse. Las misiones no se guardan en SQLite en esta versión.

`champion_history.py` y `champion_active_penalties.py` leen la base para los sensores de histórico y penalizaciones activas. Sus respuestas JSON permiten mostrar errores sin inventar resultados. `lf_database.yaml` enlaza las escrituras de los scripts con los comandos Python; `lf_history.yaml` y `lf_admin.yaml` enlazan las lecturas y el control de penalizaciones.

Los scripts que escriben comprueban el helper de mantenimiento. El cierre diario comprueba además la fecha de inicio de temporada y la semana a la que pertenecen las misiones. El cálculo de temporada informa del período; no hay un cambio automático a una temporada nueva ni una migración de sus recursos.

## Paneles

Los paneles de jugador incluyen únicamente su pestaña Level Up Family. El panel de padres contiene Control, Histórico, Tareas y premios y Familia. El módulo local `level-up-family-cards.js` registra las tarjetas de administración, misiones, premio y familia, usando el objeto `hass` de Home Assistant y nodos de texto para los nombres y recompensas. No hay pestañas de domótica general ni referencias a dispositivos de la casa. Los nuevos jugadores aparecen como vistas del panel compartido de hijos.

## Gestión de familia

`custom_components/level_up_family` carga `family.json` de versión 2, publica `sensor.champ_family` y registra la acción `level_up_family.manage_family` con autorización de administrador en el servidor. Su registro mantiene separados el identificador público, el nombre visible, el prefijo de entidades, la clave SQLite y la ruta de panel. Los comandos del motor aceptan también el formato inicial de versión 1; la interfaz requiere la versión 2.

Las operaciones se serializan mediante un bloqueo y validan la revisión del registro. Cambiar nombre o retirar actualiza metadatos, conserva las identidades numéricas de SQLite y mantiene las tablas de actividad. Los hijos retirados quedan fuera del catálogo y los cierres activos, pero siguen en el histórico y sus multas pendientes continúan consultables. Al actualizar paneles se sustituyen las vistas del juego por sus plantillas; las otras vistas y los ajustes generales se conservan.

Una alta se prepara con un token que caduca a los diez minutos. Aplicarla pone el juego en mantenimiento, espera a que terminen los scripts, copia SQLite y los helpers, genera el paquete del nuevo jugador y amplía tareas y automatizaciones. Después valida la configuración de HA y guarda `family_pending.json` antes del reinicio. Al arrancar restaura helpers, comprueba las entidades del nuevo jugador, sincroniza SQLite y actualiza paneles antes de recuperar el estado previo de mantenimiento. Una recuperación incompleta mantiene el juego en mantenimiento y publica el error.

`templates.json` contiene las plantillas genéricas utilizadas para generar paneles y altas. Se reconstruye con `python tools/build_family_templates.py`; una prueba verifica que coincide con los YAML y valores iniciales de origen. El cambio de estilo de las vistas administradas debe actualizar también este archivo generado.

## Compatibilidad

Se conservan prefijos internos históricos (`champ_`, `champion_`) para mantener las referencias entre módulos. Las claves públicas son identificadores estables como `player1`, `player2` y `player3`; el nombre visible y estado activo se describen en `family.json`. El generador `tools/configure_family.py` prepara la configuración completa desde un archivo privado, usando los dos jugadores incluidos como plantillas. Cambiar un nombre visible conserva la identidad; cambiar una clave interna de una instalación existente requiere migrar el estado.

