"""Validate/freeze a study plan without running simulations or API calls."""
import argparse
import hashlib
import json
from pathlib import Path


def validate(plan):
    if plan.get('schema') != 'agent-study-plan-v1' or plan.get('horizon', 0) <= 0:
        raise ValueError('A positive common horizon is required')
    if not plan.get('model') or plan.get('promptVersion') != 'paper-agent-v5':
        raise ValueError('Fix model and supported prompt version')
    groups = [plan.get(k, []) for k in ('developmentSeeds', 'calibrationSeeds', 'testSeeds')]
    if any(not group or any(type(seed) is not int for seed in group) or len(set(group)) != len(group) for group in groups):
        raise ValueError('Each split needs unique integer seeds')
    if any(set(groups[a]) & set(groups[b]) for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError('Seed splits overlap')
    if not plan.get('conditionKeys') or any(not isinstance(k, str) or not k for k in plan['conditionKeys']):
        raise ValueError('Export physical condition keys from Unity first')
    if set(plan.get('informationConditions', [])) != {'Core', 'SharedContext'}:
        raise ValueError('Include Core and SharedContext')
    if not {'OriginalGameTheory', 'LLM', 'MockHeuristic', 'RandomMatched'} <= set(plan.get('policies', [])):
        raise ValueError('All four controls are required')
    if not plan.get('primaryContrast') or not plan.get('multiplicityTreatment'):
        raise ValueError('Fix primary contrast and multiplicity treatment')


def freeze(plan, root):
    validate(plan)
    root = Path(root).resolve()
    files = sorted((root/'Assets/scripts').rglob('*.cs'))
    files += sorted((root/'Assets/Scenes').glob('*.unity'))
    files += sorted((root/'tools').glob('*.py'))
    files += [root/'Packages/manifest.json', root/'ProjectSettings/ProjectVersion.txt', root/'RESEARCH_PROTOCOL.zh-TW.md']
    calibrations = plan.get('calibrationFiles', [])
    if not calibrations:
        raise ValueError('List the frozen calibration files before locking final tests')
    covered = set()
    for name in calibrations:
        path = (root/name).resolve()
        if not path.is_relative_to(root) or path.suffix != '.json':
            raise ValueError('Calibration files must be project-local JSON files')
        calibration = json.loads(path.read_text(encoding='utf-8-sig'))
        if (calibration.get('schema') != 'cooperation-calibration-v1' or calibration.get('conditionKey') not in plan['conditionKeys']
                or calibration.get('model') != plan['model'] or calibration.get('promptVersion') != plan['promptVersion']):
            raise ValueError('Calibration is not for a planned condition')
        if not set(calibration['seeds']) <= set(plan['calibrationSeeds']):
            raise ValueError('Calibration provenance is outside the declared calibration split')
        if set(calibration['seeds']) & set(plan['testSeeds']):
            raise ValueError('Calibration and test seeds overlap')
        files.append(path)
        covered.add((calibration['conditionKey'], calibration['informationCondition']))
    if not {(key, info) for key in plan['conditionKeys'] for info in plan['informationConditions']} <= covered:
        raise ValueError('Missing calibration for a planned condition/information setting')
    plan = dict(plan, locked=True)
    plan['sourceFiles'] = [dict(path=p.relative_to(root).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    plan['planID'] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft', type=Path)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Locked plans are immutable; choose a new output')
    try:
        plan = freeze(json.loads(args.draft.read_text(encoding='utf-8-sig')), args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
