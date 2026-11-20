"""Archive existing test artifacts by purpose; never runs simulations or reads credentials."""
import csv
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT/'experiment_records'
DATA = RECORDS/'data'


def native(path):
    """Do not silently omit >260-character archived paths on Windows."""
    absolute=Path(path).resolve()
    return Path('\\\\?\\'+str(absolute)) if os.name=='nt' else absolute


def files_under(path):
    return [p for p in native(path).rglob('*') if p.is_file()]


def sha(path):
    result=hashlib.sha256()
    with native(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def rows(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def checked_move(source, destination, manifest):
    source, destination = source.resolve(), destination.resolve()
    if not source.is_relative_to(ROOT) or not destination.is_relative_to(DATA.resolve()):
        raise ValueError('Move outside project/data directory refused')
    if source.is_dir():
        if destination.exists():
            raise FileExistsError(destination)
        files = files_under(source)
        entry = dict(source=str(source.relative_to(ROOT)), destination=str(destination.relative_to(ROOT)),
                     files=len(files), bytes=sum(p.stat().st_size for p in files), verification='same-volume directory rename; historical internal manifest preserved')
    else:
        checksum = sha(source)
        if destination.exists():
            if sha(destination) == checksum:
                raise FileExistsError(f'Artifact already archived: {destination}')
            raise FileExistsError(f'Different existing artifact: {destination}')
        entry = dict(source=str(source.relative_to(ROOT)), destination=str(destination.relative_to(ROOT)),
                     files=1, bytes=source.stat().st_size, sha256=checksum)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    if 'sha256' in entry and sha(destination) != entry['sha256']:
        raise ValueError('Post-move checksum mismatch')
    manifest.append(entry)


def classify(config_path):
    prefix = str(config_path)[:-len('_config.json')]
    totals = rows(Path(prefix+'_global.csv'))
    total = totals[0] if totals else {}
    termination = total.get('Termination', 'incomplete')
    if termination.startswith('invalid_llm_'):
        return 'api_connectivity_and_credentials'
    if int(total.get('ApiRequests', 0)) > 0:
        return 'llm_decision_behavior_random_room'
    return 'recruitment_trigger_random_room'


def summarize(path, purpose):
    c = json.loads(path.read_text(encoding='utf-8-sig'))
    prefix = str(path)[:-len('_config.json')]
    global_rows = rows(Path(prefix+'_global.csv'))
    g = global_rows[0] if global_rows else {}
    decisions = rows(Path(prefix+'_llm_decisions.csv'))
    paper = rows(Path(prefix+'_paper_decisions.csv'))
    events = rows(Path(prefix+'_obstacle_events.csv'))
    actions = Counter(r['Action'] for r in events)
    choices = Counter(r['Decision'] for r in decisions)
    initial_agents = [r for r in rows(Path(prefix+'_trajectories.csv')) if r['Step']=='0']
    initial_obstacles = [r for r in rows(Path(prefix+'_obstacles.csv')) if r['Step']=='0']
    # Hash normalized initial records to check equality across policies.
    initial_hash = hashlib.sha256(json.dumps([initial_agents, initial_obstacles], sort_keys=True).encode()).hexdigest()
    return dict(record_id=path.name[:-len('_config.json')], purpose=purpose,
                data_directory=str(path.parent.relative_to(RECORDS)), scenario=c.get('scenario'), policy=c.get('volunteerPolicy'),
                seed=c.get('seed'), agents=c.get('actualAgents'), obstacles=c.get('actualObstacles'),
                configured_horizon=c.get('maxSteps'), stop_step=g.get('TotalSteps'), termination=g.get('Termination'),
                evacuated=g.get('EvacuatedCount'), t100_steps=g.get('TotalSteps') if g.get('Termination')=='completed' else '',
                api_logical_calls=g.get('ApiRequests', 0), willing_decisions=sum(r['Willing'].lower()=='true' for r in paper),
                refusal_decisions=choices.get('selfish', 0), activations=actions['activate'], settled=actions['settle'],
                push=actions['push'], pull=actions['pull'], rotate=actions['rotate'],
                initial_state_sha256=initial_hash, condition_key=c.get('conditionKey', ''),
                interpretation='Functional/development record; not a final research replicate')


def main():
    RECORDS.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    manifest = []
    assignments = []
    # Preserve each full run prefix and Unity .meta sidecars.
    for config in sorted((ROOT/'Assets/data').glob('*_config.json')):
        purpose = classify(config)
        stem = config.name[:-len('_config.json')]
        destination = DATA/'development'/purpose/stem
        for source in sorted(config.parent.glob(stem+'_*')):
            if source.is_file():
                checked_move(source, destination/source.name, manifest)
        assignments.append((destination/config.name, purpose))
    for source_name, purpose in [('llm-smoke-tests', 'blocked_exit_llm'),
                                 ('game-theory-smoke-tests', 'blocked_exit_game_theory'),
                                 ('no-volunteers-smoke-tests', 'blocked_exit_no_volunteers')]:
        parent = ROOT/'tmp'/source_name
        if parent.exists():
            for source in sorted(parent.iterdir()):
                if not source.is_dir():
                    continue
                destination = DATA/'functional_comparison'/purpose/source.name
                checked_move(source, destination, manifest)
                assignments.extend((p, purpose) for p in destination.glob('*_config.json'))
    legacy = ROOT/'archived_results/2026-11-09_before_redesign'
    if legacy.exists():
        checked_move(legacy, DATA/'historical_archive/2026-11-09_before_redesign', manifest)
    # Current validation and launcher logs: local data only, never tracked or printed.
    for name in ['agent-contract.log', 'menu-validation.log', 'volunteer-flow.log',
                 'llm-live-smoke.log', 'game-theory-smoke.log', 'no-volunteers-smoke.log']:
        source = ROOT/'tmp'/name
        if source.exists():
            checked_move(source, DATA/'validation'/name, manifest)
    source = ROOT/'tmp/completion-project/tmp/menu-validation'
    if source.exists():
        checked_move(source, DATA/'validation/menu-validation', manifest)
    catalog = [summarize(path, purpose) for path, purpose in assignments]
    catalog_path = RECORDS/'RUN_CATALOG.csv'
    if catalog_path.exists():
        previous = {row['record_id']: row for row in rows(catalog_path)}
        for row in catalog:
            previous.setdefault(row['record_id'], row)
        catalog = list(previous.values())
    if catalog:
        with catalog_path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(catalog[0]))
            writer.writeheader(); writer.writerows(catalog)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    manifest_path = RECORDS/('relocation_manifest_'+stamp+'.json')
    manifest_path.write_text(json.dumps(dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), moves=manifest),
                                        ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(catalog_runs=len(catalog), moved_entries=len(manifest),
                          moved_files=sum(m['files'] for m in manifest),
                          moved_bytes=sum(m['bytes'] for m in manifest),manifest=str(manifest_path.relative_to(ROOT)))))


if __name__ == '__main__':
    main()
