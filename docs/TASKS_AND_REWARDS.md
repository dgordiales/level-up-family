# Tareas y premios

En el panel de padres, abre **Tareas y premios**. El formulario edita las 20 tareas actuales sin cambiar archivos YAML.

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

Esta versión edita o desactiva los 20 espacios existentes. Crear espacios adicionales y eliminarlos físicamente queda para una ampliación del catálogo.

## Recompensa semanal

Escribe el premio de cada jugador y pulsa su botón **Guardar premio**. Cada panel infantil muestra únicamente su propio premio, bajo sus datos de nivel, rachas y bonus. El premio sigue configurado hasta que los padres lo cambien; no se entrega ni se borra automáticamente al cambiar de semana. Un texto vacío muestra **Tu premio está por decidir**.

La tarjeta carga automáticamente `recompensa.png` de la carpeta de la temporada activa, por ejemplo `/local/level_up_family/season_01/recompensa.png`. Al cambiar `sensor.champ_theme.season_path`, cambia también la imagen, sin modificar el YAML del panel. Se puede indicar una imagen alternativa con el atributo `reward_image` del tema, bajo `/local/level_up_family/`. Si el archivo no puede cargar, se muestra el icono de regalo. Cada temporada debe incluir su propio `recompensa.png`. La imagen se muestra en un espacio fijo de **80 × 80 px**, conservando sus proporciones.

## Panel infantil

Conserva la cabecera de temporada, el nombre y progreso semanal y las métricas de XP, racha diaria y multas. Después aparecen la cabecera de misiones y las filas de tareas, con el diseño original y el catálogo editable. Bajo las tareas se muestran el nivel, la racha semanal, el bonus y la recompensa. Las filas usan solo círculos de estado, sin pictogramas ni fondo común. La corrección de otros días de la semana se ofrece únicamente en el panel de padres.

## Persistencia e instalación

`task_defaults.json` contiene solo los valores iniciales. Los cambios se guardan en los helpers `input_text.champ_task_config_*`; los premios, en `input_text.champ_<jugador>_weekly_reward`. No tienen `initial`, por lo que Home Assistant restaura sus valores al reiniciarse. Incluye estos helpers en las copias de seguridad y no los borres para actualizar una temporada.

El nuevo paquete es `lf_tasks.yaml` y el recurso JavaScript es `/local/level_up_family/level-up-family-cards.js?v=2.4` (tipo **módulo**). El mismo archivo registra las tarjetas de administración, misiones y recompensa. Se conserva button-card para el resto del diseño. No se necesita otra tarjeta de HACS ni una integración personalizada.

Las pestañas de Control e Histórico comparten con Tareas y premios los fondos azul oscuro, bordes redondeados y acentos de temporada. Las tarjetas nativas conservan sus controles y confirmaciones y se estilizan con card-mod; las métricas y tablas usan los estilos de button-card. Cambiar estos estilos solo requiere recargar el panel.

La administración se muestra en el panel de padres y el formulario solo aparece para administradores. Se mantienen los permisos existentes de Home Assistant sobre scripts y helpers.
