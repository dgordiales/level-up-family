🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# Roadmap

The project is developed through branches and pull requests. The improvements below are planned and have not yet been implemented.

## New seasons

Prepare each season on its own branch, including its assets in \`season_XX\`, labels, and visual configuration. Its PR should specify duration, proposed start date, added assets, and checks of all three dashboards. Keep the asset deployment separate from switching the active season or resetting progress. Content updates must not delete history.

## Mission management from the parents' dashboard

The existing 20 tasks can already be edited (name, XP, player, days, and frequency), disabled, and assigned a reward per player under **Tasks & Rewards**. Rule changes affect the current week only if a task has no progress. Stale forms and changes to rules of tasks with progress are rejected.

Adding a child creates ten new task slots. Creating more slots for an existing player, reordering tasks, and removing slots from the interface remain planned. A history of delivered rewards is also pending. The card already displays a season-specific \`recompensa.png\` at 80 × 80 px; artwork must be supplied for each season. Extensions must preserve stable identifiers and provide a migration path for existing progress.

## Family configuration

The **Family** tab already supports adding and retiring children and changing display names, while preserving identities, helpers, and history. The generator can also prepare a new installation for one or more children. See [Family Configuration](FAMILY_CONFIGURATION.md).

Reactivating a retired child from the dashboard remains to be implemented, especially after several weeks away: it requires reconciling the active week, task masks, and streaks. At least one child must remain active.

## Localization

Move all user-facing text into a separate translation catalog so labels and messages can be translated without changing game logic. The language selection and translation files are planned features, not yet available.

## Optional allowance bonus

For families that give their children a weekly allowance, add an optional monetary bonus tied to weekly results. This should remain completely optional and separate from XP and existing reward logic.

## Pull request requirements

- Describe the behavioral change and how it was tested.
- Run data, season, configuration, and dashboard JavaScript tests.
- Keep identifiers generic; exclude real data, backups, and credentials.
- Visually test changes in Home Assistant before deploying.
- Include migration and rollback instructions for changes affecting persistent state.

---

<a id="español"></a>

# Próximos cambios

El proyecto se desarrolla mediante ramas y pull requests. Las ampliaciones siguientes están pendientes.

## Temporadas nuevas

Preparar cada temporada en una rama, con sus recursos en `season_XX`, textos y configuración visual. Su PR debe indicar duración, fecha propuesta, recursos añadidos y comprobaciones de los tres paneles. Mantener separado el despliegue de los recursos del cambio de temporada y de cualquier reinicio de progreso. Evitar que una actualización de contenido borre el histórico.

## Administración de misiones desde padres

Ya se pueden editar las 20 tareas actuales (nombre, XP, jugador, días y frecuencia), desactivarlas y definir un premio por jugador desde **Tareas y premios**. Los cambios de reglas se aplican esta semana si la tarea todavía no tiene progreso; los formularios antiguos y los cambios de reglas con progreso se rechazan.

Cada alta de un hijo crea diez espacios nuevos. Queda crear espacios adicionales para un hijo existente, ordenar tareas y retirar espacios desde la interfaz. También queda el historial de premios entregados. La tarjeta ya admite `recompensa.png` por temporada y la muestra a 80 × 80 px; el arte debe aportarse para cada temporada. Las ampliaciones deberán mantener identificadores estables e incluir una migración del progreso existente.

## Configuración familiar

La pestaña **Familia** ya permite altas, retiradas y cambios de nombre desde padres, conservando identidades, helpers e histórico. El generador sigue disponible para preparar una instalación inicial con uno o más hijos. Consulta [Configurar la familia](FAMILY_CONFIGURATION.md).

Queda implementar la reactivación desde el panel, especialmente después de semanas de ausencia: requiere reconciliar semana activa, máscaras y rachas. Esta versión exige mantener al menos un hijo activo.

## Criterios para cada PR

- Describir el comportamiento que cambia y cómo se ha comprobado.
- Ejecutar pruebas de datos, temporadas, configuración y JavaScript de paneles.
- Mantener identificadores genéricos y excluir datos reales, copias y credenciales.
- Probar cambios visuales en Home Assistant antes de desplegarlos.
- Incluir migración y vuelta atrás cuando cambie el estado persistente.

## Personalización de idioma

Extraer todos los textos visibles a un catálogo independiente para facilitar las traducciones sin modificar la lógica del juego. La selección de idioma y los archivos de traducción están pendientes.

## Bonus económico opcional

Para familias con paga semanal, incorporar un incentivo económico configurable en función del resultado de la semana, completamente opcional y separado de los XP y premios existentes.