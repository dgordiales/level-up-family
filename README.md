# Level Up Family

Juego familiar de misiones domésticas para Home Assistant. Cada jugador completa misiones, gana XP, sube de nivel y sigue su progreso en temporadas de 28 días.

Esta primera versión reúne el motor SQLite, los paquetes de Home Assistant, los paneles del juego y los recursos gráficos de la temporada 1. Los dos jugadores usan los identificadores genéricos `player1` y `player2` en todo el código.

## Qué incluye

- Panel de `player1` y panel de `player2`, cada uno con una única pestaña del juego.
- Panel de padres con control e histórico de Level Up Family.
- Misiones, XP, bonus, rachas, niveles, penalizaciones y cierres diarios/semanales.
- Temporada de 28 días, con fecha de inicio configurable y estados pendiente, activa y finalizada.
- Histórico en SQLite y utilidad de limpieza con copia de seguridad.
- Pruebas aisladas y validaciones de YAML, plantillas y referencias.

```text
config/
  level_up_family/python/       Motor y utilidades de datos
  packages/level_up_family/     Helpers, reglas y automatizaciones
  panel/level_up_family/        player1.yaml, player2.yaml y parents.yaml
  www/level_up_family/season_01/ Recursos gráficos
examples/configuration.yaml    Inclusiones mínimas para Home Assistant
docs/                          Instalación, funcionamiento y próximos cambios
tests/                         Pruebas sin acceso a datos reales
tools/                         Validadores de configuración y paneles
```

Consulta la [instalación](docs/INSTALLATION.md), la [arquitectura](docs/ARCHITECTURE.md) y la [hoja de ruta](docs/ROADMAP.md).

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

El repositorio contiene una distribución anonimizada para una instalación nueva. Los nombres internos `champ_*` y `champion_*` se conservan por compatibilidad entre los componentes. Cambiar los nombres visibles no exige renombrar esos identificadores.

No incluye bases de datos, actividad de jugadores, credenciales, copias de seguridad, dispositivos personales ni otras pestañas de los paneles de la casa. La configuración de ejemplo debe combinarse con la configuración propia de Home Assistant.

La instalación que originó esta copia utiliza otros identificadores de jugador. Sustituirla directamente por estos archivos crearía entidades nuevas: una migración de esa instalación requiere mapear por separado entidades, referencias y claves SQLite. Publicar este repositorio no cambia la instalación en uso.
