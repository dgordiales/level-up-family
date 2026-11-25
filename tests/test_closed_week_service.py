"""Exercise service orchestration, crash recovery, and archiving before reset."""
from contextlib import closing
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch
import unittest

import test_family_service as fixtures
import test_closed_weeks as store_fixtures


class ClosedWeekServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.FamilyServiceTests.asyncSetUp(self)
        scripts = self.app/'python'
        scripts.mkdir()
        (scripts/'luf_db.py').write_bytes((fixtures.ROOT/'config/level_up_family/python/luf_db.py').read_bytes())
        with closing(store_fixtures.sqlite3.connect(self.db)) as conn,conn:
            store_fixtures.db.create_schema(conn)
        module = importlib.import_module(self.component.__name__+'.history')
        self.history = module.HistoryManager(self.manager)
        self.manager.history = self.history
        self.store = self.history.store
        self.factory = store_fixtures.ClosedWeekTests()
        self.factory.path = self.db
        self.factory.store = self.store
        self.first = self.factory.add_week('2026-11-02',store_fixtures.snapshot())
        self.second = self.factory.add_week('2026-11-09',store_fixtures.snapshot(incoming=1,daily=7))
        self.store.register(self.first,'player1',store_fixtures.snapshot())
        self.store.register(self.second,'player1',store_fixtures.snapshot(incoming=1,daily=7))
        for entity,value in {
            'input_number.luf_player1_points_total':664,
            'input_number.luf_player1_streak_days':14,
            'input_number.luf_player1_streak_weeks':2,
            'input_text.luf_player1_last_applied_week':'2026-W46',
            'input_text.luf_player1_active_week':'2026-W47',
            'input_number.luf_xp_daily_bonus':25,
            'input_number.luf_weekly_streak_multiplier':1.25,
        }.items():
            self.states.async_set(entity,value)

    async def request(self,operation,**data):
        return await self.history.handle(SimpleNamespace(data=dict(operation=operation,player_id='player1',week_id=self.first,**data)))

    async def proposal(self):
        loaded=await self.request('load')
        return await self.request('preview',revision=loaded['revision'],progress={'daily':0,'weekly':1},reason='Correct mission marks')

    async def test_preview_and_apply_sync_absolute_helpers_without_resetting_current_tasks(self):
        task_before=self.states.get('input_number.luf_player1_task_dormir_solo_week').state
        result=await self.proposal()
        self.assertEqual(self.states.get('input_number.luf_player1_points_total').state,'664.0')
        reply=await self.request('apply',token=result['token'])
        self.assertTrue(reply['ok'])
        self.assertEqual(self.states.get('input_number.luf_player1_points_total').state,'345.0')
        self.assertEqual(self.states.get('input_number.luf_player1_streak_weeks').state,'1.0')
        self.assertEqual(self.states.get('input_number.luf_player1_streak_days').state,'7.0')
        self.assertEqual(self.states.get('input_boolean.luf_maintenance').state,'off')
        self.assertEqual(self.states.get('input_number.luf_player1_task_dormir_solo_week').state,task_before)
        self.assertEqual(self.store.pending(),[])
        self.assertTrue(list((self.app/'backups').glob('*/luf.db')))

    async def test_helper_failure_keeps_maintenance_and_restart_retries_absolute_targets(self):
        plan=await self.proposal()
        restore=self.manager.restore_helpers
        self.manager.restore_helpers=AsyncMock(side_effect=RuntimeError('helper offline'))
        with self.assertRaisesRegex(RuntimeError,'helper offline'):
            await self.request('apply',token=plan['token'])
        self.assertEqual(self.states.get('input_boolean.luf_maintenance').state,'on')
        self.assertEqual(len(self.store.pending()),1)
        self.manager.restore_helpers=restore
        await self.history.recover()
        self.assertEqual(self.states.get('input_number.luf_player1_points_total').state,'345.0')
        self.assertEqual(self.store.pending(),[])
        self.assertEqual(self.states.get('input_boolean.luf_maintenance').state,'off')
        await self.history.recover()
        self.assertEqual(self.states.get('input_number.luf_player1_points_total').state,'345.0')

    async def test_current_progress_change_rejects_stale_preview(self):
        plan=await self.proposal()
        self.states.async_set('input_number.luf_player1_points_total',665)
        with self.assertRaisesRegex(RuntimeError,'progreso vivo ha cambiado'):
            await self.request('apply',token=plan['token'])
        self.assertEqual(self.store.pending(),[])
        self.assertEqual(self.states.get('input_boolean.luf_maintenance').state,'off')

    async def test_database_failure_resumes_when_rollback_is_verified(self):
        plan=await self.proposal()
        with patch.object(self.store.db_module,'rebuild_year_summary',side_effect=RuntimeError('disk failure')):
            with self.assertRaisesRegex(RuntimeError,'disk failure'):
                await self.request('apply',token=plan['token'])
        self.assertEqual(self.states.get('input_boolean.luf_maintenance').state,'off')
        self.assertEqual(self.store.pending(),[])
        self.assertEqual(self.states.get('input_number.luf_player1_points_total').state,'664.0')

    async def test_journal_recovery_keeps_newer_closed_days(self):
        plan=await self.proposal()
        restore=self.manager.restore_helpers
        self.manager.restore_helpers=AsyncMock(side_effect=RuntimeError('helper offline'))
        with self.assertRaises(RuntimeError):
            await self.request('apply',token=plan['token'])
        with closing(store_fixtures.sqlite3.connect(self.db)) as conn,conn:
            conn.execute("INSERT INTO days(player_id,day_date,year,iso_week,iso_weekday,perfect,daily_streak_end,closed_at,updated_at) VALUES(1,'2026-11-16',2026,47,1,1,8,'new','new')")
        self.manager.restore_helpers=restore
        await self.history.recover()
        self.assertEqual(self.states.get('input_number.luf_player1_streak_days').state,'8.0')

    async def test_archive_uses_stable_identity_and_retries_never_overwrite_snapshot(self):
        snap=store_fixtures.snapshot(incoming=2,daily=14)
        third=self.factory.add_week('2026-11-16',snap)
        tasks=[dict(t,player='player1',entity='input_number.archive_'+t['id']) for t in snap['tasks']]
        self.states.async_set('sensor.luf_task_catalog',len(tasks),{'tasks':tasks})
        for task in tasks:
            self.states.async_set(task['entity'],task['progress'])
        self.states.async_set('input_text.luf_player1_active_week','2026-W47')
        data=SimpleNamespace(data={'player_id':'player1','week_id':third})
        archived=await self.history.archive(data)
        self.assertTrue(archived['ok'])
        saved=deepcopy(archived['snapshot'])
        self.states.async_set('input_text.luf_player1_active_week','2026-W48')
        for task in tasks:
            self.states.async_set(task['entity'],0)
        retry=await self.history.archive(data)
        self.assertTrue(retry['unchanged'])
        self.assertEqual(self.store.load(third,'player1')['snapshot'],saved)
