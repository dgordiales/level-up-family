# 🎮 Level Up Family

**Las rutinas de casa se convierten en misiones. El progreso, en una aventura compartida.**

Level Up Family es un juego de tareas domésticas para **Home Assistant**. Cada hijo tiene su panel, completa misiones, gana experiencia y sigue su evolución durante temporadas de **28 días**. Los padres acompañan el progreso, organizan las tareas y eligen una recompensa semanal para cada jugador.

Puedes empezar con un hijo o con varios. Los nombres, las tareas y los premios se adaptan a tu familia.

![Banner de la temporada 1 de Level Up Family](config/www/level_up_family/season_01/banner.png)

## Explora el proyecto

- [Qué puedes hacer](#-qué-puedes-hacer)
- [Cómo funciona una semana](#-cómo-funciona-una-semana)
- [Instalación](#-instalación)
- [Configurar tu familia](#-configurar-tu-familia)
- [Temporadas y gráficos](#-temporadas-y-gráficos)
- [Datos y actualizaciones](#-datos-y-actualizaciones)
- [Desarrollo y contribuciones](#-desarrollo-y-contribuciones)
- [Guías y preguntas frecuentes](#-guías-y-preguntas-frecuentes)

## ✨ Qué puedes hacer

### Un panel para cada jugador

Cada hijo dispone de una vista del juego con:

- Cabecera y ambientación de la temporada activa.
- Nombre y progreso hacia su objetivo semanal.
- XP de la semana, racha diaria y multas.
- Misiones del día y sus puntos de experiencia.
- Nivel, racha semanal y estado del bonus.
- Su recompensa semanal, con una imagen propia de la temporada.

Las tareas conservan un formato sencillo: nombre, puntos y una marca para indicar si están completadas. Las correcciones de otros días se realizan desde el panel de padres.

### Un panel para los padres

| Pestaña | Para qué sirve |
| --- | --- |
| **Control** | Consultar el progreso, corregir misiones de la semana activa, aplicar multas y anularlas por su identificador. |
| **Histórico** | Consultar semanas cerradas y resúmenes anuales almacenados en SQLite. |
| **Tareas y premios** | Editar tareas, dificultad, XP, destinatario, días, frecuencia y premio de cada jugador. |
| **Familia** | Cambiar nombres, preparar altas y retirar hijos conservando su progreso y sus registros. |

La gestión de familia comprueba en el servidor que quien realiza los cambios sea administrador. Los demás scripts y helpers siguen sujetos a los permisos de Home Assistant; no hay un sistema independiente de permisos por hijo.

## 🗓️ Cómo funciona una semana

1. **Los padres organizan las misiones.** Cada tarea tiene nombre, jugador, XP y días de aplicación. También puede realizarse una sola vez entre varios días elegidos.
2. **Cada hijo completa sus misiones.** El panel refleja el progreso y los XP de la semana.
3. **Se sigue un objetivo semanal.** El valor inicial es el 75 % de las misiones previstas y puede ajustarse. La recompensa es una descripción del premio que han elegido los padres.
4. **Los cierres consolidan el progreso.** Los cierres diarios y semanales calculan resultados, actualizan rachas y guardan los registros correspondientes. Los XP de la semana y el total histórico tienen funciones distintas: el total se consolida con el cierre semanal.

Los días perfectos y las semanas consecutivas que cumplen el objetivo participan en los bonus. Las multas descuentan XP de la semana y quedan registradas; no eliminan XP del total histórico. Anular una multa conserva su registro y la marca como cancelada.

### Editar tareas sin perder el progreso

- El nombre de una tarea puede cambiar aunque ya tenga progreso.
- Los XP, días, frecuencia o jugador solo pueden cambiar si esa tarea todavía no tiene progreso en la semana activa.
- Sin días seleccionados, la tarea queda desactivada.
- Los formularios antiguos se rechazan si otra sesión ha guardado cambios.
- Las tareas de una vez por semana cuentan una sola vez y no forman parte del bonus de día perfecto.

Los cambios de reglas permitidos se aplican a la semana actual. Consulta los detalles en [Tareas y premios](docs/TASKS_AND_REWARDS.md).

## 🚀 Instalación

Level Up Family combina **paquetes YAML, scripts Python, una integración local y tarjetas de interfaz**. Se instala copiando y combinando su configuración con la de Home Assistant.

### Necesitas

- Home Assistant con acceso a `/config` y soporte de paquetes YAML.
- Python 3 con SQLite en el entorno donde se ejecuta Home Assistant.
- [button-card](https://github.com/custom-cards/button-card) y [card-mod](https://github.com/thomasloven/lovelace-card-mod), instalados y registrados.
- La integración local de `config/custom_components/level_up_family`.
- El recurso `/local/level_up_family/level-up-family-cards.js?v=2.6.0`, registrado como **módulo JavaScript**.
- Una copia de seguridad antes de modificar una instalación existente.

La integración local incluida no se instala desde HACS. HACS puede utilizarse para las tarjetas externas indicadas arriba.

### Primeros pasos

1. **Prepara tu familia.** Puedes utilizar el ejemplo de dos jugadores o seguir el [generador familiar](docs/FAMILY_CONFIGURATION.md) para obtener una configuración inicial con uno o más hijos.
2. **Copia los archivos.** Copia el contenido de `config/` a `/config/`, conservando su estructura. Combina las inclusiones de `examples/configuration.yaml` o del fragmento generado con tu configuración existente.
3. **Inicializa una base nueva**, únicamente para una instalación nueva:

   ```sh
   python3 /config/level_up_family/python/luf_db.py init
   ```

4. **Registra las tarjetas**, comprueba la configuración con Home Assistant y reinicia si es válida.
5. **Elige la temporada y su fecha de inicio** mediante `input_number.luf_season_number` e `input_datetime.luf_season_start`.
6. **Configura tareas y premios desde padres.** Comprueba que `input_boolean.luf_maintenance` esté apagado cuando el juego esté listo para usarse.

La guía de [Instalación](docs/INSTALLATION.md) explica las inclusiones, los requisitos y las comprobaciones. Conserva tu configuración de dispositivos y las otras pestañas de tus paneles al combinar los archivos.

## 👨‍👩‍👧‍👦 Configurar tu familia

El repositorio utiliza nombres genéricos como `player1` y `player2`. Son identificadores estables; el nombre que aparece en el juego se configura por separado.

Una vez instalada la función, abre **Familia** en el panel de padres:

| Acción | Qué ocurre |
| --- | --- |
| **Guardar nombre** | Cambia el nombre visible sin crear otro jugador ni reiniciar sus puntos. |
| **Retirar** | Deja de incluir al hijo en los controles activos y conserva sus helpers, tareas e histórico. Requiere confirmar la retirada. |
| **Preparar alta** | Muestra una propuesta para crear un nuevo jugador. |
| **Aplicar alta y reiniciar HA** | Crea su panel y diez tareas desactivadas, comprueba la configuración y carga las nuevas entidades mediante un reinicio. |

Las altas preparan copias de seguridad y recuperan los valores anteriores de los helpers antes de reanudar el juego. Después puedes activar los días de las nuevas tareas y ajustar sus XP.

Debe quedar al menos un hijo activo. Los identificadores retirados no se reutilizan. La reactivación desde el panel todavía está pendiente; consulta [Configurar la familia](docs/FAMILY_CONFIGURATION.md) antes de realizar cambios manuales sobre una instalación con actividad.

## 🌌 Temporadas y gráficos

### Temporada 1 · THE ORIGIN

La primera temporada se presenta como **THE ORIGIN** y utiliza la carpeta `season_01`. El número y la carpeta permanecen estables para que el cambio de título no cree una temporada distinta ni cambie sus fechas.

Cada temporada dura 28 días naturales: si empieza en una fecha determinada, su último día es esa fecha más 27 días. El panel indica si está pendiente de inicio, activa o finalizada.

### Dónde van las imágenes

Los recursos se organizan por temporada:

```text
config/www/level_up_family/
├── level-up-family-cards.js
├── season_01/
│   ├── banner.png
│   ├── fondo_vertical.png
│   ├── recompensa.png
│   ├── icono_xp.png
│   ├── icono_nivel.png
│   ├── icono_mision.png
│   ├── icono_penalizacion.png
│   ├── icono_racha.png
│   ├── icono_semana.png
│   ├── icono_temporada.png
│   └── icono_bonus.png
└── season_XX/
    └── ...
```

`season_XX` representa la estructura para otras temporadas, no una carpeta que debas crear literalmente. El catálogo de nombres previsto no implica que todas las temporadas tengan ya sus gráficos o colores propios.

| Recurso | Uso |
| --- | --- |
| `banner.png` | Cabecera de la temporada y vista previa de este README para la temporada 1. |
| `fondo_vertical.png` | Fondo del panel infantil. |
| `icono_*.png` | Iconos de métricas y secciones del juego. |
| `recompensa.png` | Imagen del premio semanal, presentada a **80 × 80 px** conservando sus proporciones. |
| `emblema.png`, `estela.png`, `elementos_flotantes.png` | Recursos complementarios del conjunto gráfico, cuando se incluyan. |

En Home Assistant, `www/level_up_family/season_01` se publica como `/local/level_up_family/season_01`. La tarjeta de recompensa busca la imagen de la temporada activa; si no puede cargarla, utiliza un icono de regalo.

Para añadir una temporada, conserva los nombres esperados de los archivos y revisa su definición en `lf_themes.yaml` y los textos de los paneles. Después regenera las plantillas de aprovisionamiento:

```sh
python tools/build_family_templates.py
```

Subir gráficos o cambiar el título de una temporada no cambia la temporada activa de una instalación de HA, no modifica su fecha de inicio y no reinicia contadores. La transición a otra temporada se configura por separado; no es automática.

## 💾 Datos y actualizaciones

El progreso utiliza dos tipos de almacenamiento:

| Dato | Dónde se conserva |
| --- | --- |
| Marcas de misiones, contadores y ajustes editados | Helpers de Home Assistant. |
| Jugadores, cierres diarios y semanales, resúmenes anuales y multas | SQLite: `/config/level_up_family/data/luf.db`. |
| Identidades y vinculaciones de la familia | `/config/level_up_family/family.json`. |
| Definiciones iniciales de tareas | `/config/level_up_family/task_defaults.json`. |

Incluye estos elementos en las copias de seguridad. Actualizar imágenes o código no es un motivo para borrar los datos del juego.

Las instalaciones anteriores con otros nombres de entidades o de base de datos necesitan una migración coordinada. La nomenclatura actual usa `luf_`; consulta [Nomenclatura del repositorio](docs/REPOSITORY_NAMESPACE.md) antes de copiar archivos sobre una instalación con progreso.

El repositorio distribuye una configuración genérica. Mantén fuera de publicaciones las bases de datos, copias, credenciales, nombres reales y capturas con información personal. Los recursos de `www` son accesibles desde el frontal de HA: utiliza esa carpeta para imágenes del juego.

## 🛠️ Desarrollo y contribuciones

### Estructura del proyecto

```text
config/
├── custom_components/level_up_family/  Gestión de familia y aprovisionamiento
├── level_up_family/
│   ├── python/                        Motor SQLite y utilidades
│   ├── family.json                    Registro familiar de ejemplo
│   └── task_defaults.json             Tareas iniciales
├── packages/level_up_family/          Reglas, helpers, sensores y automatizaciones
├── panel/level_up_family/             Paneles de jugadores y padres
└── www/level_up_family/               Tarjetas y gráficos de temporadas
docs/                                 Guías y decisiones de funcionamiento
examples/                             Configuración para adaptar a tu instalación
tests/                                Pruebas con datos aislados
tools/                                Generadores y validadores
```

### Comprobar los cambios

Con Python 3.12 o posterior y Node.js disponibles:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/validate_config.py config
python tools/validate_panels_js.py config/panel/level_up_family
node --check config/www/level_up_family/level-up-family-cards.js
```

Las pruebas crean datos temporales y no necesitan conectarse a tu HA. Comprueban el motor, las reglas, la conservación del histórico y la recuperación, entre otros casos. Los validadores estáticos no sustituyen la comprobación de configuración ni la revisión visual en la versión de HA donde vayas a instalar.

Si cambias las fuentes de los paneles o del aprovisionamiento, regenera `templates.json` antes de ejecutar las pruebas. Si añades gráficos, comprueba sus nombres, su apertura y sus rutas además de la sintaxis del código.

Las contribuciones se revisan mediante PR. Describe qué cambia, qué archivos de temporada incluye, cómo lo has comprobado y si necesita migración o despliegue. Mantén separados los cambios de contenido y cualquier operación que reinicie progreso.

## 📚 Guías y preguntas frecuentes

| Quiero… | Guía |
| --- | --- |
| Instalar el juego | [Instalación](docs/INSTALLATION.md) |
| Adaptarlo a mis hijos | [Configurar la familia](docs/FAMILY_CONFIGURATION.md) |
| Cambiar tareas y recompensas | [Tareas y premios](docs/TASKS_AND_REWARDS.md) |
| Entender dónde se guarda cada dato | [Arquitectura](docs/ARCHITECTURE.md) |
| Preparar una actualización desde otra nomenclatura | [Nomenclatura](docs/REPOSITORY_NAMESPACE.md) |
| Consultar el alcance de las funcionalidades incorporadas | [Cambios](docs/CHANGES.md) |
| Ver qué falta por implementar | [Hoja de ruta](docs/ROADMAP.md) |

**¿Sirve para un solo hijo?** Sí. Puedes generar una configuración inicial con un jugador y añadir otros más adelante desde Familia.

**¿Tengo que editar archivos para cambiar una tarea o un premio?** Una vez instalado, esos cambios habituales se hacen desde el panel de padres, respetando las reglas de protección del progreso.

**¿El premio se entrega automáticamente?** El juego muestra el premio y si se alcanza el objetivo. Su entrega la organizan los padres; el texto permanece configurado hasta que lo cambien.

**¿Puedo añadir tareas sin límite desde el panel?** Puedes editar los espacios existentes; cada alta de un hijo crea diez nuevos. Crear espacios adicionales para un jugador existente sigue pendiente.

**¿Añadir gráficos pone en marcha una temporada nueva?** No. La carga de recursos y la configuración de la temporada son pasos distintos.

**¿Qué hago si una alta queda pendiente?** Conserva la copia de seguridad y revisa el error de Familia. Si la recuperación no termina, el juego mantiene el modo de mantenimiento. Sigue la guía de recuperación antes de reanudarlo.
