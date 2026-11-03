"""Generate an isolated HA configuration for a family; never edit a live installation."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil

import yaml

ROOT = Path(__file__).resolve().parent.parent


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


Dumper.add_representer(str, lambda d, v: d.represent_scalar(
    'tag:yaml.org,2002:str', v, style='|' if '\n' in v else None))


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, Dumper=Dumper, allow_unicode=True,
                              sort_keys=False, width=110), encoding='utf-8', newline='\n')


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def transform(value, function):
    if isinstance(value, str):
        return function(value)
    if isinstance(value, list):
        return [transform(v, function) for v in value]
    if isinstance(value, dict):
        return {function(k): transform(v, function) for k, v in value.items()}
    return value


def identity(value, old, new):
    return transform(value, lambda s: s.replace(old, new))


def markup_name(name):
    # Names must remain literal even in HA markdown/Jinja and JS-generated HTML.
    return html.escape(name, quote=True).replace('{', '&#123;').replace('}', '&#125;')


def label(value, player):
    value = deepcopy(value)
    key, name = player['id'], player['name']
    for node in walk(value):
        for field in ('name', 'alias', 'title', 'heading', 'description'):
            if isinstance(node.get(field), str):
                node[field] = node[field].replace(key, name)
        confirmation = node.get('confirmation')
        if isinstance(confirmation, dict) and isinstance(confirmation.get('text'), str):
            confirmation['text'] = confirmation['text'].replace(key, name)
        if isinstance(node.get('content'), str) and node['content'].strip() == '### ' + key:
            node['content'] = '### ' + markup_name(name) + '\n'
        if isinstance(node.get('tooltip'), str):
            node['tooltip'] = node['tooltip'].replace(key, '${' + json.dumps(markup_name(name)) + '}')
    return value


def package_for(source, player, base):
    key = player['id']
    data = identity(load(source / f'lf_{base}.yaml'), base, key)
    # A visible-name change must never change Home Assistant entity IDs.
    for block in data.get('template', []):
        for domain in ('sensor', 'binary_sensor'):
            for sensor in block.get(domain, []):
                sensor.setdefault('default_entity_id', domain + '.' + sensor['unique_id'])
    data = label(data, player)
    if not player['active']:
        data['automation'] = []
        for script in data.get('script', {}).values():
            script['sequence'].insert(0, {'condition': 'template', 'value_template': '{{ false }}'})
    return data


def child_panel(source, player, base):
    key = player['id']
    panel = identity(load(source / f'{base}.yaml'), base, key)
    panel = label(panel, player)
    if not player['active']:
        # A stale HA sidebar registration cannot expose retired mission buttons.
        panel['views'] = [{'title': player['name'], 'path': key + '-luf',
                           'cards': [{'type': 'markdown', 'content': 'Este jugador está retirado. Su histórico se conserva en el panel de padres.'}]}]
        return panel
    profile = panel['views'][0]['sections'][0]['cards'][1]['custom_fields']
    profile['content'], count = re.subn(r'(?m)^(\s*)' + re.escape(key) + r'\s*$',
                                       lambda m: m[1] + '${' + json.dumps(markup_name(player['name'])) + '}',
                                       profile['content'])
    if count != 1:
        raise ValueError('Ha cambiado la plantilla del nombre del jugador; revisa el generador.')
    return panel


def parents_panel(panel, players):
    panel = deepcopy(panel)
    active = [p for p in players if p['active']]
    control, history, editor = panel['views'][:3]
    sections = control['sections']
    fines = deepcopy(sections[3])
    fine_grid = fines['cards'][0]['cards'][1]
    prototype = deepcopy(fine_grid['cards'][0])
    fine_grid['columns'] = min(2, len(active))
    fine_grid['cards'] = [label(identity(prototype, 'player1', p['id']), p) for p in active]
    corrections = deepcopy(sections[5])
    prototype = deepcopy(corrections['cards'][0])
    corrections['cards'] = [label(identity(prototype, 'player1', p['id']), p) for p in active]
    control['sections'] = [sections[0],
                           *[label(identity(sections[1], 'player1', p['id']), p) for p in active],
                           fines, sections[4], corrections, sections[6]]
    sections = history['sections']
    years = []
    for player in players:
        section = label(identity(sections[2], 'player1', player['id']), player)
        if not player['active']:
            section['cards'][0]['heading'] += ' (retirado)'
        years.append(section)
    history['sections'] = [*sections[:2], *years, *sections[4:]]
    admin = editor['sections'][0]['cards'][0]
    admin['players'] = {p['id']: p['name'] for p in active}
    admin['rewards'] = {p['id']: f"input_text.luf_{p['id']}_weekly_reward" for p in active}
    names = json.dumps({p['id']: markup_name(p['name']) for p in players})
    pattern = r"p === 'player1' \? 'player1' :\s*p === 'player2' \? 'player2' : p"
    return transform(panel, lambda s: re.sub(pattern, lambda _: '(' + names + ')[p] || p', s))


def task_package(package, players, defaults):
    package = deepcopy(package)
    package['input_text'] = {f"luf_task_config_{t['id']}": {
        'name': 'Level Up Family - Configuración tarea ' + t['id'], 'max': 255,
        'icon': 'mdi:clipboard-edit-outline'} for t in defaults}
    return package


def core_package(package, players):
    package = deepcopy(package)
    fields = package['script']['luf_aplicar_penalizacion']['fields']
    fields['player_key']['description'] = 'Identificador estable del jugador configurado en family.json.'
    return package


def generate(family_path, output, source=ROOT):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output == source or output.is_relative_to(source / 'config'):
        raise ValueError('Elige una carpeta de salida nueva, fuera de config. Nunca uses /config de HA como salida.')
    spec = importlib.util.spec_from_file_location('family_schema', source / 'config/level_up_family/python/luf_db.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    players = module.validate_family(load(family_path))
    active = [p for p in players if p['active']]
    defaults_source = json.loads((source / 'config/level_up_family/task_defaults.json').read_text(encoding='utf-8'))['tasks']
    if any(sum(t['player'] == key for t in defaults_source) != 10 for key in ('player1', 'player2')):
        raise ValueError('Las plantillas deben conservar diez espacios por jugador; adapta el generador si amplías el catálogo.')
    cfg = output / 'config'
    # Only source configuration is copied; runtime databases/overrides are never read.
    shutil.copytree(source / 'config', cfg, ignore=shutil.ignore_patterns('data', '__pycache__', '*.pyc'))
    packages = cfg / 'packages/level_up_family'
    panels = cfg / 'panel/level_up_family'
    defaults, weekly, dashboards = [], [], {}
    for player in players:
        key = player['id']
        base = 'player1' if key == 'player1' else 'player2'
        save(packages / f'lf_{key}.yaml', package_for(source / 'config/packages/level_up_family', player, base))
        save(panels / f'{key}.yaml', child_panel(source / 'config/panel/level_up_family', player, base))
        for i, task in enumerate((t for t in defaults_source if t['player'] == base), 1):
            item = identity(task, base, key)
            item['id'] = f"task{(int(key[6:]) - 1) * 10 + i:02}"
            defaults.append(item)
        if not player['active']:
            continue
        automations = identity(load(source / 'config/packages/level_up_family/lf_weekly.yaml')['automation'][:2], 'player1', key)
        # Keep every close on Monday, shortly after the daily consolidation.
        when = datetime(2000, 1, 1, 0, 10) + timedelta(seconds=10 * (len(dashboards)))
        if when.day != 1:
            raise ValueError('Demasiados jugadores para escalonar los cierres dentro del mismo día.')
        automations[1]['triggers'][0]['at'] = when.strftime('%H:%M:%S')
        weekly.extend(label(automations, player))
        dashboards['level-up-family-' + key] = {'mode': 'yaml', 'title': 'Level Up Family - ' + player['name'],
            'icon': 'mdi:gamepad-variant', 'show_in_sidebar': True, 'filename': f'panel/level_up_family/{key}.yaml'}
    # These are known files in the newly created output, never a live directory.
    for key in ('player1', 'player2'):
        if key not in {p['id'] for p in players}:
            (packages / f'lf_{key}.yaml').unlink()
            (panels / f'{key}.yaml').unlink()
    save(packages / 'lf_weekly.yaml', {'automation': weekly})
    save(packages / 'lf_tasks.yaml', task_package(load(source / 'config/packages/level_up_family/lf_tasks.yaml'), players, defaults))
    save(packages / 'lf_core.yaml', core_package(load(source / 'config/packages/level_up_family/lf_core.yaml'), players))
    save(panels / 'parents.yaml', parents_panel(load(source / 'config/panel/level_up_family/parents.yaml'), players))
    (cfg / 'level_up_family/task_defaults.json').write_text(json.dumps({'version': 1, 'tasks': defaults}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    registry = {'version': 2, 'revision': 0, 'players': [dict(p, entity_prefix=p['id'], db_key=p['id'],
                dashboard_url='level-up-family-' + p['id'], dashboard_path=p['id'] + '-luf') for p in players]}
    (cfg / 'level_up_family/family.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (cfg / 'panel/level_up_family/children.yaml').write_text('title: Level Up Family\nviews: []\n', encoding='utf-8')
    dashboards['level-up-family-parents'] = {'mode': 'yaml', 'title': 'Level Up Family - Padres',
        'icon': 'mdi:shield-account', 'show_in_sidebar': True, 'require_admin': True,
        'filename': 'panel/level_up_family/parents.yaml'}
    dashboards['level-up-family-children'] = {'mode': 'yaml', 'title': 'Level Up Family - Hijos',
        'icon': 'mdi:account-group', 'show_in_sidebar': True, 'filename': 'panel/level_up_family/children.yaml'}
    # Inclusion tags are written literally; this is a fragment to merge into HA.
    (output / 'configuration.fragment.yaml').write_text(
        'homeassistant:\n  packages: !include_dir_named packages\n\n' +
        yaml.dump({'lovelace': {'dashboards': dashboards}}, Dumper=Dumper, allow_unicode=True, sort_keys=False), encoding='utf-8')
    result = {'active_players': [p['id'] for p in active], 'registered_players': len(players),
              'task_slots': len(defaults), 'output': str(output), 'live_state_modified': False}
    (output / 'generation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', type=Path, required=True, help='Archivo YAML/JSON privado con los jugadores.')
    parser.add_argument('--output', type=Path, required=True, help='Carpeta nueva para revisar los archivos generados.')
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.family, args.output), ensure_ascii=False, indent=2))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')
