"""Exercise generated families and retirement against isolated HA files and SQLite."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from configure_family import generate
from validate_config import validate
import test_task_catalog as catalog_checks


def module_at(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture(function, *args, **kwargs):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        function(*args, **kwargs)
    return output.getvalue()


class FamilyConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='family-test-', dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)

    def make(self, players, suffix='family'):
        family = self.temp / (suffix + '.json')
        family.write_text(json.dumps({'version': 1, 'players': players}), encoding='utf-8')
        output = self.temp / suffix
        generate(family, output)
        return output / 'config'

    def fixture(self, config):
        self.enterContext(patch.object(catalog_checks, 'CONFIG', config))
        fixture = catalog_checks.TaskCatalogTests()
        fixture.setUp()
        return fixture

    def test_one_three_and_nonconsecutive_ids_have_complete_references(self):
        for keys in [('player1',), ('player1', 'player2', 'player3'), ('player3', 'player10')]:
            with self.subTest(keys=keys):
                cfg = self.make([{'id': key, 'name': 'Nombre ' + key} for key in keys], '_'.join(keys))
                report = validate(cfg)
                self.assertTrue(report['ok'], report['errors'])
                subprocess.run([sys.executable, str(ROOT / 'tools/validate_panels_js.py'),
                                str(cfg / 'panel/level_up_family')], check=True, capture_output=True)
                defaults = json.loads((cfg / 'level_up_family/task_defaults.json').read_text(encoding='utf-8'))['tasks']
                self.assertEqual(len(defaults), 10 * len(keys))
                self.assertEqual(len({t['id'] for t in defaults}), len(defaults))
                parents = yaml.safe_load((cfg / 'panel/level_up_family/parents.yaml').read_text(encoding='utf-8'))
                admin = parents['views'][2]['sections'][0]['cards'][0]
                self.assertEqual(set(admin['players']), set(keys))
                self.assertEqual(set(admin['rewards']), set(keys))
                week = yaml.safe_load((cfg / 'packages/level_up_family/lf_weekly.yaml').read_text(encoding='utf-8'))['automation']
                self.assertEqual(len(week), 2 * len(keys))
                self.assertEqual(len({a['id'] for a in week}), len(week))

    def test_third_player_scores_and_mutation_policy_are_not_limited_to_two(self):
        cfg = self.make([{'id': f'player{i}', 'name': str(i)} for i in range(1, 4)])
        fixture = self.fixture(cfg)
        fixture.values['input_text.champ_player3_active_week'] = '2026-W45'
        for task in fixture.defaults:
            fixture.values[task['entity']] = '127'
        fixture.refresh()
        self.assertEqual(fixture.score('player3', 'xp_tareas_semana'), 820)
        self.assertEqual(fixture.score('player3', 'misiones_completadas_calculadas'), 60)
        self.assertFalse(fixture.rejects('Revisa el nombre', name='Leer', player='player3', xp=20, days=31, once=False))
        self.assertTrue(fixture.rejects('Revisa el nombre', name='Leer', player='player4', xp=20, days=31, once=False))
        guard = fixture.edit_steps()[0]['if'][0]['value_template']
        fixture.values['input_text.champ_player3_active_week'] = '2026-W44'
        self.assertEqual(fixture.render(guard, task=fixture.catalog[0]), 'True')
        fixture.values['input_text.champ_player3_active_week'] = '2026-W45'
        self.assertEqual(fixture.render(guard, task=fixture.catalog[0]), 'False')
        recheck = fixture.edit_steps()[-1]['then'][0]['repeat']['sequence']
        self.assertEqual(recheck[1]['repeat']['sequence'][0]['action'], '{{ repeat.item }}')
        targets = fixture.render(recheck[1]['repeat']['for_each'])
        self.assertEqual(__import__('ast').literal_eval(targets),
                         [f'script.champ_player{i}_cerrar_dia' for i in range(1, 4)])

    def test_retired_player_keeps_helpers_but_not_buttons_closures_or_week_guards(self):
        cfg = self.make([{'id': 'player1', 'name': 'Uno'}, {'id': 'player2', 'name': 'Dos', 'active': False},
                         {'id': 'player3', 'name': 'Tres'}])
        fixture = self.fixture(cfg)
        fixture.values['input_text.champ_player2_active_week'] = '2025-W01'
        fixture.values['input_text.champ_player3_active_week'] = '2026-W45'
        fixture.refresh()
        self.assertEqual({t['player'] for t in fixture.catalog}, {'player1', 'player3'})
        guard = fixture.edit_steps()[0]['if'][0]['value_template']
        self.assertEqual(fixture.render(guard, task=fixture.catalog[0]), 'False')
        retired = yaml.safe_load((cfg / 'packages/level_up_family/lf_player2.yaml').read_text(encoding='utf-8'))
        self.assertTrue(retired['input_number'])
        self.assertEqual(retired['automation'], [])
        self.assertEqual(retired['script']['champ_player2_cerrar_semana']['sequence'][0]['value_template'], '{{ false }}')
        panel = (cfg / 'panel/level_up_family/player2.yaml').read_text(encoding='utf-8')
        self.assertNotIn('custom:level-up-family-missions', panel)
        parents = yaml.safe_load((cfg / 'panel/level_up_family/parents.yaml').read_text(encoding='utf-8'))
        self.assertNotIn('player2', parents['views'][2]['sections'][0]['cards'][0]['players'])
        self.assertTrue(any(s['cards'][0].get('heading') == 'Dos (retirado)' for s in parents['views'][1]['sections']))

    def test_renaming_and_reordering_keep_entity_and_task_ids(self):
        a = self.make([{'id': 'player1', 'name': 'Luna'}, {'id': 'player3', 'name': 'Leo'}], 'a')
        b = self.make([{'id': 'player3', 'name': 'Mía O\'Neil & "Sol"'}, {'id': 'player1', 'name': 'Otro nombre'}], 'b')
        def tasks(cfg):
            data = json.loads((cfg / 'level_up_family/task_defaults.json').read_text(encoding='utf-8'))['tasks']
            return {t['id']: (t['entity'], t['player']) for t in data}
        self.assertEqual(tasks(a), tasks(b))
        package = yaml.safe_load((b / 'packages/level_up_family/lf_player3.yaml').read_text(encoding='utf-8'))
        for block in package['template']:
            for domain in ('sensor', 'binary_sensor'):
                for sensor in block.get(domain, []):
                    self.assertEqual(sensor['default_entity_id'], domain + '.' + sensor['unique_id'])
        subprocess.run([sys.executable, str(ROOT / 'tools/validate_panels_js.py'),
                        str(b / 'panel/level_up_family')], check=True, capture_output=True)

    def test_invalid_configuration_is_rejected_before_generating(self):
        invalid = [[], [{'id': 'player1', 'name': 'A', 'active': False}],
                   [{'id': 'player1', 'name': 'A'}, {'id': 'player1', 'name': 'B'}],
                   [{'id': '../player1', 'name': 'A'}], [{'id': 'player1', 'name': ''}],
                   [{'id': 'player1', 'name': 'A', 'active': 'false'}],
                   [{'id': 'player01', 'name': 'A'}], [{'id': 'player1', 'name': 'A', 'activ': False}]]
        for i, players in enumerate(invalid):
            with self.subTest(players=players), self.assertRaises(ValueError):
                self.make(players, f'invalid{i}')
            self.assertFalse((self.temp / f'invalid{i}').exists())

    def test_generator_refuses_existing_output_and_never_copies_databases(self):
        cfg = self.make([{'id': 'player1', 'name': 'Uno'}])
        before = (cfg / 'level_up_family/family.json').read_bytes()
        with self.assertRaises(ValueError):
            generate(self.temp / 'family.json', cfg.parent)
        self.assertEqual((cfg / 'level_up_family/family.json').read_bytes(), before)
        self.assertFalse(list(cfg.rglob('*.db')))

    def test_database_sync_retains_ids_activity_and_retired_history(self):
        cfg = self.make([{'id': 'player1', 'name': 'Uno'}, {'id': 'player2', 'name': 'Dos'}, {'id': 'player3', 'name': 'Tres'}])
        code = cfg / 'level_up_family/python'
        db = module_at(code / 'champion_db.py', 'family_database_test')
        db.BASE_DIR = self.temp / 'data'
        db.DB_PATH = db.BASE_DIR / 'champion.db'
        capture(db.init_database)
        capture(db.add_penalty, 'player2', 10, 'Prueba')
        capture(db.close_day, 'player2', '2026-11-02', 1)
        capture(db.close_week, 'player2', 2026, 45, '2026-11-02', '2026-11-08', 1,
                60, 50, 500, 3, 75, 10, 565, 1, 2, 1, 1, 1)
        def rows(table):
            with contextlib.closing(sqlite3.connect(db.DB_PATH)) as conn:
                return conn.execute('SELECT * FROM ' + table + ' ORDER BY id').fetchall()
        activity = {t: rows(t) for t in ('days', 'weeks', 'years', 'penalties')}
        ids = [r[0] for r in rows('players')]
        manifest = cfg / 'level_up_family/family.json'
        family = json.loads(manifest.read_text(encoding='utf-8'))
        family['players'][1].update(name='Nombre nuevo', active=False)
        manifest.write_text(json.dumps(family), encoding='utf-8')
        capture(db.sync_family)
        capture(db.init_database)
        self.assertEqual([r[0] for r in rows('players')], ids)
        self.assertEqual(rows('players')[1][2:4], ('Nombre nuevo', 0))
        self.assertEqual({t: rows(t) for t in activity}, activity)
        history = module_at(code / 'champion_history.py', 'family_history_test')
        history.DB_PATH = db.DB_PATH
        record = json.loads(capture(history.main))
        self.assertEqual(record['weeks'][0]['player_name'], 'Nombre nuevo')
        self.assertEqual(record['weeks'][0]['player_active'], 0)
        with self.assertRaises(SystemExit):
            capture(db.add_penalty, 'player2', 10, 'No permitido')
        family['players'][1]['active'] = True
        manifest.write_text(json.dumps(family), encoding='utf-8')
        capture(db.sync_family)
        self.assertEqual({t: rows(t) for t in activity}, activity)
        self.assertEqual(rows('players')[1][3], 1)

    def test_legacy_init_without_manifest_keeps_existing_names_and_players(self):
        db = module_at(ROOT / 'config/level_up_family/python/champion_db.py', 'legacy_family_test')
        db.BASE_DIR = self.temp / 'data'
        db.DB_PATH = db.BASE_DIR / 'champion.db'
        db.FAMILY_PATH = self.temp / 'missing.json'
        capture(db.init_database)
        with db.connect() as conn:
            conn.execute("UPDATE players SET display_name='Nombre anterior' WHERE player_key='player1'")
            conn.execute("INSERT INTO players(player_key,display_name,active,created_at) VALUES ('player3','Tres',1,'2026-01-01')")
        capture(db.init_database)
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT display_name FROM players WHERE player_key='player1'").fetchone()[0], 'Nombre anterior')
            self.assertEqual(conn.execute("SELECT active FROM players WHERE player_key='player3'").fetchone()[0], 1)
        with self.assertRaises(ValueError):
            capture(db.sync_family)


if __name__ == '__main__':
    unittest.main()
