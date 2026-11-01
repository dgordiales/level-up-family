"""Checks for the standalone, generic player distribution."""
from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent
PANELS = ROOT / 'config/panel/level_up_family'
PACKAGES = ROOT / 'config/packages/level_up_family'


class DistributionTests(unittest.TestCase):
    def test_player_panels_only_contain_their_game_view(self):
        for player, other in [('player1', 'player2'), ('player2', 'player1')]:
            with self.subTest(player=player):
                path = PANELS / (player + '.yaml')
                text = path.read_text(encoding='utf-8')
                panel = yaml.safe_load(text)
                self.assertEqual([v['path'] for v in panel['views']], [player + '-champion'])
                self.assertNotIn('champ_' + other, text)
                self.assertIn('script.champ_' + player + '_toggle_mision', text)

    def test_parents_panel_contains_control_and_history_only(self):
        data = yaml.safe_load((PANELS / 'parents.yaml').read_text(encoding='utf-8'))
        self.assertEqual([v['path'] for v in data['views']],
                         ['control-champion', 'historico-champion'])

    def test_no_household_devices_or_notification_destinations_in_panels(self):
        for path in PANELS.glob('*.yaml'):
            text = path.read_text(encoding='utf-8')
            self.assertIsNone(re.search(
                r'\b(?:notify|person|calendar|weather|camera|media_player|light|cover)\.[a-z0-9_]+', text), path.name)

    def test_all_referenced_graphics_exist(self):
        names = set()
        for path in PANELS.glob('*.yaml'):
            names.update(re.findall(r'([a-z_]+\.png)', path.read_text(encoding='utf-8')))
        self.assertGreaterEqual(len(names), 10)
        for name in names:
            path = ROOT / 'config/www/level_up_family/season_01' / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.read_bytes()[:8], b'\x89PNG\r\n\x1a\n', name)

    def test_weekly_automation_targets_match_the_players(self):
        data = yaml.safe_load((PACKAGES / 'lf_weekly.yaml').read_text(encoding='utf-8'))['automation']
        self.assertEqual(len(data), 4)
        self.assertEqual(len({a['id'] for a in data}), 4)
        for player in ('player1', 'player2'):
            close = next(a for a in data if a['id'] == 'champ_' + player + '_weekly_close')
            self.assertEqual(close['actions'], [{'action': 'script.champ_' + player + '_cerrar_semana'}])


if __name__ == '__main__':
    unittest.main()
