# Level Up Family

Juego familiar de misiones domésticas para Home Assistant. Cada jugador completa misiones, gana XP, sube de nivel y sigue su progreso en temporadas de 28 días.

Esta versión reúne el motor SQLite, los paquetes de Home Assistant, los paneles del juego y los recursos gráficos de la temporada 1. Incluye dos jugadores como ejemplo y un generador para configurar uno, dos o más hijos con nombres propios e identificadores estables `player1`, `player2`, `player3`…

## Qué incluye

- Panel de `player1` y panel de `player2`, cada uno con una única pestaña del juego.
- Configuración familiar central para añadir, renombrar o retirar hijos sin borrar su histórico.
- Panel de padres con Control, Histórico, Tareas y premios y Familia.
- Pestaña de padres **Tareas y premios** para editar las 20 tareas actuales: nombre, XP, jugador y calendario.
- Un premio semanal distinto para cada jugador, visible en su propio panel con el estilo de temporada.
- Misiones, XP, bonus, rachas, niveles, penalizaciones y cierres diarios/semanales.
- Temporada de 28 días, con fecha de inicio configurable y estados pendiente, activa y finalizada.
- Histórico en SQLite y utilidad de limpieza con copia de seguridad.
- Pruebas aisladas y validaciones de YAML, plantillas y referencias.

```text
config/
  custom_components/level_up_family/ Gestión de familia y plantillas de aprovisionamiento
  level_up_family/family.json   Registro familiar de ejecución (versión 2)
  level_up_family/python/       Motor y utilidades de datos
  packages/level_up_family/     Helpers, reglas y automatizaciones
  panel/level_up_family/        player1.yaml, player2.yaml y parents.yaml
  www/level_up_family/season_01/ Recursos gráficos
examples/configuration.yaml    Inclusiones mínimas para Home Assistant
docs/                          Instalación, funcionamiento y próximos cambios
tests/                         Pruebas sin acceso a datos reales
tools/                         Validadores de configuración y paneles
```

Consulta la [instalación](docs/INSTALLATION.md), [Tareas y premios](docs/TASKS_AND_REWARDS.md), la [arquitectura](docs/ARCHITECTURE.md) y la [hoja de ruta](docs/ROADMAP.md).

Los [cambios acumulados y su validación](docs/CHANGES.md) explican el alcance de esta actualización y sus límites.

En **Familia**, dentro del panel de padres, puedes añadir hijos, retirarlos conservando su progreso e histórico y cambiar sus nombres. Las altas requieren un reinicio comprobado de HA; nombres y retiradas se aplican al guardar. Consulta [Configurar la familia](docs/FAMILY_CONFIGURATION.md) para instalar esta función o preparar una familia inicial con el generador.

## Desarrollo

Con Python 3.12 o posterior y Node.js disponibles:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/validate_config.py config
python tools/validate_panels_js.py config/panel/level_up_family
```

Los tests crean bases de datos temporales. No leen ni modifican Home Assistant.

## Alcance de esta copia

El repositorio contiene una distribución anonimizada para una instalación nueva. Los identificadores internos usan el prefijo `luf_`, correspondiente a Level Up Family. Cambiar los nombres visibles no exige renombrar esos identificadores.

La [nomenclatura del repositorio](docs/REPOSITORY_NAMESPACE.md) describe archivos, entidades y rutas. Esta revisión cambia identificadores de ejecución y requiere una migración para instalaciones anteriores; no se ha aplicado a la instalación de HA en uso.

No incluye bases de datos, actividad de jugadores, credenciales, copias de seguridad, dispositivos personales ni otras pestañas de los paneles de la casa. La configuración de ejemplo debe combinarse con la configuración propia de Home Assistant.

La instalación que originó esta copia utiliza otros identificadores de jugador. Sustituirla directamente por estos archivos crearía entidades nuevas: una migración de esa instalación requiere mapear por separado entidades, referencias y claves SQLite. Publicar este repositorio no cambia la instalación en uso.
