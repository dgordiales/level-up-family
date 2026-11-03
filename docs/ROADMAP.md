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

