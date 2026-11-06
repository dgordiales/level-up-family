"""Per-child persistence and the actual XP templates, including weekly settlement."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

import test_task_catalog as catalog

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('goal_model', ROOT/'config/custom_components/level_up_family/model.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class GoalSettingsTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((ROOT/'config/level_up_family/family.json').read_text(encoding='utf-8'))

    def test_different_goals_survive_serialization_and_other_family_changes(self):
        first=model.goal_change(self.registry,'player1',60,0)
        second=model.goal_change(first,'player2',85,1)
        reloaded=model.validate(json.loads(json.dumps(second)))
        renamed=model.change(reloaded,'rename',2,'player1','Nombre nuevo')
        self.assertEqual([p['weekly_goal_pct'] for p in renamed['players']],[60,85])
        self.assertEqual([p['weekly_goal_pct'] for p in self.registry['players']],[75,75])
        added=model.change(renamed,'add',3,name='Tres')
        self.assertEqual(added['players'][-1]['weekly_goal_pct'],75)

    def test_legacy_registry_gets_default_without_mutating_input(self):
        for p in self.registry['players']:p.pop('weekly_goal_pct',None)
        validated=model.validate(self.registry)
        self.assertEqual(validated['players'][0]['weekly_goal_pct'],75)
        self.assertNotIn('weekly_goal_pct',self.registry['players'][0])

    def test_invalid_stale_or_retired_goal_never_modifies_registry(self):
        before=deepcopy(self.registry)
        for value in [-1,101,True,60.5,'70',None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.goal_change(self.registry,'player1',value,0)
        with self.assertRaisesRegex(ValueError,'otra sesión'):model.goal_change(self.registry,'player1',70,8)
        self.registry['players'][0]['active']=False
        with self.assertRaises(ValueError):model.goal_change(self.registry,'player1',70,0)
        self.registry['players'][0]['active']=True
        self.assertEqual(self.registry,before)


class XPGoalTests(catalog.TaskCatalogTests):
    # Reuse the actual catalogue renderer, without rerunning its unrelated tests here.
    def refresh_scores(self,player='player1'):
        for suffix in ['misiones_previstas_calculadas','misiones_completadas_calculadas','xp_tareas_semana',
                       'dias_perfectos_semana','xp_bonus_semana','xp_semana_bruto','xp_previsto_semana',
                       'multiplicador_racha_semanal','xp_semana_efectivo']:
            self.values[f'sensor.{player}_{suffix}']=self.render(self.sensor(player,suffix)['state'])
        package=__import__('yaml').safe_load((ROOT/f'config/packages/level_up_family/lf_{player}.yaml').read_text(encoding='utf-8'))
        return package['template'][1]['binary_sensor'][0]

    def configure(self):
        self.values.update({'input_number.luf_xp_daily_bonus':'25','input_number.luf_weekly_streak_multiplier':'1.25',
                            'input_number.luf_player1_streak_weeks':'0','input_number.luf_player2_streak_weeks':'0',
                            'input_number.luf_player1_penalties_this_week':'0','input_number.luf_player2_penalties_this_week':'0'})
        for p in self.attributes[('sensor.luf_family','players')]:p['weekly_goal_pct']=75

    def test_xp_weights_can_achieve_goal_with_fewer_than_75_percent_tasks(self):
        self.configure()
        for t in self.defaults:
            self.values['input_text.luf_task_config_'+t['id']]=json.dumps(dict(name=t['name'],player=t['player'],xp=90 if t['id']=='task01' else 10,days=1,once=False))
        self.values[self.defaults[0]['entity']]='1'
        self.refresh();goal=self.refresh_scores()
        self.attributes[('sensor.luf_family','players')][0]['weekly_goal_pct']=50
        self.assertEqual(self.values['sensor.player1_xp_previsto_semana'],'180')
        self.assertEqual(self.render(goal['state']),'True')
        self.assertEqual(self.values['sensor.player1_misiones_completadas_calculadas'],'1')

    def test_streak_helps_reach_goal_and_penalties_reduce_progress(self):
        self.configure()
        # 500 earned out of 820: 60.98% without a streak, 76.22% with x1.25.
        self.values['sensor.player1_xp_semana_bruto']='500'
        self.values['sensor.player1_xp_previsto_semana']='820'
        goal=self.refresh_scores()
        self.values['sensor.player1_xp_semana_bruto']='500'
        self.values['sensor.player1_xp_previsto_semana']='820'
        def earned():
            self.values['sensor.player1_multiplicador_racha_semanal']=self.render(self.sensor('player1','multiplicador_racha_semanal')['state'])
            self.values['sensor.player1_xp_semana_efectivo']=self.render(self.sensor('player1','xp_semana_efectivo')['state'])
            return self.render(goal['state'])
        self.assertEqual(earned(),'False')
        self.values['input_number.luf_player1_streak_weeks']='1'
        self.assertEqual(earned(),'True')
        self.assertEqual(self.values['sensor.player1_xp_semana_efectivo'],'625')
        self.values['input_number.luf_player1_penalties_this_week']='20'
        self.assertEqual(earned(),'False')

    def test_zero_budget_never_wins_and_zero_target_is_not_replaced_by_75(self):
        self.configure();goal=self.refresh_scores()
        self.values['sensor.player1_xp_previsto_semana']='0'
        self.assertEqual(self.render(goal['state']),'False')
        self.values['sensor.player1_xp_previsto_semana']='100'
        self.attributes[('sensor.luf_family','players')][0]['weekly_goal_pct']=0
        self.assertEqual(self.render(goal['state']),'True')
        self.assertEqual(self.render(goal['attributes']['objetivo_pct']),'0')

    def test_weekly_close_matches_live_score_without_circular_goal_condition(self):
        import yaml
        self.configure()
        for t in self.defaults:self.values[t['entity']]='127' if t['player']=='player1' else '0'
        self.values['input_text.luf_player1_active_week']='2026-W44'  # Include all closed days.
        self.values['input_number.luf_player1_streak_weeks']='1'
        self.values['input_number.luf_player1_penalties_this_week']='15'
        goal=self.refresh_scores()
        package=yaml.safe_load((ROOT/'config/packages/level_up_family/lf_player1.yaml').read_text(encoding='utf-8'))
        seq=package['script']['luf_player1_cerrar_semana']['sequence']
        start=next(i for i,s in enumerate(seq) if 'bonus_semana' in s.get('variables',{}))
        end=next(i for i,s in enumerate(seq) if 'nivel_inicio' in s.get('variables',{}))
        values=dict(dias_perfectos_cierre=7,xp_tareas=820,penalizaciones=15)
        for step in seq[start:end]:
            for key,expression in step['variables'].items():
                rendered=self.render(expression,**values)
                try:values[key]=ast.literal_eval(rendered)
                except (ValueError,SyntaxError):values[key]=rendered
        self.assertEqual(str(values['xp_efectivo']),self.values['sensor.player1_xp_semana_efectivo'])
        self.assertEqual(values['objetivo_conseguido'],1)
        self.assertEqual(values['racha_semanal_fin'],2)
        self.assertEqual(self.render(goal['state']),'True')


# Inherit only the renderer helpers; the catalogue suite is collected separately.
for name in list(vars(catalog.TaskCatalogTests)):
    if name.startswith('test_') and name not in vars(XPGoalTests):
        setattr(XPGoalTests,name,None)


if __name__=='__main__':unittest.main()
