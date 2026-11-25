"""Calendar counts and the parents' History view with multiple children."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

ROOT=Path(__file__).resolve().parent.parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader=load('history_overview_reader',ROOT/'config/level_up_family/python/luf_history.py')
model=load('history_overview_model',ROOT/'config/custom_components/level_up_family/model.py')
generator=load('history_overview_generator',ROOT/'tools/configure_family.py')


def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value,list):
        for child in value:
            yield from walk(child)


class HistoryOverviewTests(unittest.TestCase):
    def setUp(self):
        self.panel=yaml.safe_load((ROOT/'config/panel/level_up_family/parents.yaml').read_text(encoding='utf-8'))
        self.history=next(v for v in self.panel['views'] if v['path']=='historico-luf')
        self.weeks=[{'player_key':player,'year':2026,'iso_week':week}
                    for player in ('player1','player2') for week in (45,46,47)]
        self.years=[{'player_key':player,'year':2026} for player in ('player1','player2')]

    def test_reader_counts_unique_calendar_periods_and_keeps_record_counts(self):
        result=reader.summary_counts(self.weeks,self.years)
        self.assertEqual((result['weeks_count'],result['real_weeks_count'],result['years_count'],result['real_years_count']),(3,3,1,1))
        self.assertEqual((result['week_records_count'],result['year_records_count']),(6,2))
        self.assertEqual(len(self.weeks),6)

    def test_year_and_week_form_the_key_and_test_periods_are_separate(self):
        weeks=self.weeks+[{'year':2025,'iso_week':47},{'year':2099,'iso_week':1},{'year':'2099','iso_week':'1'}]
        years=self.years+[{'year':2025},{'year':2099},{'year':'2099'}]
        counts=reader.summary_counts(weeks,years)
        self.assertEqual((counts['real_weeks_count'],counts['real_years_count'],counts['test_weeks_count']),(4,2,1))
        self.assertEqual((counts['weeks_count'],counts['years_count']),(5,3))
        self.assertEqual(reader.summary_counts([],[])['real_weeks_count'],0)

    def test_counter_template_renders_three_weeks_and_one_year_on_old_reader_data(self):
        card=next(c for c in walk(self.history) if 'SEMANAS REALES' in c.get('custom_fields',{}).get('content',''))
        code=re.fullmatch(r'\[\[\[(.*?)\]\]\]\s*',card['custom_fields']['content'],re.S).group(1)
        program="""const fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));const html=new Function('states',input.code)({'sensor.luf_historico':{state:'6',attributes:input.attributes}});process.stdout.write(html.replace(/<[^>]*>/g,' ').replace(/\\s+/g,' ').trim());"""
        result=subprocess.run([shutil.which('node'),'-e',program],input=json.dumps({'code':code,'attributes':{'weeks':self.weeks,'years':self.years}}),
                              text=True,encoding='utf-8',capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertRegex(result.stdout,r'SEMANAS REALES 3 RESÚMENES ANUALES 1 DATOS DE PRUEBA 0')

    def test_editor_precedes_summaries_and_survives_provisioning_extra_children(self):
        first=self.history['sections'][1]['cards'][0]
        self.assertEqual(first['type'],'custom:level-up-family-history')
        templates=json.loads((ROOT/'config/custom_components/level_up_family/templates.json').read_text(encoding='utf-8'))
        registry=json.loads((ROOT/'config/level_up_family/family.json').read_text(encoding='utf-8'))
        registry=model.change(registry,'add',registry['revision'],name='Third child')
        histories=[model.parents_views(templates,registry)[1],generator.parents_panel(self.panel,registry['players'])['views'][1]]
        for history in histories:
            self.assertEqual(history['sections'][1]['cards'][0]['type'],'custom:level-up-family-history')
            summaries=[s for s in history['sections'] if (s.get('cards') or [{}])[0].get('heading') in ('player1','player2','Third child')]
            self.assertEqual(len(summaries),3)
            self.assertEqual(len([c for c in walk(history) if c.get('type')=='custom:level-up-family-history']),1)

    def test_content_occupies_the_full_grid_without_hidden_icon_columns(self):
        cards=[c for c in walk(self.history) if c.get('type')=='custom:button-card']
        self.assertEqual(len(cards),6)
        for card in cards:
            grid={k:v for style in card['styles']['grid'] for k,v in style.items()}
            self.assertEqual(grid['grid-template-areas'],'"content"')
            self.assertEqual(grid['grid-template-columns'],'minmax(0,1fr)')
            self.assertNotIn('minmax(360px,420px)',card['custom_fields']['content'])
