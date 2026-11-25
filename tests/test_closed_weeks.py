"""Corrections against disposable SQLite fixtures, including an already-corrected week."""
from contextlib import closing, redirect_stdout
from copy import deepcopy
from datetime import date, timedelta
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


db = load('closed_week_db_test', ROOT / 'config/level_up_family/python/luf_db.py')
history = load('closed_week_history_test', ROOT / 'config/custom_components/level_up_family/history_store.py')


def snapshot(progress=127, incoming=0, daily=0):
    return {'tasks': [
        {'id':'daily','name':'Daily mission','xp':10,'days':127,'once':False,'progress':progress},
        {'id':'weekly','name':'Weekly mission','xp':50,'days':127,'once':True,'progress':1}],
        'rules': {'daily_bonus':25,'weekly_multiplier':1.25,'goal_pct':75,'reward':'Family outing',
                  'weekly_streak_before':incoming,'daily_streak_before':daily,'xp_adjustment':0}}


class ClosedWeekTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'tests')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'game.db'
        self.store = history.HistoryStore(self.path, ROOT/'config/level_up_family/python/luf_db.py')
        with closing(sqlite3.connect(self.path)) as conn, conn:
            db.create_schema(conn)
            db.seed_players(conn, [{'id':'player1','name':'Player 1','active':True}, {'id':'player2','name':'Player 2','active':True}])

    def add_week(self, start, snap, effective=None, player=1, daily=None, weekly=None):
        day = date.fromisoformat(start)
        iso = day.isocalendar()
        stats = history.score(snap, snap['rules']['weekly_streak_before'])
        amount = stats['gross_effective'] if effective is None else effective
        streak = snap['rules']['daily_streak_before']
        with closing(self.store.connect()) as conn, conn:
            for i, perfect in enumerate(stats['perfect']):
                current = day + timedelta(days=i)
                streak = streak+1 if perfect else 0
                conn.execute('''INSERT INTO days(player_id,day_date,year,iso_week,iso_weekday,perfect,daily_streak_end,closed_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?)''', (player,current.isoformat(),iso.year,iso.week,i+1,perfect,streak,'old','old'))
            columns = ['player_id','year','iso_week','week_start','week_end','tasks_due','tasks_completed','task_xp',
                       'perfect_days','bonus_xp','effective_xp','daily_streak_end','weekly_streak_end','weekly_goal_achieved','season_number','closed_at']
            values = [player,iso.year,iso.week,start,(day+timedelta(days=6)).isoformat(),
                      *[stats[k] for k in ['tasks_due','tasks_completed','task_xp','perfect_days','bonus_xp']],amount,
                      streak if daily is None else daily,snap['rules']['weekly_streak_before']+1 if weekly is None else weekly,
                      int(stats['budget']>0 and amount*100>=stats['budget']*snap['rules']['goal_pct']),1,'old']
            cursor = conn.execute('INSERT INTO weeks('+','.join(columns)+') VALUES('+','.join('?' for _ in values)+')',values)
            db.rebuild_year_summary(conn,player,iso.year)
            return cursor.lastrowid

    def rows(self, table):
        with closing(self.store.connect()) as conn:
            return [dict(r) for r in conn.execute('SELECT * FROM '+table+' ORDER BY id')]

    def setup_chain(self):
        a,b=snapshot(),snapshot(incoming=1,daily=7)
        first=self.add_week('2026-11-02',a)
        second=self.add_week('2026-11-09',b)
        self.store.register(first,'player1',a)
        self.store.register(second,'player1',b)
        with closing(self.store.connect()) as conn,conn:
            conn.execute("INSERT INTO days(player_id,day_date,year,iso_week,iso_weekday,perfect,daily_streak_end,closed_at,updated_at) VALUES(1,'2026-11-16',2026,47,1,1,15,'old','old')")
        runtime={'points_total':664,'last_applied_week':'2026-W46','streak_days':15,'streak_weeks':2}
        return first,second,runtime

    def test_preview_rolls_back_and_recalculates_chain_and_live_days(self):
        first,second,runtime=self.setup_chain()
        old={t:self.rows(t) for t in ['weeks','years','days','week_history']}
        result=self.store.preview(first,'player1',self.store.load(first,'player1')['revision'],{'daily':0,'weekly':1},runtime)
        self.assertEqual(result['helpers'],{'points_total':345,'streak_weeks':1,'streak_days':8})
        self.assertEqual(result['xp_delta'],-319)
        self.assertEqual([c['after']['effective_xp'] for c in result['changes']],[50,295])
        self.assertEqual([c['multiplier'] for c in result['changes']],[1,1])
        self.assertEqual([c['reward_earned'] for c in result['changes']],[False,True])
        self.assertEqual(result['changes'][-1]['after']['level_end'],1)
        self.assertEqual({t:self.rows(t) for t in old},old)

    def test_apply_is_atomic_has_audit_pending_absolute_helpers_and_no_duplicate_reward(self):
        first,second,runtime=self.setup_chain()
        rev=self.store.load(first,'player1')['revision']
        result=self.store.apply(first,'player1',rev,{'daily':0,'weekly':1},runtime,'Correct forgotten marks',{'prefix':'stable_alias','was_maintenance':False})
        self.assertEqual(self.rows('years')[0]['effective_xp'],345)
        self.assertEqual(self.store.pending()[0]['data']['values'],result['helpers'])
        self.assertEqual(self.store.pending()[0]['data']['prefix'],'stable_alias')
        audit=self.store.load(first,'player1')['audit']
        self.assertEqual(audit[-1]['reason'],'Correct forgotten marks')
        self.assertEqual(audit[-1]['before']['tasks'][0]['progress'],127)
        self.assertEqual(audit[-1]['after']['tasks'][0]['progress'],0)
        with self.assertRaisesRegex(ValueError,'ha cambiado'):
            self.store.apply(first,'player1',rev,{'daily':0,'weekly':1},runtime,'Retry request',{'prefix':'stable_alias'})
        self.assertEqual(len(self.store.load(first,'player1')['audit']),2)
        self.store.acknowledge(self.store.pending()[0]['id'])
        runtime.update(points_total=345,streak_days=8,streak_weeks=1)
        latest=self.store.load(first,'player1')
        no_op=self.store.apply(first,'player1',latest['revision'],{'daily':0,'weekly':1},runtime,'Retry unchanged',{})
        self.assertTrue(no_op['unchanged'])
        self.assertEqual(self.store.pending(),[])
        self.assertEqual(len(self.store.load(first,'player1')['audit']),2)

    def test_failure_rolls_back_all_days_weeks_years_and_audit(self):
        first,_,runtime=self.setup_chain()
        old={t:self.rows(t) for t in ['weeks','years','days','week_history','history_sync']}
        with patch.object(self.store.db_module,'rebuild_year_summary',side_effect=RuntimeError('disk failure')):
            with self.assertRaisesRegex(RuntimeError,'disk failure'):
                self.store.apply(first,'player1',self.store.load(first,'player1')['revision'],{'daily':0,'weekly':1},runtime,'Correct tasks',{})
        self.assertEqual({t:self.rows(t) for t in old},old)

    def test_unknown_tasks_invalid_bits_and_wrong_player_are_rejected(self):
        first,_,runtime=self.setup_chain()
        rev=self.store.load(first,'player1')['revision']
        for progress in [{'daily':128,'weekly':1},{'daily':True,'weekly':1},{'daily':0,'weekly':1,'other':0}]:
            with self.assertRaises(ValueError):
                self.store.preview(first,'player1',rev,progress,runtime)
        with self.assertRaisesRegex(ValueError,'ese hijo'):
            self.store.load(first,'player2')

    def test_legacy_baseline_must_match_and_does_not_reapply_manually_corrected_week(self):
        weights=[10,10,10,10,15,15,20,20]
        masks=[113|14,113,113,113,113|6,113,113|14,113|6]
        tasks=[{'id':str(i),'name':f'Task {i}','xp':xp,'days':127,'once':False,'progress':masks[i]} for i,xp in enumerate(weights)]
        tasks.append({'id':'8','name':'School','xp':15,'days':15,'once':False,'progress':1})
        snap={'tasks':tasks,'rules':dict(snapshot()['rules'],goal_pct=60,weekly_streak_before=2)}
        stats=history.score(snap,2)
        self.assertEqual([stats[k] for k in ['tasks_completed','tasks_due','task_xp','perfect_days']],[43,60,615,4])
        week=self.add_week('2026-11-16',snap,effective=873,daily=3,weekly=3)
        with closing(self.store.connect()) as conn,conn:
            conn.execute('UPDATE weeks SET penalty_xp=20,level_start=3,level_end=4 WHERE id=?',(week,))
            db.rebuild_year_summary(conn,1,2026)
        before=self.rows('weeks'),self.rows('years'),self.rows('days')
        bad=deepcopy(snap);bad['tasks'][0]['progress']=0
        with self.assertRaisesRegex(ValueError,'no coincide'):
            self.store.register(week,'player1',bad)
        registered=self.store.register(week,'player1',snap)
        self.assertEqual(registered['snapshot']['rules']['xp_adjustment'],-1)
        self.assertEqual((self.rows('weeks'),self.rows('years'),self.rows('days')),before)
        runtime={'points_total':873,'last_applied_week':'2026-W47','streak_days':3,'streak_weeks':3}
        progress={t['id']:t['progress'] for t in tasks}
        result=self.store.apply(week,'player1',registered['revision'],progress,runtime,'Already corrected',{})
        self.assertTrue(result['unchanged'])
        self.assertEqual((self.rows('weeks'),self.rows('years'),self.rows('days')),before)
        self.assertEqual(self.store.pending(),[])

    def test_snapshots_keep_original_rules_and_weekly_tasks_count_once(self):
        snap=snapshot();snap['tasks'][1]['progress']=127
        stats=history.score(snap,0)
        self.assertEqual((stats['tasks_due'],stats['tasks_completed'],stats['task_xp'],stats['perfect_days']),(8,8,120,7))
        history.validate_snapshot(snap)

    def test_unarchived_successor_needs_evidence_before_multiplier_changes(self):
        first=self.add_week('2026-11-02',snapshot())
        second=self.add_week('2026-11-09',snapshot(incoming=1,daily=7))
        self.store.register(first,'player1',snapshot())
        runtime={'points_total':664,'last_applied_week':'2026-W46','streak_days':14,'streak_weeks':2}
        with self.assertRaisesRegex(ValueError,'2026-W46'):
            self.store.preview(first,'player1',self.store.load(first,'player1')['revision'],{'daily':0,'weekly':1},runtime)

    def test_other_players_are_unchanged_and_year_boundary_propagates(self):
        first_snap=snapshot();second_snap=snapshot(incoming=1,daily=7)
        first=self.add_week('2025-12-22',first_snap)
        second=self.add_week('2025-12-29',second_snap)
        self.add_week('2025-12-22',first_snap,player=2)
        self.store.register(first,'player1',first_snap)
        self.store.register(second,'player1',second_snap)
        other=[w for w in self.rows('weeks') if w['player_id']==2]
        runtime={'points_total':664,'last_applied_week':'2026-W01','streak_days':14,'streak_weeks':2}
        self.store.apply(first,'player1',self.store.load(first,'player1')['revision'],{'daily':0,'weekly':1},runtime,'Correct previous year',{'prefix':'player1'})
        self.assertEqual([w for w in self.rows('weeks') if w['player_id']==2],other)
        self.assertEqual([y['effective_xp'] for y in self.rows('years') if y['player_id']==1],[50,295])

    def test_offline_reset_includes_archives_and_pending_sync_in_verified_backup(self):
        first,_,runtime=self.setup_chain()
        self.store.apply(first,'player1',self.store.load(first,'player1')['revision'],{'daily':0,'weekly':1},runtime,'Correct tasks',{'prefix':'player1'})
        reset=load('closed_week_reset_test', ROOT/'config/level_up_family/python/prepare_reset.py')
        plan=reset.prepare_reset(self.path,'2026-11-02')
        self.assertEqual(plan['delete_counts']['week_history'],2)
        self.assertEqual(plan['delete_counts']['history_sync'],1)
        result=reset.prepare_reset(self.path,'2026-11-02',apply=True,backup_directory=Path(self.temp.name)/'backups')
        self.assertEqual(self.rows('weeks'),[])
        self.assertEqual(self.rows('week_history'),[])
        self.assertEqual(self.rows('history_sync'),[])
        with closing(sqlite3.connect(result['backup'])) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM week_history').fetchone()[0],2)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM history_sync').fetchone()[0],1)


if __name__ == '__main__':
    unittest.main()
