"""Exercise the actual controller with isolated files, SQLite and HA adapter doubles."""
from contextlib import closing
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import yaml

ROOT = Path(__file__).resolve().parent.parent


def module(name, **attributes):
    result = ModuleType(name)
    result.__dict__.update(attributes)
    return result


class States:
    def __init__(self):
        self.data = {}

    def async_set(self, entity, state, attributes=None):
        if entity.startswith('input_number.'):
            state = float(state)
        self.data[entity] = SimpleNamespace(entity_id=entity, state=str(state), attributes=attributes or {},
                domain=entity.split('.')[0], object_id=entity.split('.')[1])

    def get(self, entity):
        return self.data.get(entity)

    def is_state(self, entity, state):
        return self.get(entity).state == state

    def async_all(self, domain=None):
        return [s for s in self.data.values() if domain is None or s.domain == domain]


class Dashboard:
    mode = 'storage'

    def __init__(self, config):
        self.config = deepcopy(config)

    async def async_load(self, force):
        return deepcopy(self.config)

    async def async_save(self, config):
        self.config = deepcopy(config)


class FamilyServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fake_schema = module('probatio', Schema=lambda *a, **k: None, Optional=lambda x, **k: x,
                             Required=lambda x, **k: x, In=lambda x: x, ALLOW_EXTRA=1)
        fake = {'probatio': fake_schema,
                'homeassistant.config': module('homeassistant.config', async_check_ha_config_file=AsyncMock(return_value=None)),
                'homeassistant.const': module('homeassistant.const', EVENT_HOMEASSISTANT_STARTED='started'),
                'homeassistant.core': module('homeassistant.core', SupportsResponse=SimpleNamespace(ONLY=1), callback=lambda f: f),
                'homeassistant.exceptions': module('homeassistant.exceptions', HomeAssistantError=RuntimeError),
                'homeassistant.helpers.service': module('homeassistant.helpers.service', async_register_admin_service=lambda *a, **k: None),
                'homeassistant.components.lovelace.const': module('homeassistant.components.lovelace.const', LOVELACE_DATA='lovelace')}
        self.enterContext(patch.dict(sys.modules, fake))
        component = ROOT / 'config/custom_components/level_up_family'
        spec = importlib.util.spec_from_file_location('lf_controller_test', component / '__init__.py', submodule_search_locations=[str(component)])
        self.component = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.component
        spec.loader.exec_module(self.component)
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        app = self.root / 'level_up_family'
        (app / 'data').mkdir(parents=True)
        self.app = app
        self.registry = json.loads((ROOT / 'config/level_up_family/family.json').read_text(encoding='utf-8'))
        (app / 'family.json').write_text(json.dumps(self.registry), encoding='utf-8')
        (app / 'task_defaults.json').write_bytes((ROOT / 'config/level_up_family/task_defaults.json').read_bytes())
        packages = self.root / 'packages/level_up_family'
        packages.mkdir(parents=True)
        (packages / 'lf_weekly.yaml').write_bytes((ROOT / 'config/packages/level_up_family/lf_weekly.yaml').read_bytes())
        self.db = app / 'data/champion.db'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript('''CREATE TABLE players(id INTEGER PRIMARY KEY AUTOINCREMENT,player_key TEXT UNIQUE,
              display_name TEXT,active INTEGER,created_at TEXT);CREATE TABLE activity(value TEXT);
              INSERT INTO players VALUES(1,'player1','player1',1,'original');
              INSERT INTO players VALUES(2,'player2','player2',1,'original');
              INSERT INTO activity VALUES('retained history');''')
        self.states = States()
        for entity, value in {'input_boolean.champ_maintenance': 'off',
                              'input_number.champ_player1_points_total': '500',
                              'input_number.champ_player1_task_dormir_solo_week': '3',
                              'input_text.champ_player1_active_week': '2026-W45',
                              'input_text.champ_player2_active_week': '2026-W45',
                              'input_number.champ_weekly_goal_pct': '85',
                              'sensor.player1_nivel_champion': '2',
                              'sensor.player1_xp_semana_efectivo': '45'}.items():
            self.states.async_set(entity, value)
        self.dashboards = {path: Dashboard({'views': []}) for path in
            ['level-up-family-parents', 'level-up-family-children', 'level-up-family-player1', 'level-up-family-player2']}
        self.dashboards['level-up-family-player1'].config = {'views': [{'path': 'home', 'cards': ['private house controls']}]}
        async def executor(function, *args):
            return function(*args)
        async def service(domain, name, data, blocking=False):
            entity = data['entity_id']
            self.states.async_set(entity, data.get('value', 'on' if name == 'turn_on' else 'off'))
        self.scheduled = []
        def schedule(coroutine):
            self.scheduled.append(True)
            coroutine.close()
        hass = SimpleNamespace(config=SimpleNamespace(config_dir=str(self.root)), states=self.states,
            services=SimpleNamespace(async_call=service), async_add_executor_job=executor,
            async_create_task=schedule, bus=SimpleNamespace(async_fire=lambda *a: None),
            data={'lovelace': SimpleNamespace(dashboards=self.dashboards)})
        self.manager = self.component.FamilyManager(hass, {'parents_dashboard': 'level-up-family-parents', 'children_dashboard': 'level-up-family-children'})

    def call(self, **data):
        return self.manager.handle(SimpleNamespace(data=data))

    def activity(self):
        with closing(sqlite3.connect(self.db)) as conn:
            return conn.execute('SELECT * FROM activity').fetchall()

    async def test_rename_updates_dashboard_and_metadata_without_touching_progress(self):
        before = self.manager.snapshot()
        reply = await self.call(operation='rename', revision=0, player_id='player1', name='Nombre nuevo')
        self.assertTrue(reply['ok'])
        self.assertEqual(self.manager.snapshot(), before)
        self.assertEqual(self.activity(), [('retained history',)])
        self.assertEqual(self.manager.registry['players'][0]['name'], 'Nombre nuevo')
        self.assertEqual(self.dashboards['level-up-family-player1'].config['views'][0]['cards'], ['private house controls'])
        self.assertFalse(self.manager.pending_file.exists())
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'off'))

    async def test_retire_archives_summary_and_keeps_helpers_and_database_identity(self):
        before = self.manager.snapshot()
        reply = await self.call(operation='retire', revision=0, player_id='player1')
        self.assertTrue(reply['ok'])
        self.assertEqual(self.manager.snapshot(), before)
        self.assertEqual(self.manager.registry['players'][0]['retired_summary']['weekly_xp'], '45')
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute('SELECT id,active,created_at FROM players WHERE player_key="player1"').fetchone(), (1, 0, 'original'))
        self.assertEqual(self.activity(), [('retained history',)])

    async def test_stale_change_returns_a_clear_service_error_without_writing(self):
        before = self.manager.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'otra sesión'):
            await self.call(operation='rename', revision=-1, player_id='player1', name='Old form')
        self.assertEqual(self.manager.snapshot(), before)
        self.assertEqual(self.manager.registry['revision'], 0)

    async def test_failed_dashboard_rollback_keeps_maintenance_enabled(self):
        self.manager.write_dashboard = AsyncMock(side_effect=RuntimeError('Cannot save dashboard'))
        with self.assertRaises(RuntimeError):
            await self.call(operation='rename', revision=0, player_id='player1', name='Try')
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'on'))
        self.assertTrue(self.manager.error)
        self.assertEqual(self.activity(), [('retained history',)])

    async def test_invalid_ha_configuration_rolls_back_provisioning_without_reset(self):
        before = self.manager.snapshot()
        defaults = (self.app / 'task_defaults.json').read_bytes()
        reply = await self.call(operation='prepare_add', revision=0, name='Tres')
        self.component.async_check_ha_config_file.return_value = 'Invalid configuration'
        with self.assertRaises(RuntimeError):
            await self.call(operation='apply_add', token=reply['token'])
        self.assertEqual(self.manager.snapshot(), before)
        self.assertEqual((self.app / 'task_defaults.json').read_bytes(), defaults)
        self.assertFalse((self.root / 'packages/level_up_family/lf_player3.yaml').exists())
        self.assertFalse(self.manager.pending_file.exists())
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'off'))

    async def test_add_restores_all_existing_values_before_finishing_restart(self):
        before = self.manager.snapshot()
        prepared = await self.call(operation='prepare_add', revision=0, name='Tres')
        reply = await self.call(operation='apply_add', token=prepared['token'])
        self.assertTrue(reply['restart'])
        self.assertTrue(self.manager.pending_file.exists())
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'on'))
        self.assertEqual(len(self.scheduled), 1)
        # Simulate HA defaults being restored on startup, then recover the snapshot.
        self.states.async_set('input_number.champ_weekly_goal_pct', '75')
        self.states.async_set('input_number.champ_player3_points_total', '0')
        self.states.async_set('input_text.champ_player3_active_week', '2026-W45')
        await self.manager.started()
        self.assertEqual({k: self.manager.snapshot()[k] for k in before}, before)
        self.assertFalse(self.manager.pending_file.exists())
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'off'))
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute('SELECT player_key FROM players ORDER BY id').fetchall(), [('player1',), ('player2',), ('player3',)])
        self.assertEqual(self.activity(), [('retained history',)])
        self.assertEqual(self.dashboards['level-up-family-children'].config['views'][0]['path'], 'player3-champion')

    async def test_missing_entity_keeps_recovery_pending_and_game_in_maintenance(self):
        prepared = await self.call(operation='prepare_add', revision=0, name='Tres')
        await self.call(operation='apply_add', token=prepared['token'])
        with self.assertLogs(self.component._LOGGER, level='ERROR'):
            await self.manager.started()
        self.assertTrue(self.manager.pending_file.exists())
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'on'))
        self.assertTrue(self.manager.error)

    async def test_unavailable_new_helper_keeps_recovery_pending(self):
        prepared = await self.call(operation='prepare_add', revision=0, name='Tres')
        await self.call(operation='apply_add', token=prepared['token'])
        self.states.async_set('input_text.champ_player3_active_week', 'unavailable')
        with self.assertLogs(self.component._LOGGER, level='ERROR'):
            await self.manager.started()
        self.assertTrue(self.manager.pending_file.exists())
        self.assertTrue(self.states.is_state('input_boolean.champ_maintenance', 'on'))


if __name__ == '__main__':
    unittest.main()
