# Cambios acumulados: familia configurable y recompensa de temporada

Este documento describe la actualización respecto a `main` anterior a la gestión de familia. La edición de tareas, los premios individuales y el diseño de los paneles ya existentes se mantienen y se adaptan a más jugadores.

## Cambios de uso

- **Familia en el panel de padres:** cambiar nombres y retirar hijos al guardar; preparar altas con revisión y confirmación de un reinicio de HA. La retirada conserva las identidades, los helpers y la actividad SQLite; no puede retirarse el último hijo activo.
- **Uno o más hijos:** el generador inicial acepta identificadores estables `playerN`, aunque no sean consecutivos, y nombres de hasta 40 caracteres. Genera paquetes, paneles, tareas, premios y automatizaciones sin editar manualmente todas sus referencias.
- **Altas desde HA:** cada hijo nuevo recibe una identidad sin reutilizar las retiradas, una vista en el panel compartido y diez tareas inicialmente desactivadas. Los padres activan sus días y ajustan XP en Tareas y premios.
- **Recompensa:** la imagen de temporada se presenta a **80 × 80 px**, conservando sus proporciones. Se mantiene la selección automática de `recompensa.png` y el icono alternativo si no carga.
- **Histórico y multas:** los jugadores retirados siguen presentes en las lecturas históricas y sus multas pendientes siguen consultables. El catálogo activo y los cierres dejan de incluirlos.

## Componentes y persistencia

La integración local 0.4.1 añade la acción de administrador `level_up_family.manage_family` y `sensor.luf_family`. El registro de versión 2 separa nombre visible, identidad pública, entidades existentes, clave SQLite y ruta de panel. Así se puede migrar una instalación con identificadores anteriores sin crear otros jugadores para los mismos hijos.

Las operaciones validan revisiones para rechazar formularios antiguos. Las altas crean una copia SQLite y del estado de helpers, generan los archivos, comprueban la configuración y guardan la recuperación pendiente antes de reiniciar. El arranque restaura los valores anteriores antes de reanudar. Si no puede completar la recuperación, mantiene el juego en mantenimiento. Las escrituras de metadatos no eliminan las tablas de actividad.

Los cambios extensos en YAML incluyen su serialización y la generalización de referencias de dos jugadores a un registro familiar. Las plantillas de aprovisionamiento se guardan en `templates.json`; una prueba compara ese archivo con las fuentes para evitar desajustes. Consulta la [arquitectura](ARCHITECTURE.md).

## Instalación y límites

Sigue [Instalación](INSTALLATION.md) para una copia nueva y [Configurar la familia](FAMILY_CONFIGURATION.md) para migración, formatos y vuelta atrás. Deben instalarse juntos la integración, los paquetes, el registro, los paneles y el recurso de tarjetas 2.5.1. Actualizar solo JavaScript no habilita Familia.

No se incluyen un reset de progreso ni una nueva temporada. Una instalación con datos propios necesita conservar sus vinculaciones, base de datos, tareas personalizadas y valores de helpers. El registro de ejecución y las copias pueden contener datos personales y deben mantenerse fuera de publicaciones del repositorio.

La reactivación desde padres, la ampliación manual del número de tareas para un jugador existente y el historial de premios entregados siguen pendientes. Las vistas del juego se regeneran desde las plantillas: guarda sus personalizaciones antes de actualizar; las vistas ajenas al juego se conservan. La ruta de nuevas altas es `level-up-family-children`.

## Validación

Los resultados en HA de esta sección corresponden a la funcionalidad previa a la [unificación de nomenclatura](REPOSITORY_NAMESPACE.md). La revisión de nombres 0.5.0 se comprueba en el repositorio y no se ha desplegado en la instalación existente.

- **86 pruebas automatizadas:** motor SQLite y reset aislado; temporadas; catálogo, puntuación y reglas de edición; uno, tres y jugadores no consecutivos; conservación de identidades e histórico; altas, retiradas, revisiones antiguas, rollback y recuperación de helpers tras reinicio.
- Validación estática de **15 YAML**, **379 plantillas Jinja** y **106 plantillas JavaScript** de paneles; comprobación de sintaxis del módulo de tarjetas.
- Comprobación de configuración e instalación en **HA 2026.10.4**. Tras cargar la integración 0.4.1, se compararon los valores de todos los helpers del juego y las filas de jugadores, días, semanas, años y multas: quedaron iguales al estado previo.
- En la instalación real se comprobaron el guardado de un nombre sin cambiar su valor, el rechazo de un formulario antiguo y las propuestas canceladas de alta y retirada. Las mutaciones de alta y retirada con datos de prueba se verificaron en entornos aislados; no se añadieron ni retiraron jugadores reales para probarlas.

Las comprobaciones estáticas y las pruebas con adaptadores de HA no garantizan compatibilidad con otras versiones de HA. Conserva una copia completa y ejecuta la comprobación de configuración de tu instalación antes del despliegue.
