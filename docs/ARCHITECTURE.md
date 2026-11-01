# Funcionamiento

## Estado de juego

Home Assistant mantiene las misiones semanales en helpers numéricos: cada bit representa un día, del lunes (`1`) al domingo (`64`). Marcar o desmarcar una misión actualiza ese bitmask. Los sensores derivan XP, progreso, objetivos y nivel. Las tareas y sus calendarios todavía están definidos en YAML.

`lf_core.yaml` contiene reglas compartidas y scripts de acceso. `lf_player1.yaml` y `lf_player2.yaml` reúnen los helpers, sensores, acciones y cierres diarios de cada jugador. `lf_weekly.yaml` inicializa la semana y programa su cierre, incluyendo recuperación al arrancar. `lf_season.yaml` calcula el estado y las fechas de una temporada de 28 días. `lf_themes.yaml` define la presentación de la temporada.

## Persistencia

`champion_db.py` mantiene jugadores, días, semanas, años y penalizaciones en SQLite. Los cierres usan claves únicas y actualizaciones para evitar duplicar actividad al repetirse. Las misiones no se guardan en SQLite en esta versión.

`champion_history.py` y `champion_active_penalties.py` leen la base para los sensores de histórico y penalizaciones activas. Sus respuestas JSON permiten mostrar errores sin inventar resultados. `lf_database.yaml` enlaza las escrituras de los scripts con los comandos Python; `lf_history.yaml` y `lf_admin.yaml` enlazan las lecturas y el control de penalizaciones.

Los scripts que escriben comprueban el helper de mantenimiento. El cierre diario comprueba además la fecha de inicio de temporada y la semana a la que pertenecen las misiones. El cálculo de temporada informa del período; no hay un cambio automático a una temporada nueva ni una migración de sus recursos.

## Paneles

Los paneles de jugador incluyen únicamente su pestaña Level Up Family. El panel de padres contiene control e histórico. No hay pestañas de domótica general ni referencias a dispositivos de la casa.

## Compatibilidad

Se conservan prefijos internos históricos (`champ_`, `champion_`) para mantener las referencias entre módulos. Las claves públicas de jugador de esta distribución son `player1` y `player2`. Renombrar una instalación existente requiere una migración de estado, no solamente copiar archivos.
