# Próximos cambios

El proyecto se desarrolla mediante ramas y pull requests. Las ampliaciones siguientes están pendientes.

## Temporadas nuevas

Preparar cada temporada en una rama, con sus recursos en `season_XX`, textos y configuración visual. Su PR debe indicar duración, fecha propuesta, recursos añadidos y comprobaciones de los tres paneles. Mantener separado el despliegue de los recursos del cambio de temporada y de cualquier reinicio de progreso. Evitar que una actualización de contenido borre el histórico.

## Administración de misiones desde padres

Ya se pueden editar las 20 tareas actuales (nombre, XP, jugador, días y frecuencia), desactivarlas y definir un premio por jugador desde **Tareas y premios**. Los cambios de reglas se aplican esta semana si la tarea todavía no tiene progreso; los formularios antiguos y los cambios de reglas con progreso se rechazan.

Queda ampliar el catálogo para crear espacios adicionales, ordenar tareas desde la interfaz y retirar espacios sin tocar YAML. También quedan el historial de premios entregados y los iconos de recompensa específicos de cada temporada. La ampliación deberá mantener identificadores estables e incluir una migración del progreso existente.

## Configuración familiar

La composición familiar ya se configura con un archivo privado y el generador descrito en [Configurar la familia](FAMILY_CONFIGURATION.md). Queda una futura interfaz de altas, retiradas y nombres desde padres; deberá coordinar helpers, paneles y SQLite sin borrar identidades históricas.

## Criterios para cada PR

- Describir el comportamiento que cambia y cómo se ha comprobado.
- Ejecutar pruebas de datos, temporadas, configuración y JavaScript de paneles.
- Mantener identificadores genéricos y excluir datos reales, copias y credenciales.
- Probar cambios visuales en Home Assistant antes de desplegarlos.
- Incluir migración y vuelta atrás cuando cambie el estado persistente.
