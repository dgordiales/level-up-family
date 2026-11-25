"""Admin services for the parents' closed-week editor."""
from copy import deepcopy
import secrets
import time

from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service import async_register_admin_service

from .history_store import HistoryStore, score


class HistoryManager:
    def __init__(self, family):
        self.family, self.hass = family, family.hass
        self.store = HistoryStore(family.db, family.app / 'python/luf_db.py')
        self.plan = None

    def player(self, key):
        player = next((p for p in self.family.registry['players'] if p['id'] == key), None)
        if player is None:
            raise ValueError('No se encuentra ese hijo en la familia.')
        return player

    def number(self, entity):
        state = self.hass.states.get(entity)
        if state is None or state.state in ('unknown', 'unavailable'):
            raise ValueError(f'Espera a que esté disponible {entity}.')
        return float(state.state)

    def runtime(self, player):
        prefix = player['entity_prefix']
        total = self.number(f'input_number.luf_{prefix}_points_total')
        applied = self.hass.states.get(f'input_text.luf_{prefix}_last_applied_week')
        if not total.is_integer() or total < 0 or applied is None:
            raise ValueError('No se ha podido verificar el progreso vivo de este hijo.')
        return {'points_total': int(total), 'last_applied_week': applied.state,
                'streak_days': int(self.number(f'input_number.luf_{prefix}_streak_days')),
                'streak_weeks': int(self.number(f'input_number.luf_{prefix}_streak_weeks'))}

    def draft(self, player, week):
        catalog = self.hass.states.get('sensor.luf_task_catalog')
        if catalog is None or catalog.state in ('unknown', 'unavailable'):
            raise ValueError('El catálogo de tareas todavía no está disponible.')
        tasks = [{k: t[k] for k in ('id','name','xp','days','once')}
                 for t in catalog.attributes.get('tasks', []) if t['player'] == player['id']]
        for task in tasks:
            task['progress'] = 0
        prefix = player['entity_prefix']
        reward = self.hass.states.get(f'input_text.luf_{prefix}_weekly_reward')
        return {'tasks': tasks, 'rules': {
            'daily_bonus': int(self.number('input_number.luf_xp_daily_bonus')),
            'weekly_multiplier': self.number('input_number.luf_weekly_streak_multiplier'),
            'goal_pct': player.get('weekly_goal_pct', 75),
            'reward': reward.state if reward and reward.state not in ('unknown', 'unavailable') else '',
            'weekly_streak_before': week['weekly_streak_before'],
            'daily_streak_before': 0, 'xp_adjustment': 0}}

    async def recover(self):
        pending = await self.hass.async_add_executor_job(self.store.pending)
        if not pending:
            return
        await self.family.maintenance(True)
        resume = True
        for item in pending:
            data = item['data']
            targets = await self.hass.async_add_executor_job(self.store.recovery_values, item)
            values = {f"input_number.luf_{data['prefix']}_{key}": str(value)
                      for key, value in targets.items()}
            await self.family.restore_helpers(values)
            for entity, value in values.items():
                if self.number(entity) != float(value):
                    raise ValueError(f'Home Assistant no ha confirmado el valor de {entity}.')
            resume = resume and not data['was_maintenance']
        if resume and not self.family.pending_file.exists():
            await self.family.maintenance(False)
        for item in pending:
            await self.hass.async_add_executor_job(self.store.acknowledge, item['id'])
        self.family.error = ''
        self.family.publish()

    def check_ranges(self, player, result):
        for key, value in result.get('helpers', {}).items():
            state = self.hass.states.get(f"input_number.luf_{player['entity_prefix']}_{key}")
            if state is None or not state.attributes.get('min', 0) <= value <= state.attributes.get('max', float('inf')):
                raise ValueError(f'El nuevo valor de {key} queda fuera del rango del control en Home Assistant.')

    async def handle(self, call):
        try:
            async with self.family.lock:
                return await self.execute(call.data)
        except (ValueError, KeyError) as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def execute(self, data):
        operation, week_id = data['operation'], data['week_id']
        player = self.player(data['player_id'])
        key = player['db_key']
        if self.family.pending_file.exists() or self.hass.states.is_state('input_boolean.luf_maintenance', 'on'):
            raise ValueError('El juego está en mantenimiento. Espera a que termine la recuperación.')
        loaded = await self.hass.async_add_executor_job(self.store.load, week_id, key)
        if operation == 'load':
            if loaded['snapshot'] is None:
                loaded['draft'] = self.draft(player, loaded)
            return loaded
        if operation == 'baseline':
            # Registering an original record never changes the saved summary or live helpers.
            await self.hass.async_add_executor_job(self.family.backup, self.family.snapshot())
            return await self.hass.async_add_executor_job(self.store.register, week_id, key,
                data['snapshot'], data['revision'])
        runtime = self.runtime(player)
        if operation == 'preview':
            reason = data.get('reason', '').strip()
            if not 3 <= len(reason) <= 500:
                raise ValueError('Explica la corrección (entre 3 y 500 caracteres).')
            result = await self.hass.async_add_executor_job(self.store.preview, week_id, key,
                data['revision'], data['progress'], runtime)
            self.check_ranges(player, result)
            self.plan = {'token': secrets.token_hex(16), 'expires': time.monotonic() + 600,
                'player_id': player['id'], 'week_id': week_id, 'revision': data['revision'],
                'progress': deepcopy(data['progress']), 'runtime': runtime, 'reason': reason,
                'family_revision': self.family.registry['revision']}
            result['token'] = self.plan['token']
            return result
        if operation != 'apply':
            raise ValueError('Operación desconocida.')
        plan = self.plan
        if not plan or data.get('token') != plan['token'] or time.monotonic() > plan['expires'] or (
                plan['player_id'], plan['week_id'], plan['family_revision']) != (
                player['id'], week_id, self.family.registry['revision']):
            raise ValueError('La revisión ha caducado. Vuelve a previsualizar la corrección.')
        safe_to_resume = True
        try:
            await self.family.quiesce()
            if runtime != self.runtime(player) or runtime != plan['runtime']:
                raise ValueError('El progreso vivo ha cambiado. Vuelve a previsualizar la corrección.')
            # Revalidate under maintenance before creating the verified recovery copy.
            checked = await self.hass.async_add_executor_job(self.store.preview, week_id, key,
                plan['revision'], plan['progress'], runtime)
            self.check_ranges(player, checked)
            backup = await self.hass.async_add_executor_job(self.family.backup, self.family.snapshot())
            # From this point a failed commit response is ambiguous: keep maintenance on
            # until SQLite and the durable helper journal can be inspected/recovered.
            safe_to_resume = False
            result = await self.hass.async_add_executor_job(self.store.apply, week_id, key,
                plan['revision'], plan['progress'], runtime, plan['reason'],
                {'prefix': player['entity_prefix'], 'was_maintenance': False})
            await self.recover()
            safe_to_resume = True
            self.plan = None
            result['message'] = 'Sin cambios: el progreso ya era correcto.' if result['unchanged'] else 'Corrección guardada y progreso actualizado.'
            result['backup'] = backup.name
            try:
                await self.hass.services.async_call('homeassistant', 'update_entity',
                    {'entity_id': 'sensor.luf_historico'}, blocking=True)
            except Exception:
                pass  # The reader also refreshes every 60 seconds.
            return result
        except Exception:
            if not safe_to_resume:
                try:
                    current = await self.hass.async_add_executor_job(self.store.load, week_id, key)
                    safe_to_resume = current['revision'] == plan['revision']
                except Exception:
                    pass
            raise
        finally:
            if safe_to_resume:
                await self.family.maintenance(False)
            else:
                self.family.error = 'Comprueba la corrección pendiente en SQLite. El juego sigue en mantenimiento; reinicia HA para recuperar la sincronización.'
                self.family.publish()

    async def archive(self, call):
        try:
            async with self.family.lock:
                player = self.player(call.data['player_id'])
                loaded = await self.hass.async_add_executor_job(self.store.load, call.data['week_id'], player['db_key'])
                if loaded['snapshot'] is not None:
                    return {'ok': True, 'unchanged': True}
                active = self.hass.states.get(f"input_text.luf_{player['entity_prefix']}_active_week")
                week = loaded['week']
                if active is None or active.state != f"{week['year']:04d}-W{week['iso_week']:02d}":
                    # A retry after reset must never archive the new week's empty masks.
                    raise ValueError('Los bitmasks ya pertenecen a otra semana; completa el registro original desde Histórico.')
                draft = self.draft(player, loaded)
                catalog = self.hass.states.get('sensor.luf_task_catalog')
                by_id = {t['id']: t for t in catalog.attributes['tasks'] if t['player'] == player['id']}
                for task in draft['tasks']:
                    state = self.hass.states.get(by_id[task['id']]['entity'])
                    if state is None or state.state in ('unknown', 'unavailable'):
                        raise ValueError('Falta el progreso de una tarea al archivar la semana.')
                    task['progress'] = int(float(state.state)) & task['days']
                # Daily baseline is recoverable from the recorded Sunday result when
                # all seven days are perfect; otherwise any preceding streak ends here.
                stats = score(draft, loaded['weekly_streak_before'])
                if all(stats['perfect']):
                    draft['rules']['daily_streak_before'] = max(0, week['daily_streak_end'] - 7)
                return await self.hass.async_add_executor_job(self.store.register, call.data['week_id'],
                    player['db_key'], draft, loaded['revision'], True)
        except (ValueError, KeyError) as exc:
            raise HomeAssistantError(str(exc)) from exc


def register_history(family, vol):
    manager = HistoryManager(family)
    schema = vol.Schema({vol.Required('operation'): vol.In(['load','baseline','preview','apply']),
        vol.Required('player_id'): str, vol.Required('week_id'): int,
        vol.Optional('revision'): str, vol.Optional('snapshot'): dict,
        vol.Optional('progress'): dict, vol.Optional('reason'): str, vol.Optional('token'): str})
    async_register_admin_service(family.hass, 'level_up_family', 'edit_closed_week', manager.handle,
        schema=schema, supports_response=SupportsResponse.ONLY)
    async_register_admin_service(family.hass, 'level_up_family', 'archive_week', manager.archive,
        schema=vol.Schema({vol.Required('player_id'): str, vol.Required('week_id'): int}),
        supports_response=SupportsResponse.ONLY)
    return manager
