# Editing closed weeks / Editar semanas cerradas

## English

The parents' **History** tab includes **Edit closed weeks**. Choose a child and a closed week, change the task marks for the relevant dates, enter a reason, and select **Preview recalculation**. Review every affected week before confirming. Only Home Assistant administrators can use the service, including direct WebSocket calls.

The calculation uses the archived task names, schedules, XP values, once-per-week flags, daily bonus, weekly multiplier, goal percentage, and reward text. Weekly missions count once and do not participate in perfect-day checks. The previous week's achieved goal determines the multiplier of the next week. Penalties remain the amounts recorded in the closed weeks. Levels use the existing 500 XP rule.

The preview includes task XP, perfect days, bonus, penalties, effective XP, goal/reward eligibility, daily and weekly streaks, and levels. Changes propagate chronologically, including across ISO years. Annual summaries and the live lifetime XP/streak helpers are synchronized after saving. Current-week task marks and reward text are preserved. This recalculates reward eligibility; it does not deliver or revoke a prize or payment already given.

### Old weeks that only contain summaries

Older versions did not archive individual task marks. Their exact daily task record cannot be reconstructed from a weekly total. The editor therefore asks you to complete the **original record** first. The initial suggestion uses the current task catalog and settings: check the historical names, XP, planned days, once-per-week flags, goal, multiplier, bonus, initial streaks, and reward. Then enter the original completion marks and validate them.

Validation requires the same mission counts, task XP, perfect-day count/pattern, bonus, final daily streak, and achieved goal as the saved history. It does not rewrite that summary or any live helper. A saved manual XP adjustment is retained, including historical rounding differences. An unchanged save does nothing. There is no automatic data migration, player-specific correction, or reapplication of past XP.

If an edit would change an unarchived successor's multiplier, or its daily record is missing, complete that successor's original record too. The service refuses to guess old rules or missing days. Use **Discard changes** to reload a week; incomplete drafts are not saved.

### Installation and upgrading

Update the complete custom integration (including `history.py` and `history_store.py`), `python/luf_db.py`, `python/prepare_reset.py`, both player packages, the parents' panel, generated `templates.json`, and the card resource. New player provisioning includes the archive action automatically. Keep existing stable player IDs, helper aliases and SQLite keys when adapting an existing installation; do not overwrite `family.json`, task configuration, activity data, or customized household dashboards with distribution defaults.

Register the updated JavaScript resource as `/local/level_up_family/level-up-family-cards.js?v=2.8.0` and restart Home Assistant after updating the integration. The new card type is `custom:level-up-family-history`, placed inside the existing History view. The surrounding cards and their styling are unchanged. In an installation with custom helper aliases, the weekly-close action must pass the public family `player_id`, not its database key or helper prefix.

Weekly close archives the complete original record **after the SQLite close and before resetting task masks**. Archive failure stops the reset, so the original marks remain available for retry. A retry cannot overwrite an existing snapshot or capture masks belonging to the following week.

### Persistence and recovery

The additive SQLite tables `week_history` and `history_sync` store original records, revisions, edit reasons, before/after values and pending absolute helper targets. Existing weeks, days, players and penalties are not rewritten when the editor is first loaded. Saving rejects stale previews, creates a verified SQLite/helper backup under `level_up_family/backups`, pauses game scripts and commits all affected history in one transaction. Failed database writes roll back the entire correction.

After commit, a durable journal synchronizes absolute helper values. A failure leaves maintenance enabled; restarting Home Assistant retries pending synchronization. Preserve the backup if recovery reports an error. The offline reset tool recognizes the new activity tables and includes them in its verified backup and explicit reset. Backups and audit records are local to the installation.

## Español

La pestaña **Histórico** del panel de padres incorpora **Editar semanas cerradas**. Selecciona una semana, cambia las tareas de los días que corresponda, explica el motivo y pulsa **Previsualizar recálculo**. Revisa las semanas afectadas y confirma el guardado. El servicio comprueba que el usuario sea administrador, también si se llama directamente por WebSocket.

El recálculo utiliza las tareas y reglas archivadas de cada semana: nombres, días previstos, XP, tareas de una vez por semana, bonus diario, multiplicador, objetivo y texto de la recompensa. Las tareas semanales cuentan una sola vez y no intervienen en el día perfecto. El objetivo de una semana determina la racha y el multiplicador de la siguiente. Se conservan las multas registradas. Los niveles siguen usando 500 XP por nivel.

La previsualización muestra misiones, XP de tareas, días perfectos, bonus, multas, XP final, objetivo/derecho a recompensa, rachas y niveles. Propaga los cambios a las semanas posteriores, incluso si cambia el año ISO. Al guardar se actualizan los resúmenes anuales y los controles de XP acumulado y rachas. Las marcas de tareas de la semana actual y el texto de su recompensa se conservan. Un premio o pago ya entregado debe revisarse manualmente.

### Semanas antiguas

Las versiones anteriores solo guardaban el resumen semanal y el resultado de los días. El detalle exacto de tareas no puede deducirse de esos totales. Completa primero el **registro original**, revisando la propuesta basada en la configuración actual, y valídalo contra el resumen existente. Puedes ajustar los nombres, XP, días previstos y reglas originales.

La validación exige que coincidan las misiones, XP de tareas, bonus, número/patrón de días perfectos, racha diaria final y objetivo conseguido. No cambia el resumen ni el progreso vivo. Conserva los ajustes manuales de XP y las diferencias históricas de redondeo; guardar las mismas marcas no vuelve a sumar puntos. No se ejecuta ninguna corrección particular al instalar o abrir el editor.

Si falta el registro de una semana posterior y resulta necesario para cambiar su multiplicador o reconstruir sus días, el editor pedirá completar también ese registro. No inventa los datos originales. **Descartar cambios** vuelve a cargar el registro guardado.

### Actualización y recuperación

Actualiza la integración completa, los dos scripts Python indicados arriba, los paquetes de jugadores, el panel de padres, las plantillas generadas y el recurso JavaScript con `?v=2.8.0`. Reinicia Home Assistant. En instalaciones personalizadas, conserva las identidades, alias y claves existentes; adapta los archivos completos sin sustituir la configuración familiar o los paneles domésticos por los valores genéricos del repositorio.

El cierre semanal archiva los datos antes de borrar las marcas. Si falla el archivo, se detiene el borrado para poder reintentarlo. Las tablas nuevas son aditivas y el primer acceso no recalcula las semanas existentes. Cada corrección incluye copia de seguridad comprobada, revisión contra cambios simultáneos y auditoría local. Un fallo de escritura revierte toda la transacción. Si falla la sincronización de controles después del guardado, el juego permanece en mantenimiento y se reintenta al reiniciar Home Assistant. Conserva la copia de seguridad si aparece un error de recuperación.
