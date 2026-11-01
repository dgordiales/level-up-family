"""Calendar boundary regression checks; no Home Assistant or live data access."""
from datetime import datetime, timedelta
from pathlib import Path
import unittest

import jinja2
import yaml

PACKAGE = Path(__file__).parent.parent / 'config/packages/level_up_family/lf_season.yaml'


class SeasonTimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sensors = {
            sensor['unique_id']: sensor
            for block in yaml.safe_load(PACKAGE.read_text(encoding='utf-8'))['template']
            for sensor in block['sensor']
        }

    def render(self, sensor, key, today, start='2026-11-02'):
        def strptime(value, fmt, default=None):
            try:
                return datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                return default
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.globals.update(states=lambda entity: start,
                           now=lambda: datetime.fromisoformat(today),
                           strptime=strptime, timedelta=timedelta)
        return env.from_string(self.sensors[sensor][key]).render().strip()

    def check_date(self, today, day, remaining, status):
        self.assertEqual(self.render('champ_season_day', 'state', today), str(day))
        self.assertEqual(self.render('champ_season_days_remaining', 'state', today), str(remaining))
        self.assertEqual(self.render('champ_season_status', 'state', today), status)
        self.assertEqual(self.render('champ_season_end', 'state', today), '2026-11-29')
        for sensor in self.sensors:
            self.assertEqual(self.render(sensor, 'availability', today), 'True')

    def test_day_before_launch(self):
        self.check_date('2026-11-01T23:59:59', 0, 28, 'pendiente')

    def test_launch_day(self):
        self.check_date('2026-11-02T00:00:00', 1, 28, 'activa')

    def test_last_day_stays_active_until_midnight(self):
        self.check_date('2026-11-29T23:59:59', 28, 1, 'activa')

    def test_first_completed_day(self):
        self.check_date('2026-11-30T00:00:00', 28, 0, 'finalizada')

    def test_far_before_and_after_are_clamped(self):
        self.check_date('2026-01-01T12:00:00', 0, 28, 'pendiente')
        self.check_date('2027-01-01T12:00:00', 28, 0, 'finalizada')

    def test_invalid_start_not_available_and_state_safe(self):
        for start in ('', 'unknown', 'unavailable', '2026-02-30', 'oops'):
            for sensor in self.sensors:
                with self.subTest(start=start, sensor=sensor):
                    self.assertEqual(self.render(sensor, 'availability', '2026-11-02', start), 'False')
                    self.assertEqual(self.render(sensor, 'state', '2026-11-02', start), 'None')

    def test_calendar_crosses_year(self):
        self.assertEqual(self.render('champ_season_end', 'state', '2026-12-20', '2026-12-20'), '2027-01-16')
        self.assertEqual(self.render('champ_season_status', 'state', '2027-01-17', '2026-12-20'), 'finalizada')

    def test_entity_ids_are_explicit(self):
        for key, sensor in self.sensors.items():
            self.assertEqual(sensor['default_entity_id'], 'sensor.' + key)


if __name__ == '__main__':
    unittest.main(verbosity=2)
