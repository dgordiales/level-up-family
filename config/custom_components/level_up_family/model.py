"""Family identities and rendering. No HA imports; never delete gameplay records."""
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import os

import yaml

DOMAIN = 'level_up_family'


def transform(value, function):
    if isinstance(value, str):
        return function(value)
    if isinstance(value, list):
        return [transform(v, function) for v in value]
    if isinstance(value, dict):
        return {function(k): transform(v, function) for k, v in value.items()}
    return value


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate(data):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 2:
        raise ValueError('La familia necesita un registro de versión 2.')
    data = deepcopy(data)
    if type(data.get('revision')) is not int or data['revision'] < 0:
        raise ValueError('Revisión de familia inválida.')
    players = data.get('players')
    if not isinstance(players, list) or not players:
        raise ValueError('Añade al menos un hijo.')
    identities, prefixes, db_keys = set(), set(), set()
    for p in players:
        if not isinstance(p, dict) or not re.fullmatch(r'player[1-9][0-9]{0,5}', p.get('id', '')):
            raise ValueError('Identificador de jugador inválido.')
        if not isinstance(p.get('name'), str) or not 1 <= len(p['name'].strip()) <= 40 or not p['name'].isprintable():
            raise ValueError('El nombre debe tener entre 1 y 40 caracteres, sin saltos de línea.')
        if p['name'] != p['name'].strip() or type(p.get('active')) is not bool:
            raise ValueError('Nombre o estado de jugador inválido.')
        goal = p.setdefault('weekly_goal_pct', 75)
        if type(goal) is not int or not 0 <= goal <= 100:
            raise ValueError('El objetivo semanal debe ser un porcentaje entero entre 0 y 100.')
        for field, seen in [('id', identities), ('entity_prefix', prefixes), ('db_key', db_keys)]:
            value = p.get(field, '')
            if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', value) or value in seen:
                raise ValueError('Las identidades y entidades deben ser únicas y estables.')
            seen.add(value)
        for field in ('dashboard_url', 'dashboard_path'):
            if not isinstance(p.get(field), str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)+', p[field]):
                raise ValueError('Ruta de panel inválida.')
    if not any(p['active'] for p in players):
        raise ValueError('Debe quedar al menos un hijo activo.')
    return deepcopy(data)


def change(data, operation, revision, player_id=None, name=None):
    data = validate(data)
    if type(revision) is not int or revision != data['revision']:
        raise ValueError('La familia ha cambiado en otra sesión. Recarga antes de guardar.')
    if operation == 'add':
        number = max(int(p['id'][6:]) for p in data['players']) + 1
        key = f'player{number}'
        data['players'].append({'id': key, 'name': (name or '').strip(), 'active': True,
            'entity_prefix': key, 'db_key': key, 'dashboard_url': 'level-up-family-children',
            'dashboard_path': key + '-luf'})
    else:
        player = next((p for p in data['players'] if p['id'] == player_id), None)
        if player is None:
            raise ValueError('No se encuentra ese hijo.')
        if operation == 'rename':
            player['name'] = (name or '').strip()
        elif operation == 'retire':
            if not player['active']:
                raise ValueError('Este hijo ya está retirado.')
            player['active'] = False
        else:
            raise ValueError('Operación de familia desconocida.')
    data['revision'] += 1
    return validate(data)


def atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_json(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def yaml_text(value):
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=110)


def sync_db(path, registry):
    """UPSERT only; numeric player IDs, dates and all activity rows stay intact."""
    players = validate(registry)['players']
    with closing(sqlite3.connect(path, timeout=20)) as conn, conn:
        conn.execute('PRAGMA foreign_keys=ON')
        known = {r[0] for r in conn.execute('SELECT player_key FROM players')}
        # Unknown DB identities must be explicitly bound during migration.
        if known - {p['db_key'] for p in players}:
            raise ValueError('Hay jugadores de la base de datos sin vincular. Revisa la migración.')
        for p in players:
            result = conn.execute('UPDATE players SET display_name=?,active=? WHERE player_key=?',
                                  (p['name'], int(p['active']), p['db_key']))
            if result.rowcount == 0:
                conn.execute('INSERT INTO players(player_key,display_name,active,created_at) VALUES(?,?,?,?)',
                  (p['db_key'], p['name'], int(p['active']), datetime.now(timezone.utc).isoformat()))


def public_players(registry):
    return [dict(p, reward_entity=f"input_text.luf_{p['entity_prefix']}_weekly_reward",
                 week_entity=f"input_text.luf_{p['entity_prefix']}_active_week",
                 daily_script=f"script.luf_{p['entity_prefix']}_cerrar_dia",
                 penalty_entity=f"input_number.luf_{p['entity_prefix']}_penalties_this_week")
            for p in registry['players']]


def goal_change(registry, player_id, percentage, revision):
    proposed = validate(registry)
    if type(revision) is not int or revision != proposed['revision']:
        raise ValueError('La familia ha cambiado en otra sesión. Recarga antes de guardar.')
    player = next((p for p in proposed['players'] if p['id'] == player_id and p['active']), None)
    if player is None:
        raise ValueError('No se encuentra ese hijo activo.')
    if type(percentage) is not int or not 0 <= percentage <= 100:
        raise ValueError('El objetivo semanal debe ser un porcentaje entero entre 0 y 100.')
    player['weekly_goal_pct'] = percentage
    proposed['revision'] += 1
    return proposed


def escaped(name):
    return html.escape(name, quote=True).replace('{', '&#123;').replace('}', '&#125;')


def label(value, key, name):
    value = deepcopy(value)
    for node in walk(value):
        for field in ('name', 'alias', 'title', 'heading', 'description'):
            if isinstance(node.get(field), str):
                node[field] = node[field].replace(key, name)
        confirmation = node.get('confirmation')
        if isinstance(confirmation, dict) and isinstance(confirmation.get('text'), str):
            confirmation['text'] = confirmation['text'].replace(key, name)
        if isinstance(node.get('content'), str) and node['content'].strip() == '### ' + key:
            node['content'] = '### ' + escaped(name) + '\n'
        if isinstance(node.get('tooltip'), str):
            node['tooltip'] = node['tooltip'].replace(key, '${' + json.dumps(escaped(name)) + '}')
    return value


def bind(value, players):
    for p in players:
        key, prefix, db_key = p['id'], p['entity_prefix'], p['db_key']
        value = transform(value, lambda s: s.replace('luf_' + key + '_', 'luf_' + prefix + '_')
                          .replace('sensor.' + key + '_', 'sensor.' + prefix + '_'))
        value = transform(value, lambda s: s.replace('binary_sensor.' + key + '_', 'binary_sensor.' + prefix + '_')
                          .replace("x.player_key === '" + key + "'", "x.player_key === '" + db_key + "'"))
        for node in walk(value):
            if node.get('player_key') == key:
                node['player_key'] = db_key
    return value


def child_view(templates, player):
    key = player['id']
    base = 'player1' if key == 'player1' else 'player2'
    view = transform(templates[base + '_panel']['views'][0], lambda s: s.replace(base, key))
    view = label(view, key, player['name'])
    if not player['active']:
        return {'title': player['name'], 'path': player['dashboard_path'], 'icon': 'mdi:account-off',
                'cards': [{'type': 'markdown', 'content': 'Jugador retirado. Su progreso e histórico se conservan en el panel de padres.'}]}
    profile = view['sections'][0]['cards'][1]['custom_fields']
    profile['content'], count = re.subn(r'(?m)^(\s*)' + key + r'\s*$',
                         lambda m: m[1] + '${' + json.dumps(escaped(player['name'])) + '}', profile['content'])
    if count != 1:
        raise ValueError('La plantilla del nombre del panel ha cambiado.')
    view['path'] = player['dashboard_path']
    return bind(view, [player])


def parents_views(templates, registry):
    players = registry['players']
    active = [p for p in players if p['active']]
    views = deepcopy(templates['parents']['views'])
    control, history, editor = views[:3]
    sections = control['sections']
    fines, corrections = deepcopy(sections[3]), deepcopy(sections[5])
    fine_grid = fines['cards'][0]['cards'][1]
    fine_grid['columns'] = min(2, len(active))
    prototype = deepcopy(fine_grid['cards'][0])
    make = lambda value, p: label(transform(value, lambda s: s.replace('player1', p['id'])), p['id'], p['name'])
    fine_grid['cards'] = [make(prototype, p) for p in active]
    corrections['cards'] = [make(sections[5]['cards'][0], p) for p in active]
    control['sections'] = [sections[0], *[make(sections[1], p) for p in active], fines, sections[4], corrections, sections[6]]
    sections = history['sections']
    years = [make(sections[2], p) for p in players]
    for section, p in zip(years, players):
        if not p['active']:
            section['cards'][0]['heading'] += ' (retirado)'
    history['sections'] = [*sections[:2], *years, *sections[4:]]
    admin = editor['sections'][0]['cards'][0]
    admin['players'] = {p['id']: p['name'] for p in active}
    admin['rewards'] = {p['id']: f"input_text.luf_{p['entity_prefix']}_weekly_reward" for p in active}
    names = json.dumps({p['db_key']: escaped(p['name']) for p in players})
    pattern = r"p === 'player1' \? 'player1' :\s*p === 'player2' \? 'player2' : p"
    views = transform(views, lambda s: re.sub(pattern, lambda _: '(' + names + ')[p] || p', s))
    return bind(views, players)


def merge_views(config, managed):
    """Replace only managed paths; preserve unrelated dashboard views and settings."""
    data = deepcopy(config)
    by_path = {v['path']: v for v in managed}
    views = []
    for view in data.get('views', []):
        path = view.get('path')
        views.append(by_path.pop(path, view))
    data['views'] = views + list(by_path.values())
    return data


def new_player_files(templates, player, defaults, weekly):
    """Provision an additional identity without rewriting any existing player helper."""
    key = player['id']
    package = transform(templates['player2_package'], lambda s: s.replace('player2', key))
    for block in package.get('template', []):
        for domain in ('sensor', 'binary_sensor'):
            for sensor in block.get(domain, []):
                sensor.setdefault('default_entity_id', domain + '.' + sensor['unique_id'])
    guard = {'condition': 'template', 'value_template': "{{ '" + key + "' in (state_attr('sensor.luf_family','active_ids') | default([], true)) }}"}
    for script in package.get('script', {}).values():
        script['sequence'].insert(0, deepcopy(guard))
    package = label(package, key, player['name'])
    added = []
    occupied = {t['id'] for t in defaults['tasks']}
    for index, task in enumerate((t for t in templates['defaults']['tasks'] if t['player'] == 'player2'), 1):
        item = transform(task, lambda s: s.replace('player2', key))
        item['id'] = f'task{(int(key[6:]) - 1) * 10 + index:02}'
        if item['id'] in occupied:
            raise ValueError('Los espacios de tareas ya existen. No se sobrescribirá su progreso.')
        # Parents explicitly schedule the new child's tasks after adding them.
        item['days'] = 0
        added.append(item)
    defaults = deepcopy(defaults)
    defaults['tasks'].extend(added)
    weekly = deepcopy(weekly)
    extra = transform(templates['weekly']['automation'][2:4], lambda s: s.replace('player2', key))
    for automation in extra:
        automation.setdefault('conditions', []).insert(0, deepcopy(guard))
    weekly['automation'].extend(label(extra, key, player['name']))
    helpers = {f"luf_task_config_{t['id']}": {'name': 'Level Up Family - Configuración ' + t['id'], 'max': 255}
               for t in added}
    package.setdefault('input_text', {}).update(helpers)
    return package, defaults, weekly


def runtime_tasks(package):
    """Replace pair-specific routing with the authoritative registry sensor."""
    package = deepcopy(package)
    active = "(state_attr('sensor.luf_family','active_ids') | default([], true))"
    members = "state_attr('sensor.luf_family','players') | default([], true)"
    sensor = package['template'][0]['sensor'][0]
    catalog = sensor['attributes']['tasks']
    needle = '{% set ns.tasks = ns.tasks + [task] %}'
    if "task.player in (state_attr('sensor.luf_family'" not in catalog:
        sensor['attributes']['tasks'] = catalog.replace(needle, '{% if task.player in ' + active + ' %}' + needle + '{% endif %}')
    sequence = package['script']['luf_task_mutate']['sequence']
    choices = next(s['choose'] for s in sequence if 'choose' in s)
    readiness = ("{% set ns = namespace(ready=true) %}{% for p in " + members + " %}"
                 "{% if p.active and states(p.week_entity) != now().strftime('%G-W%V') %}"
                 "{% set ns.ready=false %}{% endif %}{% endfor %}")
    for choice in choices:
        for node in walk(choice):
            expression = node.get('value_template')
            if not isinstance(expression, str):
                continue
            if 'active_week' in expression:
                extra = "(player != '' and player != task.player) or " if "player != ''" in expression else ''
                node['value_template'] = readiness + '{{ not task or ' + extra + 'not ns.ready }}'
            else:
                node['value_template'] = expression.replace("['player1','player2']", active).replace("['player1', 'player2']", active)
        if choice['conditions'] == '{{ operation == "reward" }}':
            for node in walk(choice):
                variables = node.get('variables', {})
                if 'reward_entity' in variables:
                    variables['reward_entity'] = "{{ (" + members + " | selectattr('id','eq',player) | selectattr('active') | map(attribute='reward_entity') | list | first) | default('') }}"
        if choice['conditions'] == '{{ operation == "edit" }}':
            recheck = choice['sequence'][-1]['then'][0]['repeat']['sequence']
            recheck[1:] = [{'repeat': {'for_each': '{{ ' + members + " | selectattr('active') | map(attribute='daily_script') | list }}",
                'sequence': [{'action': '{{ repeat.item }}', 'data': {'fecha': '{{ recheck_date }}'}}]}}]
    return package


def protect_player(package, key):
    package = deepcopy(package)
    guard = {'condition': 'template', 'value_template': "{{ '" + key + "' in (state_attr('sensor.luf_family','active_ids') | default([], true)) }}"}
    for script in package.get('script', {}).values():
        if guard not in script['sequence']:
            script['sequence'].insert(0, deepcopy(guard))
    return package
