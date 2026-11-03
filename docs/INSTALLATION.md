# Instalación

## Requisitos

- Home Assistant con paquetes YAML, plantillas, command_line y shell_command.
- Python 3 en el entorno donde se ejecuta Home Assistant; SQLite forma parte de Python.
- La tarjeta [button-card](https://github.com/custom-cards/button-card), instalada y registrada como recurso JavaScript, para el diseño existente de los paneles.
- [card-mod](https://github.com/thomasloven/lovelace-card-mod), instalado y registrado como recurso JavaScript, para aplicar el estilo de Level Up Family a las tarjetas nativas del panel de padres.
- El módulo local `/local/level_up_family/level-up-family-cards.js?v=2.6.0`, que registra las tarjetas incluidas en este repositorio.
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
6. Establece `input_number.luf_season_number` en `1` y `input_datetime.luf_season_start` en la fecha elegida. Ajusta las reglas de XP, objetivos y penalizaciones desde sus helpers. La fecha determina 28 días naturales, incluyendo el inicio; el último día es inicio + 27 días.
7. Revisa que `input_boolean.luf_maintenance` esté apagado. Cada panel activo debe mostrar nivel 1, XP 0 y misiones pendientes en una instalación nueva. Comprueba temporada, misiones, penalizaciones e histórico con datos de prueba y una copia de seguridad antes de usarlos de forma habitual.

Los enlaces de paneles son `/level-up-family-player1/player1-luf`, `/level-up-family-player2/player2-luf` y `/level-up-family-parents/control-luf`. La segunda pestaña de padres es `historico-luf`. `require_admin` restringe la navegación al panel de padres; no convierte los scripts o helpers en un sistema de permisos por jugador.

En el ejemplo, la gestión de hijos está en `/level-up-family-parents/family`. Debe estar registrado también `/level-up-family-children`, aunque todavía no tenga vistas: se utilizará para las altas futuras. La acción de gestión de familia exige administrador en el servidor; esto no añade permisos individuales a los scripts antiguos del juego. La funcionalidad previa se comprobó en HA 2026.10.4, integración 0.4.1 y tarjetas 2.5.1. Esta revisión usa integración 0.5.0 y una nueva nomenclatura, comprobada en las pruebas del repositorio, sin despliegue en HA. Consulta [Nomenclatura](REPOSITORY_NAMESPACE.md) y comprueba la configuración antes de instalar.

## Reinicios y limpieza

`prepare_reset.py` genera primero un plan y requiere una aplicación explícita para borrar actividad. Consulta `--help` antes de usarlo. Conserva los jugadores y valida el esquema, crea una copia SQLite y limpia días, semanas, años y penalizaciones.

La utilidad actúa únicamente sobre SQLite. No reinicia los helpers de Home Assistant, no cambia los bitmasks de misiones y no pone una temporada en producción por sí sola. Para un reinicio completo hay que guardar y reiniciar también los contadores, las marcas semanales y las fechas de cierre, manteniendo las definiciones de misiones y las reglas. Detén Home Assistant y cualquier otro escritor durante la limpieza offline; no basta con cerrar el navegador. Conserva una copia completa para poder restaurar el estado conjunto.

## Personalización actual

Los nombres, las altas y las retiradas se gestionan desde **Familia**. No hay una acción de reactivación en esta versión. El [generador familiar](FAMILY_CONFIGURATION.md) prepara la instalación inicial y conserva las identidades internas.

Abre **Tareas y premios** en el panel de padres para cambiar nombres, XP, jugador, días y premio semanal. Consulta [Tareas y premios](TASKS_AND_REWARDS.md) para las reglas de protección del progreso. Las notificaciones a teléfonos personales se han retirado de esta distribución. Los nombres de jugador son genéricos también en las claves SQLite y en los identificadores de entidades.

Los recursos de `www/level_up_family/season_01` se sirven en `/local/level_up_family/season_01`. No guardes datos privados en `www`.
