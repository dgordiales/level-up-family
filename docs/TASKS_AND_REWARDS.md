🌐 **Language / Idioma:** [English](#english) · [Español](#español)

<a id="english"></a>

# Tasks and rewards

Open **Tasks & Rewards** in the parents' dashboard. The form edits the existing 20 tasks without changing YAML files.

Those 20 tasks belong to the two-player example. The [family generator](FAMILY_CONFIGURATION.md) creates ten slots per registered child and adjusts the form to active players.

## Editing a task

Select a task, edit its fields, and press **Save task**. You can change:

- Name (up to 80 characters).
- Assigned player.
- Difficulty: easy (10 XP), standard (15 XP), important (20 XP), or custom XP between 0 and 100.
- Days of the week.
- Whether the task must be completed on every selected day or only once on any of those days during the week.

Changes apply to the current week. Once a task has progress, only its name can be changed. The server enforces this rule as well as disabling fields in the form. Changes are blocked while a player's weekly close is pending. If two sessions edit simultaneously, an outdated form submission is rejected to avoid overwriting changes.

With no selected days, the task is disabled. The once-per-week option retains the behavior of the school-bag mission: selecting Saturday and Sunday gives two possible days to complete it, but it counts as only one mission and one XP award. Once-per-week tasks are excluded from the perfect-day bonus.

Scheduled totals, XP, goals, perfect days, and weekly closes all use the same catalog. Changing days or player assignment on a task with no progress also recalculates days already closed in the current week. Reassigning keeps the task's progress identifier, so its internal name may still contain the original player's identifier.

This version edits or disables existing slots: 20 in the example, plus ten for every newly added child. Family management creates those new slots with every day disabled. Creating additional slots for an existing child or physically deleting them requires a future catalog extension.

## Weekly reward

Enter each player's reward and select **Save reward**. Each child sees only their own reward, beneath the level, streak, and bonus metrics. The reward remains configured until the parents change it; it is not automatically delivered or cleared at the start of a new week. Empty text displays **Your reward is yet to be decided** (the current interface may show the original Spanish wording).

The card automatically loads `recompensa.png` from the active season's folder, for example `/local/level_up_family/season_01/recompensa.png`. When `sensor.luf_theme.season_path` changes, the picture changes without editing dashboard YAML. A theme may specify a fallback image through `reward_image` under `/local/level_up_family/`. If the image cannot load, a gift icon is displayed. Each season should include its own `recompensa.png`. The image fits an **80 × 80 px** area while preserving aspect ratio.

## Child dashboard

The dashboard retains the seasonal header, name, weekly progress, and XP, daily streak, and penalty metrics. Below are the mission header and task rows using the original design and editable catalog. Level, weekly streak, bonus, and reward appear beneath the missions. Rows show status circles only, without pictograms or a shared background. Corrections for other days of the current week are available only in the parents' dashboard.

## Persistence and installation

`task_defaults.json` supplies initial values only. Changes are stored in `input_text.luf_task_config_*` helpers and rewards in `input_text.luf_<player>_weekly_reward`. They have no `initial` value, so HA restores them after restarting. Include these helpers in backups; do not delete them when updating a season.

The task package is `lf_tasks.yaml`. The JavaScript resource `/local/level_up_family/level-up-family-cards.js?v=2.7.0` must be registered as a **module**. This file registers administration, mission, reward, and family cards. button-card remains in use for the rest of the design. Family management uses `custom_components/level_up_family`; see [Family Configuration](FAMILY_CONFIGURATION.md).

Control and History share dark-blue backgrounds, rounded corners, and seasonal accents with Tasks & Rewards. Native cards retain their controls and confirmations and are styled with card-mod; metrics and tables use button-card styles. Style changes require only a dashboard reload.

Administration is displayed in the parents' dashboard, and its form appears only for administrators. Existing Home Assistant permissions still apply to scripts and helpers.

---

<a id="español"></a>

# Tareas y premios

En el panel de padres, abre **Tareas y premios**. El formulario edita las 20 tareas actuales sin cambiar archivos YAML.

Esas 20 tareas corresponden al ejemplo de dos jugadores. El [generador familiar](FAMILY_CONFIGURATION.md) prepara diez espacios por hijo registrado y ajusta el formulario a los jugadores activos.

## Editar una tarea

Selecciona una tarea, cambia los campos y pulsa **Guardar tarea**. Puedes editar:

- Nombre (hasta 80 caracteres).
- Jugador al que se asigna.
- Dificultad: sencilla (10 XP), estándar (15 XP), importante (20 XP), o XP personalizados entre 0 y 100.
- Días de la semana.
- Si debe completarse cada día elegido o solo una vez en cualquiera de esos días durante la semana.

Los cambios se aplican esta misma semana. Cuando una tarea ya tiene progreso, solo se permite cambiar su nombre. El servidor comprueba esta regla además de bloquear los campos en el formulario. No se permiten cambios mientras está pendiente el cierre de la semana de alguno de los jugadores. Si dos sesiones editan a la vez, se rechaza guardar una versión antigua para evitar pisar cambios.

Sin días seleccionados, la tarea queda desactivada. La opción de una vez por semana conserva el funcionamiento de la misión de mochila: elegir sábado y domingo ofrece dos días para hacerla, pero solo cuenta una misión y una entrega de XP. Las tareas de una vez por semana no forman parte del bonus de día perfecto.

Los totales previstos, XP, objetivos, días perfectos y cierres semanales se calculan desde el mismo catálogo. Al cambiar días o asignación de una tarea sin progreso se recalculan también los días ya cerrados de la semana actual. La reasignación conserva el identificador de progreso de la tarea; su nombre interno puede seguir conteniendo el jugador original.

Esta versión edita o desactiva los espacios existentes: 20 en el ejemplo y diez más por cada alta de un hijo. Las altas desde Familia los crean con todos los días desactivados. Crear espacios adicionales para un jugador existente y eliminarlos físicamente queda para una ampliación del catálogo.

## Recompensa semanal

Escribe el premio de cada jugador y pulsa su botón **Guardar premio**. Cada panel infantil muestra únicamente su propio premio, bajo sus datos de nivel, rachas y bonus. El premio sigue configurado hasta que los padres lo cambien; no se entrega ni se borra automáticamente al cambiar de semana. Un texto vacío muestra **Tu premio está por decidir**.

La tarjeta carga automáticamente `recompensa.png` de la carpeta de la temporada activa, por ejemplo `/local/level_up_family/season_01/recompensa.png`. Al cambiar `sensor.luf_theme.season_path`, cambia también la imagen, sin modificar el YAML del panel. Se puede indicar una imagen alternativa con el atributo `reward_image` del tema, bajo `/local/level_up_family/`. Si el archivo no puede cargar, se muestra el icono de regalo. Cada temporada debe incluir su propio `recompensa.png`. La imagen se muestra en un espacio fijo de **80 × 80 px**, conservando sus proporciones.

## Panel infantil

Conserva la cabecera de temporada, el nombre y progreso semanal y las métricas de XP, racha diaria y multas. Después aparecen la cabecera de misiones y las filas de tareas, con el diseño original y el catálogo editable. Bajo las tareas se muestran el nivel, la racha semanal, el bonus y la recompensa. Las filas usan solo círculos de estado, sin pictogramas ni fondo común. La corrección de otros días de la semana se ofrece únicamente en el panel de padres.

## Persistencia e instalación

`task_defaults.json` contiene solo los valores iniciales. Los cambios se guardan en los helpers `input_text.luf_task_config_*`; los premios, en `input_text.luf_<jugador>_weekly_reward`. No tienen `initial`, por lo que Home Assistant restaura sus valores al reiniciarse. Incluye estos helpers en las copias de seguridad y no los borres para actualizar una temporada.

El paquete de tareas es `lf_tasks.yaml` y el recurso JavaScript es `/local/level_up_family/level-up-family-cards.js?v=2.7.0` (tipo **módulo**). El mismo archivo registra las tarjetas de administración, misiones, recompensa y familia. Se conserva button-card para el resto del diseño. La gestión de hijos utiliza la integración local `custom_components/level_up_family`; consulta [Familia](FAMILY_CONFIGURATION.md).

Las pestañas de Control e Histórico comparten con Tareas y premios los fondos azul oscuro, bordes redondeados y acentos de temporada. Las tarjetas nativas conservan sus controles y confirmaciones y se estilizan con card-mod; las métricas y tablas usan los estilos de button-card. Cambiar estos estilos solo requiere recargar el panel.

La administración se muestra en el panel de padres y el formulario solo aparece para administradores. Se mantienen los permisos existentes de Home Assistant sobre scripts y helpers.
