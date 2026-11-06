# Individual weekly XP goals / Objetivos semanales de XP

## Español

En el panel de padres, abre **Control** y busca **Objetivo semanal** debajo del estado de cada hijo. Introduce un porcentaje entero de 0 a 100 y pulsa **Guardar objetivo**. Cada hijo tiene su propio valor; un porcentaje menor deja más margen para conseguir su premio. Los cambios se aplican a la semana en curso y a las siguientes.

El 100 % es la suma de los XP de las misiones previstas para ese hijo durante la semana. Una misión semanal cuenta una vez aunque tenga varios días posibles. Las tareas sin días no aportan XP previstos.

```text
XP efectivos = max(0, redondear((XP de misiones + bonus diarios) × multiplicador) − multas)
Progreso = 100 × XP efectivos / XP previstos de las misiones
Objetivo conseguido = XP previstos > 0 y progreso real ≥ porcentaje del hijo
```

Los bonus y el multiplicador ayudan a llegar al objetivo: no aumentan el denominador. La racha ganada en la semana anterior activa el multiplicador desde el inicio de esta semana (racha semanal de al menos 1). Al cerrar, conseguir el objetivo aumenta la racha; no conseguirlo la deja en 0 para la semana siguiente. El bonus de día perfecto se consolida al cerrar cada día, como antes. Las multas se descuentan después de multiplicar.

Ejemplo: 820 XP previstos y objetivo del 75 % requieren 615 XP efectivos. Con 500 XP acumulados y multiplicador ×1,25 se obtienen 625 XP y se alcanza el objetivo. Una multa de 20 XP los reduce a 605 y el objetivo queda pendiente.

El objetivo no se compara con el porcentaje redondeado de la pantalla. Puede mostrarse más del 100 % cuando hay bonus; la barra limita su anchura al 100 %. Sin XP previstos no hay objetivo conseguido, incluso si el porcentaje configurado es 0.

El valor se guarda en `level_up_family/family.json`, en `players[].weekly_goal_pct`, antes de confirmar el guardado. Reiniciar HA, renombrar un hijo y cerrar una semana conservan su objetivo. Los nuevos hijos empiezan en 75 %. La acción `level_up_family.set_weekly_goal` exige administrador y rechaza formularios antiguos para impedir sobrescribir cambios de otra sesión. El ayudante global antiguo queda sin uso y sin `initial`.

Al actualizar una instalación con actividad, se incorpora a cada hijo el objetivo global que estuviera en vigor, sin cambiar sus identidades, XP, misiones ni registros SQLite. Los cierres futuros usan el nuevo cálculo. El histórico ya cerrado conserva sus resultados originales; el porcentaje de misiones del histórico sigue siendo una estadística de tareas.

Actualiza los paquetes de jugador, la integración, sus plantillas y los paneles conjuntamente. Registra el módulo `/local/level_up_family/level-up-family-cards.js?v=2.7.0`, reinicia HA para cargar la integración y recarga el navegador. En instalaciones antiguas conserva los identificadores y las rutas de la base de datos: esta función no exige migrar el prefijo de las entidades.

## English

In the parents' **Control** tab, each child's **Objetivo semanal** card accepts an integer percentage from 0 to 100. Save each child separately. Lower values allow more room to miss missions. The setting applies immediately and to future weeks.

The denominator is the scheduled mission XP for that child, counting once-per-week missions once. Daily bonuses and the multiplier earned by the previous weekly streak increase the numerator, while penalties subtract after multiplication. A streak of at least one completed successful week enables the multiplier throughout the current week. Settlement evaluates the same score and then advances or clears the streak. No scheduled XP means no achieved goal. Comparison uses the unrounded score.

Settings are atomically persisted as `players[].weekly_goal_pct` in `level_up_family/family.json`. Only administrators may call `level_up_family.set_weekly_goal`; stale family revisions are rejected. Restarts, renames and weekly settlement retain the value. New children default to 75%. Existing installations inherit their current global target during the upgrade. Existing activity and closed historical results are preserved.

Update the player packages, integration, provisioning templates and dashboards together; register the frontend module with `?v=2.7.0`, restart HA and refresh the browser. Keep existing entity bindings and database paths when upgrading a legacy installation.
