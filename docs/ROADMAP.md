# Próximos cambios

Esta primera subida fija una base para trabajar mediante ramas y pull requests. Los cambios siguientes están pendientes; no forman parte de la funcionalidad actual.

## Temporadas nuevas

Preparar cada temporada en una rama, con sus recursos en `season_XX`, textos y configuración visual. Su PR debe indicar duración, fecha propuesta, recursos añadidos y comprobaciones de los tres paneles. Mantener separado el despliegue de los recursos del cambio de temporada y de cualquier reinicio de progreso. Evitar que una actualización de contenido borre el histórico.

## Administración de misiones desde padres

Extraer las tareas del código hacia un catálogo persistente editable desde el panel de padres. Definir identificador estable de misión, jugador, nombre, XP, días previstos y estado activo. Permitir crear, editar, desactivar y ordenar tareas sin editar YAML ni perder el histórico. Validar los cambios y ofrecer una vista previa antes de aplicarlos.

La migración deberá convertir los bitmasks actuales sin perder las misiones completadas; definir qué ocurre si se cambia una tarea a mitad de semana; y separar permisos de administración y acciones de jugador. El motor y los paneles deben consumir el mismo catálogo para evitar referencias duplicadas.

## Criterios para cada PR

- Describir el comportamiento que cambia y cómo se ha comprobado.
- Ejecutar pruebas de datos, temporadas, configuración y JavaScript de paneles.
- Mantener identificadores genéricos y excluir datos reales, copias y credenciales.
- Probar cambios visuales en Home Assistant antes de desplegarlos.
- Incluir migración y vuelta atrás cuando cambie el estado persistente.
