"""Admin-only family management for the existing Level Up Family game."""
import asyncio
from copy import deepcopy
from contextlib import closing
import json
import logging
from pathlib import Path
import secrets
import shutil
import sqlite3
import time

try:
    import probatio as vol
except ImportError:  # HA releases before the schema-library migration.
    import voluptuous as vol

from homeassistant.config import async_check_ha_config_file
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.components.lovelace.const import LOVELACE_DATA

from .model import (DOMAIN, atomic, change, child_view, merge_views, new_player_files,
                    parents_views, public_players, save_json, sync_db, validate, yaml_text)

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema({
    vol.Optional('parents_dashboard', default='level-up-family-parents'): str,
    vol.Optional('children_dashboard', default='level-up-family-children'): str,
})}, extra=vol.ALLOW_EXTRA)


class FamilyManager:
    def __init__(self, hass, settings):
        self.hass, self.settings = hass, settings
        self.root = Path(hass.config.config_dir)
        self.app = self.root / 'level_up_family'
        self.file = self.app / 'family.json'
        self.db = self.app / 'data/luf.db'
        self.pending_file = self.app / 'family_pending.json'
        self.registry = validate(json.loads(self.file.read_text(encoding='utf-8')))
        self.templates = json.loads((Path(__file__).parent / 'templates.json').read_text(encoding='utf-8'))
        self.lock = asyncio.Lock()
        self.busy = False
        self.error = ''
        self.plan = None

    @callback
    def publish(self):
        self.hass.states.async_set('sensor.luf_family', len([p for p in self.registry['players'] if p['active']]),
            {'friendly_name': 'Level Up Family · Familia', 'icon': 'mdi:account-group',
             'revision': self.registry['revision'], 'players': public_players(self.registry),
             'active_ids': [p['id'] for p in self.registry['players'] if p['active']],
             'busy': self.busy, 'error': self.error,
             'restart_pending': self.pending_file.exists()})

    def snapshot(self):
        return {s.entity_id: s.state for s in self.hass.states.async_all()
                if s.domain in ('input_number', 'input_text', 'input_datetime', 'input_boolean')
                and s.object_id.startswith('luf_') and s.entity_id != 'input_boolean.luf_maintenance'
                and s.state not in ('unknown', 'unavailable')}

    async def maintenance(self, enabled):
        await self.hass.services.async_call('input_boolean', 'turn_on' if enabled else 'turn_off',
                    {'entity_id': 'input_boolean.luf_maintenance'}, blocking=True)

    async def quiesce(self):
        await self.maintenance(True)
        for _ in range(100):
            running = [s for s in self.hass.states.async_all('script')
                       if s.object_id.startswith('luf_') and (s.state == 'on' or s.attributes.get('current', 0))]
            if not running:
                return
            await asyncio.sleep(.1)
        raise HomeAssistantError('Hay una operación del juego en curso. Inténtalo de nuevo.')

    def backup(self, helpers):
        folder = self.app / 'backups' / ('family_' + time.strftime('%Y%m%d_%H%M%S') + '_' + secrets.token_hex(3))
        folder.mkdir(parents=True)
        save_json(folder / 'helpers.json', helpers)
        save_json(folder / 'family.json', self.registry)
        with closing(sqlite3.connect(self.db)) as source, closing(sqlite3.connect(folder / 'luf.db')) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('No se ha podido verificar la copia de seguridad.')
        return folder

    async def dashboard_configs(self, registry):
        data = self.hass.data[LOVELACE_DATA]
        dashboards = data.dashboards
        paths = {self.settings['parents_dashboard'], self.settings['children_dashboard']}
        paths.update(p['dashboard_url'] for p in registry['players'])
        result = {}
        for path in paths:
            if path not in dashboards:
                raise HomeAssistantError(f'El panel {path} no está registrado en HA.')
            dashboard = dashboards[path]
            result[path] = (dashboard, deepcopy(await dashboard.async_load(False)))
        return result

    async def save_dashboards(self, configs, registry, backup):
        for path, (dashboard, original) in configs.items():
            if path == self.settings['parents_dashboard']:
                managed = parents_views(self.templates, registry)
            else:
                managed = [child_view(self.templates, p) for p in registry['players'] if p['dashboard_url'] == path]
            updated = merge_views(original, managed)
            if updated == original:
                continue
            await self.hass.async_add_executor_job(save_json, backup / ('dashboard_' + path + '.json'), original)
            await self.write_dashboard(dashboard, updated)

    async def write_dashboard(self, dashboard, config):
        if dashboard.mode == 'storage':
            await dashboard.async_save(config)
        else:
            path = Path(dashboard.path).resolve()
            if not path.is_relative_to((self.root / 'panel/level_up_family').resolve()):
                raise HomeAssistantError('Solo se pueden actualizar paneles dentro de panel/level_up_family.')
            await self.hass.async_add_executor_job(atomic, path, yaml_text(config))
            await dashboard.async_load(True)
            self.hass.bus.async_fire('lovelace_updated', {'url_path': dashboard.url_path})

    async def restore_helpers(self, values):
        for entity, value in values.items():
            current = self.hass.states.get(entity)
            if current is None or current.state in ('unavailable', 'unknown'):
                raise HomeAssistantError(f'No se ha recuperado la entidad {entity}; el juego seguirá en mantenimiento.')
            if current.state == value:
                continue
            domain = entity.split('.')[0]
            payload = {'entity_id': entity}
            if domain == 'input_number':
                service, payload['value'] = 'set_value', float(value)
            elif domain == 'input_text':
                service, payload['value'] = 'set_value', value
            elif domain == 'input_datetime':
                field = 'datetime' if current.attributes.get('has_date') and current.attributes.get('has_time') else 'date' if current.attributes.get('has_date') else 'time'
                service, payload[field] = 'set_datetime', value
            else:
                service = 'turn_on' if value == 'on' else 'turn_off'
            await self.hass.services.async_call(domain, service, payload, blocking=True)

    def provision(self, registry, backup):
        player = registry['players'][-1]
        defaults_path = self.app / 'task_defaults.json'
        weekly_path = self.root / 'packages/level_up_family/lf_weekly.yaml'
        package_path = self.root / f"packages/level_up_family/lf_{player['id']}.yaml"
        if package_path.exists():
            raise ValueError('Ya existe la configuración de ese identificador.')
        import yaml
        package, defaults, weekly = new_player_files(self.templates, player,
            json.loads(defaults_path.read_text(encoding='utf-8')),
            yaml.safe_load(weekly_path.read_text(encoding='utf-8')))
        writes = {package_path: yaml_text(package), defaults_path: json.dumps(defaults, ensure_ascii=False, indent=2) + '\n',
                  weekly_path: yaml_text(weekly), self.file: json.dumps(registry, ensure_ascii=False, indent=2) + '\n'}
        saved = []
        for path, content in writes.items():
            relative = str(path.relative_to(self.root))
            old = path.read_text(encoding='utf-8') if path.exists() else None
            saved.append({'path': relative, 'content': old})
        save_json(backup / 'files.json', saved)
        for path, content in writes.items():
            atomic(path, content)
        return saved

    def restore_files(self, saved):
        for item in saved:
            path = (self.root / item['path']).resolve()
            if not path.is_relative_to(self.root.resolve()):
                raise ValueError('Ruta de recuperación inválida.')
            if item['content'] is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, item['content'])

    async def handle(self, call):
        try:
            return await self.manage(call)
        except ValueError as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def manage(self, call):
        async with self.lock:
            if self.pending_file.exists():
                raise HomeAssistantError('Hay un alta pendiente de reinicio o recuperación. No se harán más cambios.')
            operation = call.data['operation']
            if operation == 'prepare_add':
                proposed = change(self.registry, 'add', call.data['revision'], name=call.data.get('name'))
                # Check every dashboard now, before offering a restart.
                await self.dashboard_configs(proposed)
                self.plan = {'token': secrets.token_hex(16), 'expires': time.monotonic() + 600,
                             'registry': proposed, 'revision': self.registry['revision']}
                return {'ok': True, 'token': self.plan['token'], 'name': proposed['players'][-1]['name'],
                        'message': 'Se crearán su panel y diez tareas desactivadas. El progreso existente se conserva. HA se reiniciará para cargar las nuevas entidades.'}
            if operation == 'apply_add':
                if not self.plan or call.data.get('token') != self.plan['token'] or time.monotonic() > self.plan['expires'] or self.plan['revision'] != self.registry['revision']:
                    raise HomeAssistantError('La propuesta de alta ha caducado. Vuelve a prepararla.')
                proposed = self.plan['registry']
            else:
                proposed = change(self.registry, operation, call.data['revision'], call.data.get('player_id'), call.data.get('name'))
            previous = deepcopy(self.registry)
            was_maintenance = self.hass.states.is_state('input_boolean.luf_maintenance', 'on')
            configs = await self.dashboard_configs(proposed)
            backup, saved, restart = None, [], False
            safe_to_resume = False
            self.busy = True
            self.error = ''
            self.publish()
            try:
                await self.quiesce()
                helpers = self.snapshot()
                if operation == 'retire':
                    player = next(p for p in proposed['players'] if p['id'] == call.data['player_id'])
                    prefix = player['entity_prefix']
                    def value(entity):
                        state = self.hass.states.get(entity)
                        return state.state if state else '0'
                    player['retired_summary'] = {
                        'level': value(f'sensor.{prefix}_nivel_luf'),
                        'total_xp': value(f'input_number.luf_{prefix}_points_total'),
                        'weekly_xp': value(f'sensor.{prefix}_xp_semana_efectivo'),
                        'week': value(f'input_text.luf_{prefix}_active_week')}
                backup = await self.hass.async_add_executor_job(self.backup, helpers)
                if operation == 'apply_add':
                    saved = await self.hass.async_add_executor_job(self.provision, proposed, backup)
                    error = await async_check_ha_config_file(self.hass)
                    if error:
                        raise HomeAssistantError('La comprobación de configuración ha rechazado el alta: ' + error)
                    await self.hass.async_add_executor_job(save_json, self.pending_file,
                        {'registry': proposed, 'helpers': helpers, 'maintenance': was_maintenance, 'backup': str(backup)})
                    restart = True
                else:
                    # Metadata is transactional; all activity tables and helper values are untouched.
                    await self.hass.async_add_executor_job(sync_db, self.db, proposed)
                    await self.hass.async_add_executor_job(save_json, self.file, proposed)
                    self.registry = proposed
                    await self.save_dashboards(configs, proposed, backup)
                    safe_to_resume = True
                self.plan = None
            except Exception:
                if not saved and backup and (backup / 'files.json').exists():
                    saved = await self.hass.async_add_executor_job(lambda: json.loads((backup / 'files.json').read_text(encoding='utf-8')))
                if saved:
                    await self.hass.async_add_executor_job(self.restore_files, saved)
                if not restart:
                    await self.hass.async_add_executor_job(sync_db, self.db, previous)
                    await self.hass.async_add_executor_job(save_json, self.file, previous)
                    self.registry = previous
                    for dashboard, original in configs.values():
                        await self.write_dashboard(dashboard, original)
                    safe_to_resume = True
                raise
            finally:
                if not restart and safe_to_resume:
                    await self.maintenance(was_maintenance)
                elif not restart:
                    self.error = 'No se ha podido completar la recuperación. El juego sigue en mantenimiento; conserva la copia de seguridad.'
                self.busy = False
                self.publish()
            if restart:
                async def restart_later():
                    await asyncio.sleep(2)
                    try:
                        await self.hass.services.async_call('homeassistant', 'restart', blocking=True)
                    except Exception as exc:
                        self.error = 'El alta está preparada; reinicia HA desde Configuración para terminarla.'
                        _LOGGER.error('Family restart failed: %s', exc)
                        self.publish()
                self.hass.async_create_task(restart_later())
                return {'ok': True, 'restart': True, 'message': 'Alta comprobada. Home Assistant se está reiniciando; se restaurará el progreso automáticamente.'}
            return {'ok': True, 'message': 'Nombre actualizado.' if operation == 'rename' else 'Hijo retirado. Se conservan su progreso e histórico.'}

    async def started(self, event=None):
        try:
            if self.pending_file.exists():
                pending = await self.hass.async_add_executor_job(lambda: json.loads(self.pending_file.read_text(encoding='utf-8')))
                await self.maintenance(True)
                await self.restore_helpers(pending['helpers'])
                player = pending['registry']['players'][-1]
                for entity in [f"input_text.luf_{player['entity_prefix']}_active_week",
                               f"input_number.luf_{player['entity_prefix']}_points_total"]:
                    state = self.hass.states.get(entity)
                    if state is None or state.state in ('unknown', 'unavailable'):
                        raise HomeAssistantError('Faltan entidades del nuevo hijo; el juego seguirá en mantenimiento.')
                await self.hass.async_add_executor_job(sync_db, self.db, pending['registry'])
                self.registry = pending['registry']
                configs = await self.dashboard_configs(self.registry)
                await self.save_dashboards(configs, self.registry, Path(pending['backup']))
                await self.hass.async_add_executor_job(self.pending_file.unlink)
                await self.maintenance(pending['maintenance'])
            self.publish()
        except Exception as exc:
            self.error = 'No se ha completado la recuperación de la familia: ' + str(exc)
            _LOGGER.exception('Family recovery did not complete; maintenance stays enabled')
            self.publish()


async def async_setup(hass, config):
    settings = config.get(DOMAIN, {})
    settings = {'parents_dashboard': 'level-up-family-parents', 'children_dashboard': 'level-up-family-children', **settings}
    manager = await hass.async_add_executor_job(FamilyManager, hass, settings)
    hass.data[DOMAIN] = manager
    manager.publish()
    schema = vol.Schema({vol.Required('operation'): vol.In(['prepare_add', 'apply_add', 'rename', 'retire']),
                         vol.Optional('revision', default=-1): int, vol.Optional('player_id'): str,
                         vol.Optional('name'): str, vol.Optional('token'): str})
    async_register_admin_service(hass, DOMAIN, 'manage_family', manager.handle,
                                 schema=schema, supports_response=SupportsResponse.ONLY)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, manager.started)
    return True
