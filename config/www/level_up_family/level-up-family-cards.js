/* Level Up Family cards. No external runtime or HTML from task/reward text. */
(() => {
  'use strict';
  const CATALOG = 'sensor.luf_task_catalog';
  const DAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
  const DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  const CSS = `
    :host { display:block; --lf-accent:#65ddff; }
    ha-card { background:rgba(4,14,38,.94); color:#fff; border:1px solid rgba(101,221,255,.30); border-radius:20px; overflow:hidden; }
    .body { padding:18px; } h2 { margin:0 0 16px; font-size:18px; letter-spacing:.2px; }
    h3 { margin:24px 0 12px; font-size:16px; } p,.hint { font-size:13px; line-height:1.5; color:rgba(255,255,255,.72); }
    .hint { margin:8px 0 14px; } .message { min-height:1.5em; margin:12px 0 0; font-size:13px; line-height:1.4; color:#a2f4df; }
    .message.error { color:#ffb4b4; } .empty { padding:12px 0; color:rgba(255,255,255,.72); }
    button,input,select,textarea { font:inherit; box-sizing:border-box; }
    button { cursor:pointer; border:1px solid rgba(101,221,255,.4); border-radius:12px; padding:10px 14px; background:rgba(101,221,255,.14); color:#fff; font-weight:700; }
    button:hover:not(:disabled) { background:rgba(101,221,255,.25); } button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible { outline:2px solid var(--lf-accent); outline-offset:3px; }
    button:disabled { opacity:.45; cursor:default; } .secondary { background:transparent; }
    .row { display:flex; align-items:center; gap:12px; } .grow { flex:1; min-width:0; } .small { font-size:12px; color:rgba(255,255,255,.70); }
    ha-card.mission-list { background:transparent; border:0; border-radius:0; box-shadow:none; overflow:visible; }
    .mission-body { padding:0; }
    .task { width:100%; height:48px; display:flex; align-items:center; text-align:left; margin:0 0 8px; padding:0 10px; border-radius:14px; box-shadow:none; background:var(--lf-track); border:1px solid var(--lf-task-border); }
    .task:last-of-type { margin-bottom:0; }
    .task:hover:not(:disabled) { background:var(--lf-track); filter:brightness(1.12); }
    .task.done,.task.done:hover:not(:disabled) { background:var(--lf-completed-background); border-color:var(--lf-completed-border); }
    .task .mark { width:22px; flex:0 0 22px; text-align:center; font-size:20px; font-weight:900; color:var(--lf-accent); }
    .task .name { padding-left:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12px; font-weight:800; color:#fff; }
    .task .xp { color:var(--lf-accent); font-size:11px; font-weight:900; white-space:nowrap; margin-left:10px; }
    .task.done .mark,.task.done .xp { color:var(--lf-completed-color); }
    .mission-body .message:empty { display:none; }
    ha-icon { --mdc-icon-size:25px; color:var(--lf-accent); flex-shrink:0; }
    label { display:block; font-size:13px; font-weight:600; } input:not([type=checkbox]),select,textarea { display:block; width:100%; margin-top:7px; padding:11px; border:1px solid rgba(255,255,255,.26); border-radius:10px; background:#0b1c37; color:#fff; }
    textarea { resize:vertical; min-height:86px; } select option { background:#0b1c37; } input:disabled,select:disabled { opacity:.55; }
    .form { display:grid; gap:15px; grid-template-columns:repeat(2,minmax(0,1fr)); } .wide { grid-column:1/-1; }
    .days { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; } .day-label { display:flex; gap:5px; align-items:center; padding:8px; background:rgba(255,255,255,.06); border-radius:9px; }
    input[type=checkbox] { accent-color:#65ddff; width:17px; height:17px; } .check { display:flex; gap:8px; align-items:center; }
    .actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; } .lock { padding:10px; background:rgba(255,198,76,.12); color:#ffe3a4; border-radius:10px; font-size:13px; margin:12px 0; }
    .week-task { margin-top:16px; } .week-task .name { font-size:14px; overflow-wrap:anywhere; } .week-days { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:5px; margin-top:8px; }
    .week-days button { padding:9px 0; font-size:12px; border-radius:8px; } .week-days button.done { background:rgba(25,149,113,.5); border-color:#67efc4; }
    details summary { cursor:pointer; font-weight:700; font-size:14px; } .reward { padding:18px; display:flex; gap:16px; align-items:center; }
    .reward ha-icon,.reward img { --mdc-icon-size:48px; width:54px; height:54px; object-fit:contain; filter:drop-shadow(0 0 9px rgba(101,221,255,.35)); }
    .reward img { width:80px; height:80px; flex:0 0 80px; }
    .eyebrow { color:var(--lf-accent); font-size:11px; font-weight:900; letter-spacing:1px; } .prize { font-size:17px; font-weight:800; margin:5px 0; white-space:pre-wrap; overflow-wrap:anywhere; } .goal { font-size:12px; opacity:.75; }
    @media(max-width:540px) { .form { grid-template-columns:1fr; } .body { padding:15px; } .day-label { padding:8px 5px; } }
  `;
  function node(tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  }
  function isoDate(date) {
    return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  }
  function monday(date = new Date()) {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 12);
    d.setDate(d.getDate() - ((d.getDay()+6)%7));
    return d;
  }
  function tasks(hass) {
    const state = hass?.states[CATALOG];
    if (!state || ['unknown','unavailable'].includes(state.state)) return null;
    return Array.isArray(state.attributes.tasks) ? state.attributes.tasks : null;
  }
  function cleanState(hass, entity) {
    const text = hass?.states[entity]?.state;
    return text === undefined || ['unknown','unavailable'].includes(text) ? '' : text;
  }
  function completed(task, bit) { return Boolean(task.progress & (task.once ? task.days : bit)); }
  function difficulty(xp) { return [10,15,20].includes(Number(xp)) ? String(xp) : 'custom'; }
  function textField(label, tag='input') {
    const holder = node('label', label);
    const input = node(tag);
    holder.append(input);
    return [holder,input];
  }
  class FamilyCard extends HTMLElement {
    constructor() { super(); this.attachShadow({mode:'open'}); }
    setConfig(config) { this.config = config; if (this._hass) this.render(); }
    set hass(hass) { this._hass=hass; if (this.config) this.render(); }
    getCardSize() { return 4; }
    shell() {
      this.shadowRoot.replaceChildren();
      const style=node('style',CSS), card=node('ha-card');
      this.shadowRoot.append(style,card);
      const theme=this._hass?.states['sensor.luf_theme']?.attributes || {};
      this.style.setProperty('--lf-accent', /^#[a-fA-F0-9]{3,8}$/.test(theme.accent || '') ? theme.accent : '#65ddff');
      return card;
    }
    message(text, error=false) {
      if (!this.status) return;
      this.status.textContent=text;
      this.status.className='message'+(error?' error':'');
    }
    async service(name, data) {
      const result=await this._hass.callWS({type:'call_service',domain:'script',service:name,service_data:data,return_response:true});
      if(!result?.response?.ok)throw new Error(result?.response?.error || 'Home Assistant no ha confirmado el cambio. Recarga y comprueba sus valores.');
      return result.response;
    }
  }
  class FamilyReward extends FamilyCard {
    render() {
      const reward=cleanState(this._hass,this.config.reward_entity);
      const theme=this._hass.states['sensor.luf_theme']?.attributes || {};
      const goal=this._hass.states[this.config.goal_entity]?.state === 'on';
      const seasonPath=/^\/local\/level_up_family\/season_\d+\/?$/.test(theme.season_path || '')
        ? theme.season_path.replace(/\/$/,'') : '/local/level_up_family/season_01';
      const rewardImage=typeof theme.reward_image==='string' && theme.reward_image.startsWith('/local/level_up_family/')
        ? theme.reward_image : `${seasonPath}/recompensa.png`;
      const signature=JSON.stringify([reward,rewardImage,theme.accent,goal,cleanState(this._hass,'input_number.luf_weekly_goal_pct')]);
      if (signature===this.signature) return;
      this.signature=signature;
      const card=this.shell(), row=node('div',undefined,'reward');
      const icon=node('ha-icon'); icon.setAttribute('icon','mdi:gift-outline');
      const img=node('img'); img.alt='Recompensa semanal'; img.src=rewardImage;
      img.addEventListener('error',()=>img.replaceWith(icon),{once:true}); row.append(img);
      const text=node('div',undefined,'grow');
      text.append(node('div','TU RECOMPENSA SEMANAL','eyebrow'),node('div',reward || 'Tu premio está por decidir','prize'),node('div',goal?'¡Objetivo semanal conseguido!':`Alcanza el ${cleanState(this._hass,'input_number.luf_weekly_goal_pct') || '75'}% de tus misiones semanales`,'goal'));
      row.append(text); card.append(row);
    }
  }
  class FamilyMissions extends FamilyCard {
    render() {
      const today=new Intl.DateTimeFormat('sv-SE',{timeZone:this._hass.config?.time_zone}).format(new Date());
      const all=tasks(this._hass), now=new Date(today+'T12:00:00');
      const theme=this._hass.states['sensor.luf_theme']?.attributes || {};
      const start=cleanState(this._hass,'input_datetime.luf_season_start');
      const signature=JSON.stringify([all,today,this._busy,this._error,this.config,theme,start,cleanState(this._hass,'input_boolean.luf_maintenance')]);
      if(signature===this.signature)return;
      this.signature=signature;
      const card=this.shell(), body=node('div',undefined,this.config.week?'body':'mission-body');card.append(body);
      if(!this.config.week){
        card.className='mission-list';
        for(const [name,value] of Object.entries({
          '--lf-track':theme.track || '#07132f',
          '--lf-task-border':theme.border_strong || 'rgba(93,125,255,.72)',
          '--lf-completed-background':theme.completed_background || 'rgba(17,95,95,.72)',
          '--lf-completed-border':theme.completed_border || 'rgba(80,255,205,.75)',
          '--lf-completed-color':theme.completed_color || '#68ffd5'
        }))card.style.setProperty(name,value);
      }
      const list=(all||[]).filter(t=>t.player===this.config.player && t.days>0);
      const bit=1<<((now.getDay()+6)%7);
      const visible=this.config.week?list:list.filter(t=>t.days&bit);
      let content=body;
      if(this.config.week){
        const details=node('details');details.open=Boolean(this._expanded);
        details.addEventListener('toggle',()=>{this._expanded=details.open;});
        details.append(node('summary',this.config.title || 'Ver y corregir esta semana'));body.append(details);content=details;
      }
      if(all===null)content.append(node('p','Las misiones todavía no están disponibles.','empty'));
      else if(!visible.length)content.append(node('p',this.config.week?'No tienes tareas asignadas esta semana.':'Hoy no hay misiones programadas.','empty'));
      for(const task of visible){
        if(!this.config.week){
          const done=completed(task,bit),button=node('button',undefined,'task'+(done?' done':''));
          button.type='button';button.setAttribute('aria-pressed',String(done));
          button.title=task.name;
          button.append(node('span',done?'✓':'○','mark'),node('span',task.name,'grow name'),node('span',`+${task.xp} XP`,'xp'));
          button.disabled=Boolean(this._busy)||!start||today<start||cleanState(this._hass,'input_boolean.luf_maintenance')==='on';
          button.addEventListener('click',()=>this.toggle(task,today));content.append(button);
        }else{
          const holder=node('div',undefined,'week-task');holder.append(node('div',task.name+(task.once?' · una vez por semana':''),'name'));
          const buttons=node('div',undefined,'week-days');
          for(let i=0;i<7;i++){
            const date=monday(now);date.setDate(date.getDate()+i);const key=isoDate(date),b=1<<i;
            const button=node('button',DAYS[i],completed(task,b)?'done':'');button.type='button';
            button.setAttribute('aria-label',`${task.name} · ${DAY_NAMES[i]}`);button.setAttribute('aria-pressed',String(completed(task,b)));
            button.disabled=!(task.days&b)||key>today||!start||key<start||Boolean(this._busy)||cleanState(this._hass,'input_boolean.luf_maintenance')==='on';
            button.addEventListener('click',()=>this.toggle(task,key));buttons.append(button);
          }
          holder.append(buttons);content.append(holder);
        }
      }
      this.status=node('p',this._error||'','message'+(this._error?' error':''));this.status.setAttribute('role','status');content.append(this.status);
    }
    async toggle(task,date){
      if(this._busy)return;this._busy=true;this._error='';this.render();
      try{await this.service('luf_task_mutate',{operation:'toggle',player:this.config.player,entity:task.entity,fecha:date});}
      catch(error){this._error=error.message||'No se ha podido cambiar la misión.';}
      finally{this._busy=false;this.render();}
    }
  }
  class FamilyAdmin extends FamilyCard {
    render(){
      if(!this._hass.user?.is_admin){const card=this.shell();card.append(node('p','Administración de padres','body'));this.initialized=false;return;}
      const roster=this._hass.states['sensor.luf_family']?.attributes?.players;
      if(Array.isArray(roster)){
        const active=roster.filter(p=>p.active), signature=JSON.stringify(active.map(p=>[p.id,p.name,p.reward_entity]));
        if(signature!==this.rosterSignature){
          if(this.initialized && (this.dirty || Object.values(this.rewardForms||{}).some(f=>f.dirty))){
            this.save.disabled=true;this.message('La familia ha cambiado. Descarta los cambios o recarga el panel para actualizar el formulario.',true);return;
          }
          this.config={...this.config,players:Object.fromEntries(active.map(p=>[p.id,p.name])),rewards:Object.fromEntries(active.map(p=>[p.id,p.reward_entity]))};
          this.rosterSignature=signature;this.initialized=false;this.loaded=null;this.optionsSignature=null;
        }
      }
      const all=tasks(this._hass);
      if(!this.initialized){this.build();this.initialized=true;}
      const signature=JSON.stringify((all||[]).map(t=>[t.id,t.name,t.player]));
      if(signature!==this.optionsSignature){
        this.optionsSignature=signature;
        this.select.replaceChildren();
        for(const task of all||[]){const option=node('option',`${task.name} · ${this.config.players[task.player] || task.player}`);option.value=task.id;this.select.append(option);}
        if(!this.selected)this.selected=all?.[0]?.id;
        this.select.value=this.selected||'';
      }
      const task=(all||[]).find(t=>t.id===this.selected);
      if(task && (!this.loaded || (!this.dirty && this.loaded.revision!==task.revision)))this.loadTask(task);
      const locked=Boolean(task && task.progress!==0);
      for(const field of this.ruleFields)field.disabled=locked || this._busy || !task;
      this.taskName.disabled=this._busy||!task;
      this.save.disabled=this._busy||!task||all===null;
      this.lock.hidden=!locked;
      this.availability.textContent=all===null?'El catálogo se está cargando.':'';
      for(const [player,form] of Object.entries(this.rewardForms)){
        const value=cleanState(this._hass,this.config.rewards[player]);
        if(!form.dirty){form.input.value=value;form.expected=value;}
      }
    }
    build(){
      const card=this.shell(),body=node('div',undefined,'body');card.append(body);
      body.append(node('h2','Tareas y recompensas'));
      body.append(node('p','Cambia el nombre, la dificultad y los días de las tareas. Los XP, días y jugador solo se pueden cambiar si esa tarea no tiene progreso esta semana.','hint'));
      this.availability=node('p','','hint');body.append(this.availability);
      const [choose,select]=textField('Tarea','select');this.select=select;body.append(choose);
      select.addEventListener('change',()=>{
        if(this.dirty){select.value=this.selected;this.message('Guarda o descarta los cambios antes de seleccionar otra tarea.',true);return;}
        this.selected=select.value;this.loaded=null;this.render();
      });
      this.lock=node('p','Esta tarea ya tiene progreso. Su nombre sigue siendo editable.','lock');body.append(this.lock);
      const grid=node('div',undefined,'form');body.append(grid);
      const [nameLabel,nameInput]=textField('Nombre de la tarea');nameLabel.className='wide';this.taskName=nameInput;nameInput.maxLength=80;grid.append(nameLabel);
      const [playerLabel,playerInput]=textField('Para quién','select');this.playerInput=playerInput;
      for(const [key,name] of Object.entries(this.config.players)){const option=node('option',name);option.value=key;playerInput.append(option);}grid.append(playerLabel);
      const [diffLabel,diff]=textField('Dificultad','select');this.diff=diff;
      for(const [key,label] of [['10','Sencilla · 10 XP'],['15','Estándar · 15 XP'],['20','Importante · 20 XP'],['custom','XP personalizados']]){const option=node('option',label);option.value=key;diff.append(option);}grid.append(diffLabel);
      const [xpLabel,xp]=textField('XP por completar la tarea');this.xp=xp;xp.type='number';xp.min=0;xp.max=100;xp.step=1;grid.append(xpLabel);
      const dayGroup=node('div',undefined,'wide');dayGroup.append(node('label','Días en que se aplica'));
      const days=node('div',undefined,'days');this.dayInputs=[];
      for(let i=0;i<7;i++){const label=node('label',undefined,'day-label'),input=node('input');input.type='checkbox';input.setAttribute('aria-label',DAY_NAMES[i]);label.append(input,node('span',DAYS[i]));days.append(label);this.dayInputs.push(input);}dayGroup.append(days);grid.append(dayGroup);
      const onceLabel=node('label',undefined,'wide check');this.once=node('input');this.once.type='checkbox';onceLabel.append(this.once,node('span','Solo una vez por semana, en cualquiera de los días elegidos'));grid.append(onceLabel);
      grid.append(node('p','Sin días seleccionados, la tarea queda desactivada. Las tareas de una vez por semana no cuentan para el bonus de día perfecto.','wide hint'));
      this.ruleFields=[playerInput,diff,xp,...this.dayInputs,this.once];
      for(const field of [nameInput,...this.ruleFields])field.addEventListener('input',()=>{this.dirty=true;});
      diff.addEventListener('change',()=>{if(diff.value!=='custom')xp.value=diff.value;this.dirty=true;});
      xp.addEventListener('input',()=>{diff.value=difficulty(xp.value);});
      const actions=node('div',undefined,'actions');this.save=node('button','Guardar tarea');this.save.type='button';this.save.addEventListener('click',()=>this.saveTask());
      const discard=node('button','Descartar cambios','secondary');discard.type='button';discard.addEventListener('click',()=>{this.dirty=false;for(const f of Object.values(this.rewardForms||{}))f.dirty=false;this.loaded=null;this.message('');this.render();});actions.append(this.save,discard);body.append(actions);
      this.status=node('p','','message');this.status.setAttribute('role','status');body.append(this.status);
      body.append(node('h3','Recompensa semanal de cada jugador'),node('p','Describe el premio que recibirá cada uno al alcanzar su objetivo semanal.','hint'));
      this.rewardForms={};
      for(const [player,name] of Object.entries(this.config.players)){
        const [label,input]=textField(`Premio de ${name}`,'textarea');input.maxLength=255;input.placeholder='Por ejemplo: elegir la película del viernes';
        const form={input,dirty:false,expected:''};this.rewardForms[player]=form;input.addEventListener('input',()=>{form.dirty=true;});
        const button=node('button',`Guardar premio de ${name}`);button.type='button';const status=node('p','','message');status.setAttribute('role','status');
        button.addEventListener('click',async()=>{
          button.disabled=true;status.textContent='Guardando…';status.className='message';
          try{await this.service('luf_configurar_recompensa',{player,reward:input.value,expected:form.expected});form.expected=input.value.trim();input.value=form.expected;form.dirty=false;status.textContent='Premio guardado.';}
          catch(error){status.textContent=error.message||'No se ha podido guardar el premio.';status.className='message error';}
          finally{button.disabled=false;}
        });
        const row=node('div',undefined,'actions');row.append(button);body.append(label,row,status);
      }
    }
    loadTask(task){
      this.loaded={...task};this.taskName.value=task.name;this.playerInput.value=task.player;this.xp.value=task.xp;this.diff.value=difficulty(task.xp);
      this.once.checked=Boolean(task.once);this.dayInputs.forEach((input,i)=>{input.checked=Boolean(task.days&(1<<i));});this.dirty=false;
    }
    async saveTask(){
      if(this._busy||!this.loaded)return;
      const xp=Number(this.xp.value),name=this.taskName.value.trim();
      if(!name||name.length>80||this.xp.value===''||!Number.isInteger(xp)||xp<0||xp>100){this.message('Escribe un nombre y un número entero de XP entre 0 y 100.',true);return;}
      const payload={task_id:this.selected,name,player:this.playerInput.value,xp,days:this.dayInputs.reduce((mask,input,i)=>mask|(input.checked?1<<i:0),0),once:this.once.checked,expected:this.loaded.revision};
      this._busy=true;this.message('Guardando…');this.render();
      try{await this.service('luf_configurar_tarea',payload);this.dirty=false;this.loaded=null;this.message('Tarea guardada.');}
      catch(error){this.message(error.message||'No se ha podido guardar la tarea.',true);}
      finally{this._busy=false;this.render();}
    }
  }
  class FamilyRoster extends FamilyCard {
    render(){
      const state=this._hass.states[this.config.entity || 'sensor.luf_family'];
      const data=state?.attributes;
      const signature=JSON.stringify([data,this._busy,this._message,this._error,this._review,this._hass.user?.is_admin]);
      if(signature===this.signature)return;this.signature=signature;
      const drafts=this.nameDrafts || {};
      const addDraft=this.shadowRoot.querySelector('input[data-add]')?.value || this.addDraft || '';
      const card=this.shell(),body=node('div',undefined,'body');card.append(body);
      body.append(node('h2','Familia'));
      if(!this._hass.user?.is_admin){body.append(node('p','Solo los padres pueden administrar la familia.'));return;}
      if(!data){body.append(node('p','La gestión de familia todavía no está disponible en HA.'));return;}
      body.append(node('p','Cambia los nombres o retira un hijo conservando sus puntos, sus tareas y su histórico. El identificador de cada jugador permanece siempre igual.','hint'));
      const disabled=Boolean(this._busy||data.busy||data.restart_pending);
      const button=(text,action,secondary=false)=>{const b=node('button',text,secondary?'secondary':'');b.type='button';b.disabled=disabled;b.addEventListener('click',action);return b;};
      for(const player of data.players || []){
        const holder=node('div');holder.append(node('h3',player.name+(player.active?'':' · retirado')));
        const [label,input]=textField('Nombre de '+player.name);input.maxLength=40;input.value=drafts[player.id]?.value ?? player.name;input.dataset.player=player.id;input.disabled=disabled;
        input.addEventListener('input',()=>{this.nameDrafts=this.nameDrafts||{};this.nameDrafts[player.id]={value:input.value,revision:this.nameDrafts[player.id]?.revision ?? data.revision};});holder.append(label);
        const actions=node('div',undefined,'actions');
        actions.append(button('Guardar nombre',()=>this.run({operation:'rename',player_id:player.id,name:input.value.trim(),revision:this.nameDrafts?.[player.id]?.revision ?? data.revision})));
        if(player.active)actions.append(button('Retirar a '+player.name,()=>{this._review={operation:'retire',player_id:player.id,name:player.name,revision:data.revision};this.render();},true));
        holder.append(actions);
        if(!player.active){
          const summary=player.retired_summary;
          holder.append(node('p',summary?`Nivel ${summary.level} · ${summary.total_xp} XP totales · ${summary.weekly_xp} XP en ${summary.week}. Sus registros siguen en Histórico.`:'Su progreso está archivado. Sus registros siguen en Histórico.','hint'));
        }
        body.append(holder);
      }
      body.append(node('h3','Añadir un hijo'));
      const [label,input]=textField('Nombre del nuevo hijo');input.maxLength=40;input.dataset.add='true';input.value=addDraft;input.disabled=disabled;
      input.addEventListener('input',()=>{this.addDraft=input.value;});body.append(label);
      const addActions=node('div',undefined,'actions');addActions.append(button('Preparar alta',()=>this.run({operation:'prepare_add',name:input.value.trim(),revision:data.revision})));body.append(addActions);
      body.append(node('p','El alta prepara su panel y diez tareas para configurar. Después de revisar la propuesta, podrás aplicarla y reiniciar Home Assistant desde aquí.','hint'));
      if(this._review){
        const review=node('div',undefined,'lock');review.setAttribute('role','region');review.setAttribute('aria-label','Revisar cambio de familia');
        const retiring=this._review.operation==='retire';
        review.append(node('h3',retiring?'Retirar a '+this._review.name:'Alta de '+this._review.name));
        review.append(node('p',retiring?'Dejará de aparecer en los controles activos. No se borrarán sus puntos, misiones ni registros históricos.':this._review.message));
        const actions=node('div',undefined,'actions');actions.append(button(retiring?'Confirmar retirada':'Aplicar alta y reiniciar HA',()=>this.run(retiring?{operation:'retire',player_id:this._review.player_id,revision:this._review.revision}:{operation:'apply_add',token:this._review.token})));
        actions.append(button('Cancelar',()=>{this._review=null;this._message='Propuesta cancelada. No se ha hecho ningún cambio.';this._error=false;this.render();},true));review.append(actions);body.append(review);
      }
      this.status=node('p',data.error || (data.restart_pending?'Alta pendiente. HA necesita terminar el reinicio y recuperar el progreso.':this._message||''),'message'+(this._error||data.error?' error':''));
      this.status.setAttribute('role','status');body.append(this.status);
    }
    async run(payload){
      if(this._busy)return;
      if(['rename','prepare_add'].includes(payload.operation) && (!payload.name || payload.name.length>40)){this._error=true;this._message='Escribe un nombre de entre 1 y 40 caracteres.';this.render();return;}
      this._busy=true;this._error=false;this._message='Comprobando…';this.render();
      try{
        const result=await this._hass.callWS({type:'call_service',domain:'level_up_family',service:'manage_family',service_data:payload,return_response:true});
        const reply=result?.response;if(!reply?.ok)throw new Error(reply?.error || 'HA no ha confirmado el cambio.');
        this._message=reply.message||'Cambio guardado.';
        if(payload.operation==='rename' && this.nameDrafts)delete this.nameDrafts[payload.player_id];
        this._review=payload.operation==='prepare_add'?{...reply,operation:'apply_add'}:null;
        if(payload.operation==='apply_add')this.addDraft='';
      }catch(error){this._error=true;this._message=error.message||'No se ha podido guardar el cambio.';}
      finally{this._busy=false;this.render();}
    }
  }
  for(const [type,element] of [['level-up-family-reward',FamilyReward],['level-up-family-missions',FamilyMissions],['level-up-family-admin',FamilyAdmin],['level-up-family-roster',FamilyRoster]]){
    if(!customElements.get(type))customElements.define(type,element);
  }
  window.customCards=window.customCards||[];
  for(const [type,name] of [['level-up-family-admin','Level Up Family · Administración'],['level-up-family-missions','Level Up Family · Misiones'],['level-up-family-reward','Level Up Family · Recompensa'],['level-up-family-roster','Level Up Family · Familia']]){
    if(!window.customCards.some(card=>card.type===type))window.customCards.push({type,name,preview:false,description:'Level Up Family'});
  }
  if(typeof module!=='undefined')module.exports={isoDate,monday,completed,difficulty};
})();
