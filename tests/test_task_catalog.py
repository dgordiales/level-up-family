"""Exercise the actual catalogue, scoring and mutation policy templates."""
import ast
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import random
import unittest

import jinja2
import yaml

ROOT=Path(__file__).resolve().parent.parent
CONFIG=ROOT/'config'

class TaskCatalogTests(unittest.TestCase):
    def setUp(self):
        self.defaults=json.loads((CONFIG/'level_up_family/task_defaults.json').read_text(encoding='utf-8'))['tasks']
        self.package=yaml.safe_load((CONFIG/'packages/level_up_family/lf_tasks.yaml').read_text(encoding='utf-8'))
        self.values={t['entity']:'0' for t in self.defaults}
        self.values.update({'input_datetime.champ_season_start':'2026-11-02',
                            'input_text.champ_player1_active_week':'2026-W45',
                            'input_text.champ_player2_active_week':'2026-W45'})
        self.attributes={('sensor.champ_task_defaults','tasks'):self.defaults}
        self.now=datetime(2026,11,4,12)
        self.env=jinja2.Environment(undefined=jinja2.StrictUndefined)
        def from_json(value,default=None):
            try:return json.loads(value)
            except (ValueError,TypeError):return default
        self.env.filters.update(bitwise_and=lambda a,b:int(a)&int(b),bitwise_or=lambda a,b:int(a)|int(b),
                                from_json=from_json,to_json=lambda v,**kw:json.dumps(v,**kw))
        self.env.globals.update(states=lambda e:self.values.get(e,'unknown'),
                                state_attr=lambda e,a:self.attributes.get((e,a)),
                                has_value=lambda e:self.values.get(e,'unknown') not in ('unknown','unavailable'),
                                now=lambda:self.now,timedelta=timedelta,
                                strptime=lambda v,f,default=None:self.strptime(v,f,default))
        self.refresh()

    @staticmethod
    def strptime(v,f,default):
        try:return datetime.strptime(v,f)
        except (ValueError,TypeError):return default

    def render(self,template,**variables):
        return self.env.from_string(template).render(**variables).strip()

    def refresh(self):
        sensor=self.package['template'][0]['sensor'][0]
        self.catalog=ast.literal_eval(self.render(sensor['attributes']['tasks']))
        self.attributes[('sensor.champ_task_catalog','tasks')]=self.catalog
        self.values['sensor.champ_task_catalog']=str(len(self.catalog))

    def sensor(self,player,suffix):
        data=yaml.safe_load((CONFIG/'packages/level_up_family'/('lf_'+player+'.yaml')).read_text(encoding='utf-8'))
        return next(s for b in data['template'] for s in b.get('sensor',[]) if s['unique_id']==player+'_'+suffix)

    def score(self,player,suffix):
        return int(self.render(self.sensor(player,suffix)['state']))

    def edit_steps(self):
        return next(c for step in self.package['script']['champ_task_mutate']['sequence'] for c in step.get('choose',[])
                    if c['conditions']=='{{ operation == "edit" }}')['sequence']

    def rejects(self,message,**variables):
        step=next(s for s in self.edit_steps() if any(message in t.get('stop','') for t in s.get('then',[])))
        return self.render(step['if'][0]['value_template'],**variables)=='True'

    def test_seed_schedule_and_xp_preserve_both_players(self):
        for t in self.defaults:self.values[t['entity']]='127'
        for p in ('player1','player2'):
            self.assertEqual(self.score(p,'misiones_previstas_calculadas'),60)
            self.assertEqual(self.score(p,'misiones_completadas_calculadas'),60)
            self.assertEqual(self.score(p,'xp_tareas_semana'),820)

    def test_every_seed_has_a_stable_entity_and_persistent_override(self):
        self.assertEqual(len(self.catalog),20)
        self.assertEqual(len({t['id'] for t in self.catalog}),20)
        self.assertEqual(len({t['entity'] for t in self.catalog}),20)
        for t in self.catalog:
            self.assertIn(t['config_entity'].split('.')[1],self.package['input_text'])

    def test_names_are_data_and_survive_serialization(self):
        first=self.catalog[0]
        value=dict(name='Leer "Misión" <script> & jugar 🐉',player='player1',xp=17,days=5,once=False)
        self.values[first['config_entity']]=json.dumps(value,ensure_ascii=False)
        self.refresh()
        self.assertEqual(self.catalog[0]['name'],value['name'])
        self.assertEqual(self.catalog[0]['xp'],17)
        self.assertEqual(self.catalog[0]['revision'],self.values[first['config_entity']])

    def test_reassignment_changes_only_the_target_player_totals(self):
        first=self.catalog[0]
        self.values[first['config_entity']]=json.dumps(dict(name='Leer',player='player2',xp=12,days=5,once=False))
        self.values[first['entity']]='1'
        self.refresh()
        self.assertEqual(self.score('player1','misiones_previstas_calculadas'),53)
        self.assertEqual(self.score('player2','misiones_previstas_calculadas'),62)
        self.assertEqual(self.score('player1','xp_tareas_semana'),0)
        self.assertEqual(self.score('player2','xp_tareas_semana'),12)

    def test_once_per_week_never_double_counts_weekend(self):
        task=next(t for t in self.catalog if t['player']=='player1' and t['once'])
        self.values[task['entity']]='96'
        self.assertEqual(self.score('player1','misiones_completadas_calculadas'),1)
        self.assertEqual(self.score('player1','xp_tareas_semana'),15)

    def test_unselected_days_do_not_earn_xp(self):
        task=next(t for t in self.catalog if t['days']==31)
        self.values[task['entity']]='96'
        self.assertEqual(self.score('player1','xp_tareas_semana'),0)

    def test_zero_tasks_has_no_perfect_day(self):
        for t in self.catalog:
            self.values[t['config_entity']]=json.dumps(dict(name=t['name'],player=t['player'],xp=t['xp'],days=0,once=t['once']))
        self.refresh()
        self.assertEqual(self.score('player1','misiones_previstas_calculadas'),0)
        self.assertEqual(self.score('player1','dias_perfectos_semana'),0)

    def test_perfect_days_use_scheduled_daily_tasks_and_skip_once_tasks(self):
        for t in self.defaults:
            if t['player']=='player1' and not t['once']:self.values[t['entity']]='3'
        self.assertEqual(self.score('player1','dias_perfectos_semana'),2)
        self.values[self.defaults[0]['entity']]='1'
        self.assertEqual(self.score('player1','dias_perfectos_semana'),1)

    def test_progress_blocks_rules_but_allows_name_only(self):
        task=self.catalog[0]
        self.values[task['entity']]='1'
        self.assertTrue(self.rejects('ya tiene progreso',task=task,rules_changed=True))
        self.assertFalse(self.rejects('ya tiene progreso',task=task,rules_changed=False))

    def test_missing_progress_fails_closed(self):
        task=self.catalog[0];self.values[task['entity']]='unavailable'
        self.assertTrue(self.rejects('ya tiene progreso',task=task,rules_changed=False))

    def test_stale_form_is_rejected(self):
        self.assertTrue(self.rejects('otra sesión',expected='old',revision='new'))
        self.assertFalse(self.rejects('otra sesión',expected='',revision=''))

    def test_invalid_edit_types_and_bounds_are_rejected(self):
        valid=dict(name='Leer',player='player1',xp=15,days=31,once=False)
        self.assertFalse(self.rejects('Revisa el nombre',**valid))
        for change in [dict(xp=-1),dict(xp=101),dict(xp=2.5),dict(xp=True),dict(days=-1),dict(days=128),dict(days=True),dict(player='unknown'),dict(once='false'),dict(name=' '),dict(name='a'*81)]:
            with self.subTest(change=change):self.assertTrue(self.rejects('Revisa el nombre',**(valid|change)))

    def test_weekly_reset_uses_assignment_not_the_entity_name(self):
        for p in ('player1','player2'):
            package=yaml.safe_load((CONFIG/'packages/level_up_family'/('lf_'+p+'.yaml')).read_text(encoding='utf-8'))
            steps=package['script']['champ_'+p+'_cerrar_semana']['sequence']
            expression=next(s['variables']['task_entities'] for s in steps if 'task_entities' in s.get('variables',{}))
            moved=self.catalog[0];moved['player']='player2'
            entities=ast.literal_eval(self.render(expression))
            self.assertEqual(moved['entity'] in entities,p=='player2')

    def test_toggle_and_edit_share_one_serial_queue(self):
        self.assertEqual(self.package['script']['champ_task_mutate']['mode'],'queued')
        core=yaml.safe_load((CONFIG/'packages/level_up_family/lf_core.yaml').read_text(encoding='utf-8'))
        for name in ('champ_marcar_mision','champ_desmarcar_mision'):
            self.assertEqual(core['script'][name]['sequence'][0]['action'],'script.champ_task_mutate')

    def test_date_guard_rejects_invalid_future_and_other_week(self):
        steps=next(c for step in self.package['script']['champ_task_mutate']['sequence']
                   for c in step.get('choose',[]) if 'mark' in c['conditions'])['sequence']
        date_guard=next(step['if'][0]['value_template'] for step in steps
                        if any('Solo se pueden cambiar' in s.get('stop','') for s in step.get('then',[])))
        for day,rejected in [('2026-11-03',False),('2026-11-05',True),('2026-11-01',True),('invalid',True),('2026-11-3',True)]:
            with self.subTest(day=day):
                valid=self.strptime(day,'%Y-%m-%d',None) is not None
                self.assertEqual(self.render(date_guard,fecha=day,valid_date=valid,start='2026-11-02')=='True',rejected)

    def test_once_toggle_unmarks_the_recorded_day_instead_of_creating_another(self):
        steps=next(c for step in self.package['script']['champ_task_mutate']['sequence']
                   for c in step.get('choose',[]) if 'mark' in c['conditions'])['sequence']
        expression=next(step['variables']['new_mask'] for step in steps if 'new_mask' in step.get('variables',{}))
        task=next(t for t in self.catalog if t['once'])
        self.assertEqual(int(self.render(expression,task=task,raw=32,bit=64,done=True,remove=True)),0)
        self.assertEqual(int(self.render(expression,task=task,raw=32,bit=64,done=True,remove=False)),32)

if __name__=='__main__':unittest.main()
