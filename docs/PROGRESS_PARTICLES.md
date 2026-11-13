# Progress particles / Partículas de progreso

## English

The weekly progress cards in both child dashboards emit continuous glitter whenever progress is greater than zero. Fourteen particles are spread across the right half of the filled segment: at 60% progress, their origins lie between 30% and 60% of the full track. The animation continues while the value is unchanged and disappears at zero or when the percentage is not finite.

Particles use the same primary, secondary, highlight, and glow colors as the bar. They follow the current `sensor.luf_theme` palette, including the success palette after the weekly goal is achieved. Seasonal changes depend on the palettes configured in that sensor; purple and gold are fallback colors. The target marker and XP calculations are unchanged. The effect uses CSS animation without timers or external libraries, does not intercept taps, and is hidden when the browser requests reduced motion.

### Compact home dashboard card

[weekly_progress_card.yaml](../examples/weekly_progress_card.yaml) contains the complete optional card for a home dashboard. It displays completed/planned mission counts beside the weekly XP percentage supplied by the goal sensor. These measures can differ because bonuses, penalties, and mission XP affect the percentage.

The example uses the distribution's `player1` and `player2` entities. Set their visible names in the `jugadores` array. To use another player, update that array and `triggers_update` with the corresponding weekly goal sensor. Existing installations with earlier entity names must keep their current mappings for the theme, general goal, and individual goal sensors.

### Updating an installation

- Update the weekly progress card in each child's dashboard, preserving its existing entity IDs and visible name. The full generic dashboard sources are `config/panel/level_up_family/player1.yaml` and `player2.yaml`.
- Update `config/custom_components/level_up_family/templates.json` so future children and regenerated game views receive the effect. This generated file must stay synchronized with the YAML sources; rebuild it with `python tools/build_family_templates.py` after editing them.
- Add the optional compact card through the dashboard's YAML card editor.

This visual update requires no database migration, progress reset, season change, or JavaScript resource version change. To roll back, restore the previous dashboard cards and provisioning templates. Preserve any local dashboard customizations when replacing files.

## Español

Las tarjetas de progreso semanal de ambos paneles infantiles emiten purpurina continuamente cuando el progreso es mayor que cero. Las catorce partículas se reparten por la mitad derecha del tramo relleno: con un progreso del 60 %, nacen entre el 30 % y el 60 % de la barra completa. La animación continúa con el valor quieto y desaparece al llegar a cero o si el porcentaje no es un número finito.

Las partículas usan los mismos colores primario, secundario, destacado y de brillo que la barra. Siguen la paleta actual de `sensor.luf_theme`, incluida la de éxito al alcanzar el objetivo semanal. Los cambios de temporada dependen de las paletas definidas en ese sensor; el morado y el dorado son colores de respaldo. La marca del objetivo y los cálculos de XP se mantienen. El efecto utiliza animación CSS, sin temporizadores ni bibliotecas externas, no intercepta pulsaciones y se oculta si el navegador solicita reducir el movimiento.

### Tarjeta compacta del inicio

[weekly_progress_card.yaml](../examples/weekly_progress_card.yaml) contiene la tarjeta opcional completa para un panel de inicio. Muestra las misiones completadas y previstas junto al porcentaje semanal de XP que proporciona el sensor de objetivo. Son medidas diferentes: los bonus, las multas y los XP de cada misión influyen en el porcentaje.

El ejemplo utiliza las entidades genéricas `player1` y `player2`. Ajusta sus nombres visibles en el array `jugadores`. Para otro jugador, actualiza ese array y `triggers_update` con su sensor de objetivo semanal. Una instalación con nombres anteriores debe conservar sus vinculaciones actuales para el tema, el objetivo general y los sensores individuales de objetivo.

### Actualizar una instalación

- Actualiza la tarjeta de progreso semanal de cada panel infantil conservando sus entidades y su nombre visible. Las fuentes completas y genéricas están en `config/panel/level_up_family/player1.yaml` y `player2.yaml`.
- Actualiza `config/custom_components/level_up_family/templates.json` para que las futuras altas y las vistas regeneradas reciban el efecto. Este archivo generado debe coincidir con los YAML; se reconstruye con `python tools/build_family_templates.py` después de editarlos.
- Añade la tarjeta compacta opcional mediante el editor YAML de tarjetas del panel.

Esta actualización visual no exige migrar la base de datos, reiniciar el progreso, cambiar la temporada ni modificar la versión del recurso JavaScript. Para volver atrás, restaura las tarjetas y plantillas anteriores. Conserva las personalizaciones locales al sustituir archivos.
