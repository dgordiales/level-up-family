"""Exercise the real card's actions and preserved drafts without browser dependencies."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

import test_closed_weeks as fixtures


class HistoryCardTests(unittest.TestCase):
    def test_review_apply_once_tasks_drafts_and_admin_controls(self):
        factory=fixtures.ClosedWeekTests()
        factory.setUp()
        self.addCleanup(factory.doCleanups)
        first,_,runtime=factory.setup_chain()
        original=factory.store.load(first,'player1')
        preview=factory.store.preview(first,'player1',original['revision'],{'daily':123,'weekly':1},runtime)
        preview['token']='review-token'
        factory.store.apply(first,'player1',original['revision'],{'daily':123,'weekly':1},runtime,'Correct Wednesday',{'prefix':'player1'})
        corrected=factory.store.load(first,'player1')
        path=Path(factory.temp.name)/'card-fixture.json'
        path.write_text(json.dumps(dict(original=original,preview=preview,corrected=corrected)),encoding='utf-8')
        program=r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const fixture=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
class Element {
 constructor(tag='element'){this.tagName=tag;this.children=[];this.attributes={};this.listeners={};this.style={setProperty(){}};this.dataset={};this.textContent='';}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=[...items];}
 attachShadow(){this.shadowRoot=new Element('shadow');return this.shadowRoot;}
 setAttribute(key,value){this.attributes[key]=value;}
 addEventListener(name,handler){this.listeners[name]=handler;}
 set innerHTML(value){throw new Error('Task and reward text must never be interpreted as HTML');}
}
const registry=new Map(),context=vm.createContext({HTMLElement:Element,document:{createElement:tag=>new Element(tag)},
 customElements:{get:key=>registry.get(key),define:(key,value)=>registry.set(key,value)},window:{}});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
function nodes(element){return [element,...element.children.flatMap(nodes)];}
function button(card,text){const b=nodes(card.shadowRoot).find(n=>n.tagName==='button'&&n.textContent===text);assert(b,`Missing button ${text}`);return b;}
function labelled(card,name){const b=nodes(card.shadowRoot).find(n=>n.attributes['aria-label']===name);assert(b,`Missing control ${name}`);return b;}
const calls=[];
let saved=false;
const hass={user:{is_admin:true},states:{
 'sensor.luf_family':{state:'1',attributes:{players:[{id:'player1',db_key:'player1',name:'Player 1',active:true}],revision:0}},
 'sensor.luf_historico':{state:'2',attributes:{weeks:[{week_id:1,player_key:'player1',year:2026,iso_week:45}]}},
 'input_boolean.luf_maintenance':{state:'off'}},
 callWS:async request=>{
  calls.push(request);
  assert.equal(request.domain,'level_up_family');assert.equal(request.service,'edit_closed_week');assert.equal(request.return_response,true);
  const d=request.service_data;assert.equal(d.week_id,1);assert.equal(d.player_id,'player1');
  if(d.operation==='load')return {response:saved?fixture.corrected:fixture.original};
  if(d.operation==='preview'){assert.equal(d.progress.daily,123);assert.equal(d.progress.weekly,1);assert.equal(d.reason,'Correct Wednesday');return{response:fixture.preview};}
  if(d.operation==='apply'){assert.equal(d.token,'review-token');saved=true;return{response:{ok:true}};}
  throw new Error('Unexpected operation');
 }};
const Card=registry.get('level-up-family-history'),card=new Card();card.setConfig({});card.hass=hass;
(async()=>{
 card.selected='1';card.player='player1';await card.run({operation:'load'});
 labelled(card,'Weekly mission: Miércoles').listeners.click();
 assert.equal(card.draft.tasks[1].progress,4,'A weekly mission moves its single mark');
 labelled(card,'Weekly mission: Lunes').listeners.click();
 assert.equal(card.draft.tasks[1].progress,1);
 labelled(card,'Daily mission: Miércoles').listeners.click();
 let reason=nodes(card.shadowRoot).find(n=>n.tagName==='textarea');reason.value='Correct Wednesday';reason.listeners.input();
 card.hass={...hass,states:{...hass.states,'sensor.irrelevant':{state:'changed'}}};
 assert.equal(card.draft.tasks[0].progress,123,'HA updates must preserve an unsaved draft');
 assert.equal(nodes(card.shadowRoot).find(n=>n.tagName==='textarea').value,'Correct Wednesday');
 await card.run({operation:'preview',revision:card.record.revision,progress:Object.fromEntries(card.draft.tasks.map(t=>[t.id,t.progress])),reason:card.reason});
 assert.equal(card.review.xp_delta,-35);
 assert(nodes(card.shadowRoot).some(n=>n.textContent==='XP final'));
 assert(nodes(card.shadowRoot).some(n=>n.textContent==='Racha diaria'));
 assert(nodes(card.shadowRoot).some(n=>n.textContent==='Objetivo / recompensa'));
 labelled(card,'Daily mission: Martes').listeners.click();assert.equal(card.review,null,'Editing a reviewed draft invalidates confirmation');
 labelled(card,'Daily mission: Martes').listeners.click();
 await card.run({operation:'preview',revision:card.record.revision,progress:Object.fromEntries(card.draft.tasks.map(t=>[t.id,t.progress])),reason:card.reason});
 await card.run({operation:'apply',token:card.review.token});
 assert.equal(card.record.week.tasks_completed,7);assert.equal(card.review,null);assert(saved);
 assert.equal(calls.filter(c=>c.service_data.operation==='apply').length,1);
 const child=new Card();child.setConfig({});child.hass={...hass,user:{is_admin:false}};
 assert(!nodes(child.shadowRoot).some(n=>n.tagName==='select'));
 console.log('History card controls passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        result=subprocess.run([shutil.which('node'),'-e',program,str(fixtures.ROOT/'config/www/level_up_family/level-up-family-cards.js'),str(path)],
                              capture_output=True,text=True,encoding='utf-8',timeout=25)
        self.assertEqual(result.returncode,0,result.stderr or result.stdout)
