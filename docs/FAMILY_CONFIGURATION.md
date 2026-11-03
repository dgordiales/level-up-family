# Configurar uno, dos o más hijos

Los dos jugadores del repositorio son un ejemplo. El generador prepara la configuración de tu familia desde **un archivo privado**: nombres, jugadores activos y jugadores retirados. Genera paneles, helpers, espacios iniciales de tareas, recompensas, multas y cierres. No hace falta duplicar manualmente todas las referencias de un jugador.

Una vez instalada esta versión, **Familia**, en el panel de padres, permite cambiar nombres, retirar hijos y dar de alta otros sin editar archivos. El generador que se explica después sirve para preparar una instalación nueva.

## Gestionar desde el panel de padres

- **Guardar nombre** actualiza el nombre visible y el mostrado en el histórico. Conserva los identificadores, las misiones completadas, los XP y los cierres anteriores. No necesita reiniciar HA.
- **Retirar** muestra primero una confirmación. El hijo desaparece de los controles activos y su panel muestra que está retirado. Se conservan sus helpers, las marcas de tareas, los premios y todas las filas de SQLite. Familia muestra un resumen de su progreso al retirarse; Histórico conserva sus semanas y años. Debe quedar al menos un hijo activo.
- **Preparar alta** valida el nombre y muestra una propuesta. **Aplicar alta y reiniciar HA** crea una identidad nueva, su panel y diez tareas inicialmente desactivadas. Comprueba la configuración, guarda una copia de seguridad y reinicia HA para cargar las nuevas entidades. Al arrancar restaura los valores anteriores de los helpers antes de quitar el mantenimiento. Después asigna los días y XP desde Tareas y recompensas.

Las altas nuevas aparecen en el panel **Level Up Family · Hijos**. Los paneles anteriores conservan sus rutas y sus otras pestañas. Los identificadores retirados nunca se reutilizan. Esta versión no incluye una acción de reactivación tras semanas de ausencia; no cambies `active` manualmente en una instalación en uso.

La acción `level_up_family.manage_family` comprueba en el servidor que quien la invoca es administrador. Los formularios rechazan revisiones antiguas si dos sesiones cambian la familia a la vez. Cada operación crea una copia en `/config/level_up_family/backups/family_*`; retirar nunca ejecuta un borrado de datos.

El módulo de interfaz es `/local/level_up_family/level-up-family-cards.js?v=2.5.1`. Es necesario instalar también `config/custom_components/level_up_family`, `lf_family.yaml`, el registro familiar de versión 2 y el panel compartido de hijos. La integración se carga al reiniciar HA. No basta con cambiar la tarjeta JavaScript.

## Actualizar una instalación anterior

Antes de sustituir archivos, realiza una copia completa. No reemplaces `data/`, los valores de los helpers ni `task_defaults.json` con el ejemplo del repositorio. Tampoco sustituyas el registro familiar existente por el ejemplo.

Una instalación antigua necesita vincular una sola vez `id`, `entity_prefix`, `db_key`, `dashboard_url` y `dashboard_path` en su registro de versión 2. Por ejemplo, el identificador público `player1` puede apuntar a entidades `champ_legacy_one_*` y a la clave SQLite `player_1`. Cambiar el nombre visible no cambia esas vinculaciones. Configura `parents_dashboard` y `children_dashboard` en `lf_family.yaml` si sus rutas difieren de las del ejemplo.

Las operaciones desde el panel actualizan solo las pestañas del juego. Las copias contienen los paneles originales para recuperación. Si un alta queda pendiente o HA no puede recuperar todos los helpers, el juego permanece en mantenimiento y Familia informa del problema; conserva `family_pending.json` y su copia de seguridad para resolverlo. No ejecutes un reset para corregir una instalación.

## Identificador y nombre

| Campo | Ejemplo | Significado |
| --- | --- | --- |
| `id` | `player3` | Identidad estable en entidades, tareas y SQLite. No se cambia ni reutiliza. |
| `name` | `Luna` | Nombre visible en paneles, controles e histórico. Puede cambiarse. |
| `active` | `true` | Con `false` el jugador queda retirado, conservando su histórico y helpers. |

Los nombres admiten tildes, espacios y comillas, hasta 40 caracteres. Los identificadores son `player1`, `player2`, `player3`… sin ceros iniciales; no necesitan ser consecutivos. Cambiar el orden del archivo cambia la presentación, no la identidad.

## Preparar los archivos

Con Python 3.12 o posterior y las dependencias de `requirements-dev.txt`, copia `examples/family.yaml` a `family.local.yaml`. Este nombre y `build/` están excluidos de Git para no publicar nombres reales.

Ejemplo de tres hijos:

```yaml
version: 1
players:
  - id: player1
    name: Luna
    active: true
  - id: player2
    name: Leo
    active: true
  - id: player3
    name: Mía
    active: true
```

Para una instalación nueva con un hijo, deja únicamente `player1`. Después genera y valida una carpeta nueva:

```sh
python tools/configure_family.py --family family.local.yaml --output build/family-v1
python tools/validate_config.py build/family-v1/config
python tools/validate_panels_js.py build/family-v1/config/panel/level_up_family
```

La salida contiene `config/`, un resumen `generation.json` y `configuration.fragment.yaml`, que se combina con la configuración existente de HA. Dentro de `config/level_up_family/`, `family.json` contiene la copia generada del registro familiar; conserva el archivo privado original para futuros cambios.

La carpeta de salida debe ser nueva. El generador no instala nada en HA, no lee bases de datos ni sobrescribe una carpeta anterior. No uses `/config` de HA como salida.

## Instalación nueva

Sigue [Instalación](INSTALLATION.md) usando la carpeta `config/` y el fragmento generados. Combina las inclusiones; no reemplaces la configuración de otros dispositivos. Mantén los recursos JavaScript descritos en la guía, incluido el módulo de tarjetas y card-mod.

En el entorno donde se ejecuta el juego:

```sh
python3 /config/level_up_family/python/champion_db.py init
python3 /config/level_up_family/python/champion_db.py players
```

`init` lee `/config/level_up_family/family.json`. Cada hijo activo tendrá su panel, premio y diez espacios iniciales de tareas. `player1` conserva la plantilla de dormir solo; los demás parten de la de higiene personal. Se pueden editar o desactivar desde **Tareas y premios**.

Configura el inicio de temporada y comprueba la configuración en tu versión de HA antes del arranque. Las validaciones del repositorio comprueban archivos y plantillas; la comprobación de configuración y la revisión visual en HA siguen siendo necesarias.

## Flujo offline para instalaciones detenidas

Para el uso habitual utiliza la pestaña **Familia**. El flujo siguiente queda como herramienta de migración para una instalación detenida y revisada; generar de nuevo el ejemplo puede sobrescribir personalizaciones si se copia sin compararlas.

1. Guarda una copia completa de HA y del archivo familiar privado.
2. Cambia `name`, manteniendo `id`, o añade una entrada con un identificador nuevo. Nunca reutilices el de otro hijo retirado.
3. Genera y valida otra carpeta, por ejemplo `build/family-v2`.
4. Con HA y los escritores del juego detenidos, actualiza los archivos del juego. Sustituye únicamente las carpetas `packages/level_up_family/` y `panel/level_up_family/` por sus versiones generadas para evitar archivos antiguos sobrantes. Actualiza el código y los JSON de `level_up_family/`, **conservando siempre `data/`**, las copias de seguridad y los valores de helpers de HA. La salida generada no contiene bases de datos.
5. Combina los registros de paneles de `configuration.fragment.yaml` con los existentes.
6. Sin escritores en ejecución, sincroniza la familia con la base existente:

   ```sh
   python3 /config/level_up_family/python/champion_db.py sync_family
   python3 /config/level_up_family/python/champion_db.py players
   ```

7. Comprueba la configuración, inicia HA y revisa nombres, misiones, premios e histórico. Un jugador nuevo empieza sin actividad; los demás mantienen entidades y contadores.

El generador conserva los identificadores físicos y espacios de tareas aunque cambien el nombre o el orden de un hijo. Los cambios de tareas y premios realizados desde padres continúan en los helpers persistentes; no se sustituyen por los valores iniciales del JSON.

## Retirar y reactivar

Termina primero el cierre de su semana y resuelve las multas pendientes. Cambiar la familia no liquida semanas ni reparte XP automáticamente.

Mantén al hijo en el archivo y cambia solo su estado:

```yaml
- id: player2
  name: Leo
  active: false
```

Aplica el mismo procedimiento de generación, actualización y `sync_family`. El jugador desaparece de selectores, multas nuevas, correcciones y cierres automáticos. Sus tareas dejan de participar en el catálogo activo. Se mantienen sus helpers y metadatos sin reiniciarlos y sus scripts quedan detenidos.

Su panel no aparece en el nuevo fragmento de navegación. Si quedó un registro antiguo en HA, el archivo de panel muestra un aviso de retirada y no ofrece botones de misiones; retira también ese registro de `configuration.yaml`.

SQLite conserva días, semanas, años y multas. El histórico sigue mostrando sus semanas y resúmenes, con una sección marcada como retirado. No borres su fila ni helpers: las relaciones de SQLite tienen borrado en cascada y una eliminación física podría borrar actividad.

Si se omite un identificador del archivo, `sync_family` también lo desactiva en SQLite, pero conviene mantenerlo con `active: false` para conservar sus helpers y nombre en todos los paneles.

Volver a `active: true` permite recuperar la misma identidad en SQLite. Si han pasado semanas desde la retirada, antes de reactivar el juego también hay que reconciliar su semana activa, máscaras y rachas: este generador no automatiza esa migración de progreso. No cambies una fecha de semana sobre máscaras que aún pertenecen a otra. Se requiere al menos un jugador activo.

## Compatibilidad y recuperación

Sin `family.json`, el motor conserva la inicialización compatible con `player1` y `player2`. Un archivo familiar inválido produce un error; no se reemplaza silenciosamente por otros nombres.

Este procedimiento corresponde a instalaciones de **la distribución genérica del repositorio**. Una instalación con claves propias, como `player_1`, o entidades que contienen nombres anteriores necesita una migración específica: copiar estos archivos directamente crearía entidades diferentes. El generador no cambia la instalación original que dio lugar al proyecto.

Para volver atrás, restaura conjuntamente configuración, SQLite y estado de helpers desde la copia anterior. Restaurar solo los YAML no revierte una sincronización de nombres o retiradas en la base.
