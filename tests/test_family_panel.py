"""Runtime identities, soft retirement, provisioning and privacy-safe templates."""
from copy import deepcopy
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / 'config/custom_components/level_up_family'
spec = importlib.util.spec_from_file_location('family_model_test', COMPONENT / 'model.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
sys.path.insert(0, str(ROOT / 'tools'))
from build_family_templates import build


class FamilyPanelTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((ROOT / 'config/level_up_family/family.json').read_text(encoding='utf-8'))
        self.templates = build()
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)

    def test_checked_in_templates_match_the_source_configuration(self):
        self.assertEqual(json.loads((COMPONENT / 'templates.json').read_text(encoding='utf-8')), self.templates)

    def test_rename_preserves_all_bindings_and_handles_literal_names(self):
        after = model.change(self.registry, 'rename', 0, 'player1', 'Mía O\'Neil & "Sol" < > {{x}}')
        before = self.registry['players'][0]
        self.assertEqual({k: v for k, v in after['players'][0].items() if k != 'name'},
                         {k: v for k, v in before.items() if k != 'name'})
        view = model.child_view(self.templates, after['players'][0])
        panel = view['sections'][0]['cards'][1]['custom_fields']['content']
        self.assertNotIn('{{x}}', panel)
        self.assertIn('&#123;', panel)
        self.assertEqual(self.registry['revision'], 0)

    def test_add_never_reuses_retired_identifiers(self):
        retired = model.change(self.registry, 'retire', 0, 'player2')
        added = model.change(retired, 'add', 1, name='Tres')
        self.assertEqual(added['players'][-1]['id'], 'player3')
        self.assertFalse(added['players'][1]['active'])
        self.assertEqual(added['revision'], 2)

    def test_last_active_child_cannot_be_retired(self):
        after = model.change(self.registry, 'retire', 0, 'player1')
        with self.assertRaises(ValueError):
            model.change(after, 'retire', 1, 'player2')

    def test_stale_revision_and_invalid_names_are_rejected(self):
        for revision in [-1, 1, True, '0']:
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                model.change(self.registry, 'rename', revision, 'player1', 'A')
        for name in ['', ' ', 'a' * 41, 'A\nB']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                model.change(self.registry, 'add', 0, name=name)

    def test_duplicate_aliases_and_path_traversal_are_rejected(self):
        for field, value in [('entity_prefix', 'player1'), ('db_key', 'player1'),
                             ('dashboard_path', '../private'), ('id', 'player01')]:
            data = deepcopy(self.registry)
            data['players'][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                model.validate(data)

    def test_migration_bindings_keep_real_database_keys(self):
        data = deepcopy(self.registry)
        data['players'][0].update(entity_prefix='legacy_one', db_key='player_1',
                                  dashboard_url='dashboard-one', dashboard_path='one-game')
        view = model.child_view(self.templates, data['players'][0])
        text = json.dumps(view)
        self.assertIn('luf_legacy_one_', text)
        self.assertIn('sensor.legacy_one_', text)
        self.assertEqual(view['path'], 'one-game')
        views = model.parents_views(self.templates, data)
        fine_keys = {n['player_key'] for n in model.walk(views) if 'player_key' in n}
        self.assertEqual(fine_keys, {'player_1', 'player2'})
        self.assertIn("x.player_key === 'player_1'", json.dumps(views))

    def test_retirement_preserves_every_activity_row_and_numeric_player_identity(self):
        path = Path(self.temp.name) / 'game.db'
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.executescript('''CREATE TABLE players(id INTEGER PRIMARY KEY AUTOINCREMENT,
              player_key TEXT UNIQUE,display_name TEXT,active INTEGER,created_at TEXT);
              CREATE TABLE activity(player_id INTEGER, value TEXT);
              INSERT INTO players VALUES(7,'player1','Original',1,'original-date');
              INSERT INTO players VALUES(8,'player2','Dos',1,'original-date');
              INSERT INTO activity VALUES(7,'45 XP, 4 tareas, semana 45');''')
        after = model.change(self.registry, 'rename', 0, 'player1', 'Nombre nuevo')
        after = model.change(after, 'retire', 1, 'player1')
        model.sync_db(path, after)
        with closing(sqlite3.connect(path)) as conn, conn:
            self.assertEqual(conn.execute('SELECT * FROM activity').fetchall(), [(7, '45 XP, 4 tareas, semana 45')])
            self.assertEqual(conn.execute('SELECT * FROM players WHERE id=7').fetchone(),
                             (7, 'player1', 'Nombre nuevo', 0, 'original-date'))

    def test_sync_refuses_unbound_database_players_without_partial_writes(self):
        path = Path(self.temp.name) / 'game.db'
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute('CREATE TABLE players(player_key TEXT,display_name TEXT,active INTEGER,created_at TEXT)')
            conn.execute("INSERT INTO players VALUES('unbound','Keep',1,'date')")
        with self.assertRaises(ValueError):
            model.sync_db(path, self.registry)
        with closing(sqlite3.connect(path)) as conn, conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM players').fetchone()[0], 1)

    def test_new_child_gets_separate_unscheduled_tasks_and_no_existing_state_changes(self):
        registry = model.change(self.registry, 'add', 0, name='Tres')
        defaults, weekly = self.templates['defaults'], self.templates['weekly']
        before = deepcopy((defaults, weekly))
        package, after, automations = model.new_player_files(self.templates, registry['players'][-1], defaults, weekly)
        self.assertEqual((defaults, weekly), before)
        self.assertEqual(after['tasks'][:20], defaults['tasks'])
        self.assertEqual([t['id'] for t in after['tasks'][20:]], [f'task{i}' for i in range(21, 31)])
        self.assertTrue(all(t['player'] == 'player3' and t['days'] == 0 for t in after['tasks'][20:]))
        self.assertTrue(all(t['entity'].split('.')[1] in package['input_number'] for t in after['tasks'][20:]))
        self.assertEqual(automations['automation'][:4], weekly['automation'])
        self.assertEqual(len(automations['automation']), 6)

    def test_new_child_refuses_colliding_task_slots(self):
        registry = model.change(self.registry, 'add', 0, name='Tres')
        defaults = deepcopy(self.templates['defaults'])
        defaults['tasks'].append(dict(defaults['tasks'][0], id='task21'))
        with self.assertRaises(ValueError):
            model.new_player_files(self.templates, registry['players'][-1], defaults, self.templates['weekly'])

    def test_dashboard_update_preserves_unrelated_views_and_settings(self):
        original = {'title': 'Casa', 'background': 'keep', 'views': [
            {'path': 'home', 'cards': [{'type': 'light', 'entity': 'light.private'}]},
            {'path': 'player1-luf', 'title': 'old'}]}
        before = deepcopy(original)
        merged = model.merge_views(original, [model.child_view(self.templates, self.registry['players'][0])])
        self.assertEqual(original, before)
        self.assertEqual(merged['views'][0], original['views'][0])
        self.assertEqual(merged['title'], 'Casa')
        self.assertEqual(merged['background'], 'keep')
        self.assertEqual(len(merged['views']), 2)

    def test_retired_panel_has_no_mission_controls_but_keeps_history_section(self):
        retired = model.change(self.registry, 'retire', 0, 'player2')
        panel = model.child_view(self.templates, retired['players'][1])
        self.assertNotIn('custom:level-up-family-missions', json.dumps(panel))
        views = model.parents_views(self.templates, retired)
        self.assertEqual(views[2]['sections'][0]['cards'][0]['players'], {'player1': 'player1'})
        self.assertIn('player2 (retirado)', json.dumps(views[1]))
        self.assertTrue(any(n.get('type') == 'custom:level-up-family-roster' for n in model.walk(views)))


if __name__ == '__main__':
    unittest.main()
