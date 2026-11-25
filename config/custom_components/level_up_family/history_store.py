"""Closed-week corrections. SQLite is authoritative; previews always roll back."""
from contextlib import closing
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import math
import sqlite3


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def integer(value, minimum, maximum, label):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{label}: escribe un entero entre {minimum} y {maximum}.')
    return value


def validate_snapshot(value):
    if not isinstance(value, dict) or set(value) != {'tasks', 'rules'}:
        raise ValueError('Falta el registro de tareas y reglas de la semana.')
    tasks, rules = value['tasks'], value['rules']
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ValueError('La semana debe contener entre 1 y 100 tareas.')
    seen = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {'id', 'name', 'xp', 'days', 'once', 'progress'}:
            raise ValueError('Registro de tarea inválido.')
        if not isinstance(task['id'], str) or not 1 <= len(task['id']) <= 100 or task['id'] in seen:
            raise ValueError('Las tareas deben tener identificadores únicos.')
        seen.add(task['id'])
        if not isinstance(task['name'], str) or not 1 <= len(task['name']) <= 255:
            raise ValueError('Nombre de tarea inválido.')
        integer(task['xp'], 0, 10000, 'XP de tarea')
        integer(task['days'], 0, 127, 'Días previstos')
        integer(task['progress'], 0, 127, 'Tareas completadas')
        if type(task['once']) is not bool or task['progress'] & ~task['days']:
            raise ValueError('Hay tareas marcadas fuera de sus días previstos.')
    if not isinstance(rules, dict) or set(rules) != {
            'daily_bonus', 'weekly_multiplier', 'goal_pct', 'reward',
            'weekly_streak_before', 'daily_streak_before', 'xp_adjustment'}:
        raise ValueError('Reglas históricas incompletas.')
    integer(rules['daily_bonus'], 0, 10000, 'Bonus diario')
    integer(rules['goal_pct'], 0, 100, 'Objetivo')
    integer(rules['weekly_streak_before'], 0, 100000, 'Racha semanal inicial')
    integer(rules['daily_streak_before'], 0, 100000, 'Racha diaria inicial')
    integer(rules['xp_adjustment'], -1000000, 1000000, 'Ajuste histórico')
    if type(rules['weekly_multiplier']) not in (int, float) or not math.isfinite(rules['weekly_multiplier']) or not 1 <= rules['weekly_multiplier'] <= 10:
        raise ValueError('El multiplicador debe estar entre 1 y 10.')
    if not isinstance(rules['reward'], str) or len(rules['reward']) > 255:
        raise ValueError('Recompensa inválida.')
    return deepcopy(value)


def score(snapshot, incoming):
    tasks, rules = snapshot['tasks'], snapshot['rules']
    due = sum(bool(t['days']) if t['once'] else t['days'].bit_count() for t in tasks)
    done = sum(bool(t['progress']) if t['once'] else t['progress'].bit_count() for t in tasks)
    xp = sum(t['xp'] * (bool(t['progress']) if t['once'] else t['progress'].bit_count()) for t in tasks)
    budget = sum(t['xp'] * (bool(t['days']) if t['once'] else t['days'].bit_count()) for t in tasks)
    perfect = []
    for i in range(7):
        daily = [t for t in tasks if not t['once'] and t['days'] & (1 << i)]
        perfect.append(int(bool(daily) and all(t['progress'] & (1 << i) for t in daily)))
    bonus = sum(perfect) * rules['daily_bonus']
    multiplier = rules['weekly_multiplier'] if incoming >= 1 else 1
    effective = max(0, round((xp + bonus) * multiplier) + rules['xp_adjustment'])
    return {'tasks_due': due, 'tasks_completed': done, 'task_xp': xp,
            'perfect_days': sum(perfect), 'bonus_xp': bonus, 'budget': budget,
            'multiplier': multiplier, 'gross_effective': effective, 'perfect': perfect}


class HistoryStore:
    def __init__(self, database, db_module_path):
        self.database = database
        spec = importlib.util.spec_from_file_location('luf_history_database', db_module_path)
        self.db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.db_module)

    def connect(self):
        # Refuse to create an empty game database on a configuration mistake.
        conn = sqlite3.connect(self.database.resolve().as_uri() + '?mode=rw', uri=True, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def schema(self, conn):
        # Additive migration, performed only on first use. Existing weeks are untouched.
        conn.execute('''CREATE TABLE IF NOT EXISTS week_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER NOT NULL,
            week_id INTEGER NOT NULL UNIQUE, snapshot_json TEXT NOT NULL,
            revision INTEGER NOT NULL, audit_json TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE,
            FOREIGN KEY(week_id) REFERENCES weeks(id) ON DELETE CASCADE)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS history_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER NOT NULL UNIQUE,
            helpers_json TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE)''')

    def week(self, conn, week_id, db_key):
        row = conn.execute('''SELECT w.*, p.player_key FROM weeks w JOIN players p ON p.id=w.player_id
                              WHERE w.id=? AND p.player_key=?''', (week_id, db_key)).fetchone()
        if row is None:
            raise ValueError('No se encuentra esa semana de ese hijo.')
        if date.fromisoformat(row['week_end']) >= date.today():
            raise ValueError('Solo se pueden editar semanas cerradas de días anteriores.')
        return dict(row)

    def fingerprint(self, conn, player_id):
        data = {}
        for table in ('weeks', 'days', 'week_history', 'history_sync'):
            data[table] = [dict(r) for r in conn.execute(
                f'SELECT * FROM {table} WHERE player_id=? ORDER BY id', (player_id,))]
        return hashlib.sha256(encoded(data).encode()).hexdigest()

    def incoming(self, conn, row, field, fallback):
        previous = conn.execute('SELECT * FROM weeks WHERE player_id=? AND week_end=?',
            (row['player_id'], (date.fromisoformat(row['week_start']) - timedelta(days=1)).isoformat())).fetchone()
        return int(previous[field]) if previous else fallback

    def load(self, week_id, db_key):
        with closing(self.connect()) as conn, conn:
            self.schema(conn)
            row = self.week(conn, week_id, db_key)
            detail = conn.execute('SELECT * FROM week_history WHERE week_id=?', (week_id,)).fetchone()
            return {'ok': True, 'week': row, 'revision': self.fingerprint(conn, row['player_id']),
                    'snapshot': json.loads(detail['snapshot_json']) if detail else None,
                    'weekly_streak_before': self.incoming(conn, row, 'weekly_streak_end', max(0, row['weekly_streak_end'] - 1)),
                    'audit': json.loads(detail['audit_json'])[-10:] if detail else []}

    def register(self, week_id, db_key, snapshot, revision=None, automatic=False):
        snapshot = validate_snapshot(snapshot)
        with closing(self.connect()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            self.schema(conn)
            row = self.week(conn, week_id, db_key)
            if conn.execute('SELECT 1 FROM week_history WHERE week_id=?', (week_id,)).fetchone():
                if automatic:
                    return {'ok': True, 'unchanged': True}
                raise ValueError('Esta semana ya tiene registro. Recarga antes de editarla.')
            if revision is not None and revision != self.fingerprint(conn, row['player_id']):
                raise ValueError('El histórico ha cambiado. Recarga la semana.')
            rules = snapshot['rules']
            rules['weekly_streak_before'] = self.incoming(conn, row, 'weekly_streak_end', rules['weekly_streak_before'])
            previous = conn.execute('SELECT daily_streak_end FROM days WHERE player_id=? AND day_date=?',
                (row['player_id'], (date.fromisoformat(row['week_start']) - timedelta(days=1)).isoformat())).fetchone()
            if previous:
                rules['daily_streak_before'] = int(previous[0])
            result = score(snapshot, rules['weekly_streak_before'])
            for key in ('tasks_due', 'tasks_completed', 'task_xp', 'perfect_days', 'bonus_xp'):
                if result[key] != row[key]:
                    raise ValueError(f'El registro original no coincide con el resumen guardado ({key}: {result[key]} / {row[key]}).')
            daily = rules['daily_streak_before']
            for i, perfect in enumerate(result['perfect']):
                daily = daily + 1 if perfect else 0
                stored = conn.execute('SELECT perfect FROM days WHERE player_id=? AND day_date=?',
                    (row['player_id'], (date.fromisoformat(row['week_start']) + timedelta(days=i)).isoformat())).fetchone()
                if stored is not None and int(stored[0]) != perfect:
                    raise ValueError('Los días perfectos no coinciden con los días históricos. Revisa el registro original.')
            if daily != row['daily_streak_end']:
                raise ValueError('La racha diaria no coincide con el resumen original.')
            # Retain historical manual adjustments, including differences in rounding.
            rules['xp_adjustment'] += row['effective_xp'] - max(0, result['gross_effective'] - row['penalty_xp'])
            result = score(snapshot, rules['weekly_streak_before'])
            effective = max(0, result['gross_effective'] - row['penalty_xp'])
            goal = int(result['budget'] > 0 and effective * 100 >= result['budget'] * rules['goal_pct'])
            if goal != row['weekly_goal_achieved']:
                raise ValueError('El objetivo indicado no coincide con el resultado histórico. Revisa las reglas originales.')
            conn.execute('''INSERT INTO week_history(player_id,week_id,snapshot_json,revision,audit_json,updated_at)
                            VALUES(?,?,?,1,?,?)''', (row['player_id'], week_id, encoded(snapshot),
                            encoded([{'at': stamp(), 'operation': 'archive' if automatic else 'baseline',
                                      'message': 'Resumen conservado sin recalcular XP.'}]), stamp()))
        return self.load(week_id, db_key)

    def change(self, conn, week_id, db_key, revision, progress, runtime):
        row = self.week(conn, week_id, db_key)
        if revision != self.fingerprint(conn, row['player_id']):
            raise ValueError('El histórico ha cambiado. Recarga y vuelve a revisar la corrección.')
        detail = conn.execute('SELECT * FROM week_history WHERE week_id=?', (week_id,)).fetchone()
        if not detail:
            raise ValueError('Completa y valida primero el registro original de esta semana.')
        original = json.loads(detail['snapshot_json'])
        snapshot = deepcopy(original)
        if not isinstance(progress, dict) or set(progress) != {t['id'] for t in snapshot['tasks']}:
            raise ValueError('La corrección debe contener exactamente las tareas archivadas.')
        for task in snapshot['tasks']:
            task['progress'] = progress[task['id']]
        validate_snapshot(snapshot)
        all_weeks = [dict(w) for w in conn.execute('SELECT * FROM weeks WHERE player_id=? ORDER BY week_start', (row['player_id'],))]
        latest = all_weeks[-1]
        if runtime['last_applied_week'] != f"{latest['year']:04d}-W{latest['iso_week']:02d}":
            raise ValueError('Hay un cierre semanal pendiente de aplicar. Termínalo antes de corregir el histórico.')
        if snapshot == original:
            return {'ok': True, 'unchanged': True, 'changes': [], 'xp_delta': 0}, None
        old_total = sum(w['effective_xp'] for w in all_weeks)
        offset = runtime['points_total'] - old_total
        if offset < 0:
            raise ValueError('El XP vivo no coincide con el histórico. Revisa la sincronización antes de editar.')
        result = score(snapshot, snapshot['rules']['weekly_streak_before'])
        start = date.fromisoformat(row['week_start'])
        for affected in (w for w in all_weeks if w['week_start'] >= row['week_start']):
            saved = conn.execute('SELECT snapshot_json FROM week_history WHERE week_id=?', (affected['id'],)).fetchone()
            daily_snapshot = snapshot if affected['id'] == week_id else json.loads(saved[0]) if saved else None
            if daily_snapshot:
                for i, perfect in enumerate(score(daily_snapshot, 0)['perfect']):
                    day = date.fromisoformat(affected['week_start']) + timedelta(days=i)
                    iso = day.isocalendar()
                    conn.execute('''INSERT INTO days(player_id,day_date,year,iso_week,iso_weekday,perfect,closed_at,updated_at)
                      VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(player_id,day_date) DO UPDATE SET perfect=excluded.perfect,updated_at=excluded.updated_at''',
                        (row['player_id'], day.isoformat(), iso.year, iso.week, iso.weekday, perfect, stamp(), stamp()))
            elif conn.execute('SELECT COUNT(*) FROM days WHERE player_id=? AND day_date BETWEEN ? AND ?',
                    (row['player_id'], affected['week_start'], affected['week_end'])).fetchone()[0] != 7:
                raise ValueError(f"Completa el registro original de {affected['year']}-W{affected['iso_week']:02d} para recalcular sus rachas diarias.")
        previous = conn.execute('SELECT day_date,daily_streak_end FROM days WHERE player_id=? AND day_date<? ORDER BY day_date DESC LIMIT 1',
            (row['player_id'], row['week_start'])).fetchone()
        daily = int(previous['daily_streak_end']) if previous and date.fromisoformat(previous['day_date']) == start - timedelta(days=1) else snapshot['rules']['daily_streak_before']
        prev_day = start - timedelta(days=1)
        for day in conn.execute('SELECT * FROM days WHERE player_id=? AND day_date>=? ORDER BY day_date', (row['player_id'], row['week_start'])).fetchall():
            current = date.fromisoformat(day['day_date'])
            if current != prev_day + timedelta(days=1):
                # An unarchived gap has no known daily result: do not invent continuity.
                boundary = conn.execute('SELECT daily_streak_end FROM weeks WHERE player_id=? AND week_end=? AND week_end<?',
                    (row['player_id'], (current - timedelta(days=1)).isoformat(), row['week_start'])).fetchone()
                daily = int(boundary[0]) if boundary else 0
            daily = daily + 1 if day['perfect'] else 0
            conn.execute('UPDATE days SET daily_streak_end=?,updated_at=? WHERE id=?', (daily, stamp(), day['id']))
            prev_day = current
        total = offset
        changes, previous_week, weekly = [], None, 0
        for old in all_weeks:
            new = dict(old)
            if old['week_start'] < row['week_start']:
                total += old['effective_xp']; previous_week = old; weekly = old['weekly_streak_end']; continue
            if previous_week is None:
                weekly = snapshot['rules']['weekly_streak_before']
            elif date.fromisoformat(previous_week['week_end']) + timedelta(days=1) != date.fromisoformat(old['week_start']):
                weekly = 0
            saved = conn.execute('SELECT * FROM week_history WHERE week_id=?', (old['id'],)).fetchone()
            current_snapshot = snapshot if old['id'] == week_id else json.loads(saved['snapshot_json']) if saved else None
            original_incoming = self.incoming_from_list(all_weeks, old, current_snapshot)
            if current_snapshot is None and bool(weekly) != bool(original_incoming):
                raise ValueError(f"Completa el registro original de {old['year']}-W{old['iso_week']:02d} para recalcular su multiplicador.")
            if current_snapshot:
                stats = score(current_snapshot, weekly)
                for key in ('tasks_due', 'tasks_completed', 'task_xp', 'perfect_days', 'bonus_xp'):
                    new[key] = stats[key]
                new['completion_pct'] = round(100 * stats['tasks_completed'] / stats['tasks_due'], 2) if stats['tasks_due'] else 0
                new['effective_xp'] = max(0, stats['gross_effective'] - old['penalty_xp'])
                new['weekly_goal_achieved'] = int(stats['budget'] > 0 and new['effective_xp'] * 100 >= stats['budget'] * current_snapshot['rules']['goal_pct'])
            weekly = weekly + 1 if new['weekly_goal_achieved'] else 0
            new['weekly_streak_end'] = weekly
            sunday = conn.execute('SELECT daily_streak_end FROM days WHERE player_id=? AND day_date=?', (row['player_id'], old['week_end'])).fetchone()
            if sunday:
                new['daily_streak_end'] = int(sunday[0])
            new['level_start'], new['level_end'] = total // 500 + 1, (total + new['effective_xp']) // 500 + 1
            total += new['effective_xp']
            columns = ('tasks_due','tasks_completed','completion_pct','task_xp','perfect_days','bonus_xp','effective_xp',
                       'weekly_goal_achieved','weekly_streak_end','daily_streak_end','level_start','level_end')
            conn.execute('UPDATE weeks SET ' + ','.join(k+'=?' for k in columns) + ' WHERE id=?', [new[k] for k in columns] + [old['id']])
            if any(old[k] != new[k] for k in columns):
                changes.append({'before': old, 'after': new, 'reward': current_snapshot['rules']['reward'] if current_snapshot else None,
                                'reward_earned': bool(new['weekly_goal_achieved']),
                                'multiplier': stats['multiplier'] if current_snapshot else None})
            previous_week = new
        for year in {w['year'] for w in all_weeks if w['week_start'] >= row['week_start']}:
            self.db_module.rebuild_year_summary(conn, row['player_id'], year)
        helpers = {'points_total': total, 'streak_weeks': weekly, 'streak_days': daily}
        return {'ok': True, 'unchanged': False, 'changes': changes, 'xp_delta': total - runtime['points_total'],
                'helpers': helpers, 'snapshot': snapshot}, (row, detail)

    @staticmethod
    def incoming_from_list(weeks, row, snapshot):
        before = (date.fromisoformat(row['week_start']) - timedelta(days=1)).isoformat()
        previous = next((w for w in weeks if w['week_end'] == before), None)
        if previous:
            return previous['weekly_streak_end']
        return snapshot['rules']['weekly_streak_before'] if snapshot else max(0, row['weekly_streak_end'] - 1)

    def preview(self, week_id, db_key, revision, progress, runtime):
        with closing(self.connect()) as conn:
            conn.execute('BEGIN')
            try:
                result, _ = self.change(conn, week_id, db_key, revision, progress, runtime)
                return result
            finally:
                conn.rollback()

    def apply(self, week_id, db_key, revision, progress, runtime, reason, pending):
        if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 500:
            raise ValueError('Explica la corrección (entre 3 y 500 caracteres).')
        with closing(self.connect()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            result, context = self.change(conn, week_id, db_key, revision, progress, runtime)
            if result['unchanged']:
                return result
            row, detail = context
            audit = json.loads(detail['audit_json'])
            audit.append({'at': stamp(), 'operation': 'edit', 'reason': reason.strip(),
                          'before': json.loads(detail['snapshot_json']), 'after': result['snapshot'],
                          'changes': result['changes'], 'xp_delta': result['xp_delta']})
            conn.execute('UPDATE week_history SET snapshot_json=?,revision=revision+1,audit_json=?,updated_at=? WHERE week_id=?',
                (encoded(result['snapshot']), encoded(audit), stamp(), week_id))
            closed_xp = conn.execute('SELECT COALESCE(SUM(effective_xp),0) FROM weeks WHERE player_id=?', (row['player_id'],)).fetchone()[0]
            sync = {**pending, 'values': result['helpers'], 'xp_offset': result['helpers']['points_total'] - closed_xp}
            conn.execute('''INSERT INTO history_sync(player_id,helpers_json,updated_at) VALUES(?,?,?)
                ON CONFLICT(player_id) DO UPDATE SET helpers_json=excluded.helpers_json,updated_at=excluded.updated_at''',
                (row['player_id'], encoded(sync), stamp()))
            return result

    def pending(self):
        with closing(self.connect()) as conn, conn:
            self.schema(conn)
            return [dict(r, data=json.loads(r['helpers_json'])) for r in conn.execute('SELECT * FROM history_sync ORDER BY id')]

    def acknowledge(self, pending_id):
        with closing(self.connect()) as conn, conn:
            conn.execute('DELETE FROM history_sync WHERE id=?', (pending_id,))

    def recovery_values(self, pending):
        # If HA crashed after resuming but before clearing the journal, later
        # closures may already exist. Rebuild from SQLite rather than replaying
        # an old streak or overwriting newer lifetime XP.
        with closing(self.connect()) as conn, conn:
            conn.execute('BEGIN')
            player = pending['player_id']
            total = conn.execute('SELECT COALESCE(SUM(effective_xp),0) FROM weeks WHERE player_id=?', (player,)).fetchone()[0]
            last = conn.execute('SELECT weekly_streak_end FROM weeks WHERE player_id=? ORDER BY week_start DESC LIMIT 1', (player,)).fetchone()
            day = conn.execute('SELECT daily_streak_end FROM days WHERE player_id=? ORDER BY day_date DESC LIMIT 1', (player,)).fetchone()
            if last is None or day is None:
                raise ValueError('Falta el histórico necesario para recuperar el progreso.')
            return {'points_total': total + pending['data']['xp_offset'],
                    'streak_weeks': last[0], 'streak_days': day[0]}
