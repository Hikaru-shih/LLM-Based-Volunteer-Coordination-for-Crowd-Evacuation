"""Audited, descriptive P3 analysis of one fixed-state sampling run. No network/Unity."""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from individual_sampling import probability, wilson

VERSION = 'individual-analysis-v1'
FACTORS = ('nearbyAgentCount', 'exitNonBlockage', 'volunteerCost', 'failureCost', 'unwillingness')
LABELS = dict(zip(FACTORS, ('Player count X', 'Unblocked fraction tau', 'Help cost cv', 'No-help loss av', 'Coefficient omega')))
SYSTEM = 'You represent one pedestrian making a personal participation decision in a simulated evacuation. Respond with strict JSON only.'
PLAN_KEYS = {'schema', 'purpose', 'model', 'promptVersion', 'repetitions', 'orderSeed', 'maxHttpAttempts', 'scenarios'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, f'Duplicate JSON key: {k}')
            result[k] = v
        return result
    def constant(value):
        raise ValueError(f'Non-finite JSON: {value}')
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    def visit(v):
        if isinstance(v, str):
            v.encode('utf-8')  # Reject unpaired surrogate escapes, as the runtime does.
        elif isinstance(v, float):
            require(math.isfinite(v), 'Non-finite JSON number')
        elif isinstance(v, dict):
            for k, child in v.items():
                visit(k)
                visit(child)
        elif isinstance(v, list):
            for child in v:
                visit(child)
    visit(value)
    return value


def read(path):
    return strict_json(path.read_text(encoding='utf-8-sig'))


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def kind(s):
    if s['nearbyAgentCount'] == 0 or s['exitNonBlockage'] == 1:
        return 'NoGame'
    return 'ReferenceBoundary' if s['nearbyAgentCount'] == 1 else 'Choice'


def validate_plan(p):
    require(isinstance(p, dict) and set(p) == PLAN_KEYS, 'Unsupported/missing plan fields')
    require(p['schema'] == 'individual-sampling-v1' and p['promptVersion'] == 'paper-agent-v5', 'Unsupported plan/prompt version')
    require(all(isinstance(p[k], str) and p[k].strip() for k in ('purpose', 'model')), 'Missing purpose/model')
    require(type(p['repetitions']) is int and 1 <= p['repetitions'] <= 10000, 'Invalid repetitions')
    require(type(p['orderSeed']) is int and -(2**31) <= p['orderSeed'] < 2**31, 'Invalid order seed')
    require(type(p['maxHttpAttempts']) is int and 0 <= p['maxHttpAttempts'] < 2**31, 'Invalid HTTP cap')
    require(isinstance(p['scenarios'], list) and 0 < len(p['scenarios'])*p['repetitions'] <= 100000, 'Invalid scenario count')
    ids, states = set(), set()
    for s in p['scenarios']:
        require(isinstance(s, dict) and set(s) == {'id', *FACTORS}, 'Invalid scenario fields')
        require(isinstance(s['id'], str) and s['id'].strip() and s['id'] not in ids, 'Duplicate/empty scenario ID')
        ids.add(s['id'])
        require(type(s['nearbyAgentCount']) is int and 0 <= s['nearbyAgentCount'] < 2**31, 'Invalid X')
        require(all(number(s[k]) for k in FACTORS), 'Invalid scenario number')
        require(0 <= s['exitNonBlockage'] <= 1 and 0 < s['volunteerCost'] < s['failureCost'] < 1 and s['unwillingness'] >= 0, 'Invalid scenario domain')
        state = tuple(s[k] for k in FACTORS)
        require(state not in states, 'Duplicate states: combine repeats in one scenario instead of ambiguous scenario IDs')
        states.add(state)


def answer(raw):
    """Revalidate the personal protocol; do not salvage invalid content."""
    try:
        root = strict_json(raw)
        require(isinstance(root, dict), 'envelope')
        choices = root.get('choices')
        require(isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict), 'choices')
        choice = choices[0]
        msg = choice.get('message')
        require(isinstance(msg, dict) and msg.get('role') == 'assistant', 'role')
        refusal = msg.get('refusal')
        require(refusal is None or isinstance(refusal, str) and not refusal, 'refusal')
        require(choice.get('finish_reason') == 'stop', 'finish')
        tools = msg.get('tool_calls')
        require(tools is None or isinstance(tools, list) and not tools, 'tools')
        content = msg.get('content')
        require(isinstance(content, str) and content.strip() and len(content) <= 262144, 'content')
        body = strict_json(content)
        require(isinstance(body, dict) and set(body) == {'decision', 'explanation'}, 'fields')
        require(body['decision'] in ('participate', 'decline_assistance') and isinstance(body['explanation'], str), 'action')
        return body, root
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None, None


def validate_payload(text, observation, model, instructions):
    p = strict_json(text)
    luna = model == 'gpt-6-luna'
    token_key = 'max_completion_tokens' if luna else 'max_tokens'
    fields = {'model', 'messages', 'temperature', token_key, 'response_format'} | ({'reasoning_effort'} if luna else set())
    require(isinstance(p, dict) and set(p) == fields, 'Unexpected request fields')
    require(not luna or p['reasoning_effort'] == 'none', 'Changed Luna reasoning profile')
    require(p['model'] == model and number(p['temperature']) and math.isclose(p['temperature'], .15, abs_tol=1e-7) and type(p[token_key]) is int and p[token_key] == 220, 'Mixed request configuration')
    require(p['messages'] == [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': instructions+'Observation:\n'+observation}], 'Changed prompt/history/observation')
    candidates = {
        'paper-choice-response-v1': {'type': 'object', 'properties': {'decision': {'type': 'string', 'enum': ['participate', 'decline_assistance']}, 'explanation': {'type': 'string'}}, 'required': ['decision', 'explanation'], 'additionalProperties': False},
        'paper-choice-response-v3': {'type': 'object', 'properties': {'explanation': {'type': 'string'}, 'decision': {'type': 'string'}}, 'required': ['explanation', 'decision'], 'additionalProperties': False}}
    for protocol, schema in candidates.items():
        expected = {'type': 'json_schema', 'json_schema': {'name': 'paper_individual_choice', 'strict': True, 'schema': schema}}
        if p['response_format'] == expected and list(p['response_format']['json_schema']['schema']['properties']) == list(schema['properties']):
            return protocol
    raise ValueError('Response schema mismatch')



def audit(folder, allow_synthetic=False):
    folder = Path(folder).resolve()
    p = read(folder/'plan.json')
    validate_plan(p)
    instructions = (folder/'instructions.txt').read_text(encoding='utf-8-sig')
    require(instructions.startswith('Task specification: paper-agent-v5; information condition: Core.'), 'Expected Core v5 instruction snapshot')
    source = (folder/'source.sha256').read_text(encoding='utf-8-sig').strip()
    require(len(source) == 64 and all(c in '0123456789abcdef' for c in source), 'Missing source hash')
    ledger = read(folder/'ledger.json')
    formal=None
    if p['purpose'].startswith('Formal:'):
        from formal_sampling import verify as verify_lock
        formal=verify_lock(folder/'study_lock')
        locked_plan=read(folder/'study_lock/plan.json')
        require(ledger.get('formalLockID')==formal['lockID'],'Missing/mismatched formal provenance')
        require(all(p[k]==locked_plan[k] for k in PLAN_KEYS-{'scenarios'}) and len(p['scenarios'])==len(locked_plan['scenarios']),'Formal plan metadata changed')
        for a,b in zip(p['scenarios'],locked_plan['scenarios']):
            require(a['id']==b['id'] and all(math.isclose(a[f],b[f],rel_tol=2e-7,abs_tol=1e-9) for f in FACTORS),'Formal state changed')
    mode = ledger.get('executionMode')
    require(mode in ('api', 'synthetic_test'), 'Missing execution provenance')
    require(allow_synthetic or mode != 'synthetic_test', 'Synthetic run: --allow-synthetic is validation only')
    reserved = ledger.get('reservedAttempts')
    require(type(reserved) is int and 0 <= reserved <= p['maxHttpAttempts'] and reserved % 3 == 0, 'Invalid reservation ledger')
    require(isinstance(ledger.get('binding'), str) and len(ledger['binding']) == 64, 'Missing run binding')
    trials, trace_rows, errors = {}, [], Counter()
    response_protocols = set()
    interruptions = []
    ipath = folder/'interruptions.jsonl'
    if ipath.exists():
        for line in ipath.read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                t = strict_json(line)
                require(t.get('execution') == 'interrupted_unknown_result' and type(t.get('index')) is int and 0 <= t['index'] < len(p['scenarios'])*p['repetitions'], 'Invalid interruption record')
                interruptions.append(t)
    for path in sorted((folder/'trials').glob('*.json')):
        t = read(path)
        i = t.get('index')
        require(type(i) is int and 0 <= i < len(p['scenarios'])*p['repetitions'] and i not in trials and path.name == f'{i:06d}.json', 'Invalid/duplicate trial index')
        s = p['scenarios'][i//p['repetitions']]
        obs = {k: s[k] for k in FACTORS}
        require(t.get('scenario') == s['id'] and type(t.get('repetition')) is int and t['repetition'] == i % p['repetitions'], 'Trial identity mismatch')
        require(strict_json(t.get('observation', '')) == obs and t.get('kind') == kind(s), 'Observation/boundary mismatch')
        require(number(t.get('referenceProbability')) and math.isclose(t['referenceProbability'], probability(s), abs_tol=2e-6), 'Incorrect reference probability')
        require(type(t.get('valid')) is bool and type(t.get('willing')) is bool, 'Choice flags must be boolean')
        if formal:require(t.get('studyLockID')==formal['lockID'],'Trial lacks formal lock provenance')
        require(type(t.get('attempts')) is int and 0 <= t['attempts'] <= 3 and number(t.get('elapsedSeconds')) and t['elapsedSeconds'] >= 0, 'Invalid attempt/duration audit')
        require(isinstance(t.get('attemptAudit'), list) and len(t['attemptAudit']) == t['attempts'], 'Missing per-attempt audit')
        for seq, attempt in enumerate(t['attemptAudit'],1):
            require(isinstance(attempt,dict) and type(attempt.get('attempt')) is int and attempt['attempt']==seq and type(attempt.get('status')) is int and isinstance(attempt.get('error'),str) and number(attempt.get('elapsedSeconds')) and attempt['elapsedSeconds']>=0, 'Malformed attempt audit')
        tokens = None
        provider_model = None
        if kind(s) == 'NoGame':
            require(t['execution'] == 'no_game' and not t['valid'] and not t['willing'] and not t.get('payload') and not t.get('response') and not t.get('error') and t['attempts'] == 0, 'No-game treated as a choice')
        else:
            require(t['execution'] == ('synthetic_test' if mode == 'synthetic_test' else 'live'), 'Mixed execution modes')
            if mode == 'synthetic_test':
                require(t['attempts'] == 0, 'Synthetic transport reported HTTP calls')
            else:
                require(t['attempts'] >= 1, 'API choice without recorded HTTP attempts')
            protocol = validate_payload(t.get('payload', ''), t['observation'], p['model'], instructions)
            response_protocols.add(protocol)
            require(len(response_protocols)==1, 'Mixed response protocols')
            if formal:
                declared=read(folder/'study_lock/design.json').get('transport',{}).get('responseProtocol','paper-choice-response-v1')
                require(protocol==declared, 'Response protocol differs from formal design')
            body, envelope = answer(t.get('response', ''))
            if t['valid']:
                require(body is not None and t['willing'] == (body['decision'] == 'participate') and t.get('explanation') == body['explanation'] and not t.get('error'), 'Valid choice does not match raw response')
            else:
                drift=formal and t.get('error')=='provider_model_drift' and envelope and envelope.get('model')!=formal['expectedProviderModel']
                require((body is None or drift) and isinstance(t.get('error'), str) and t['error'], 'Invalid record lacks failure or contains a valid answer')
                errors[t['error']] += 1
            if envelope:
                provider_model=envelope.get('model') if isinstance(envelope.get('model'),str) else None
                usage = envelope.get('usage')
                if isinstance(usage, dict) and type(usage.get('total_tokens')) is int and usage['total_tokens'] >= 0:
                    tokens = usage['total_tokens']
        trials[i] = t
        trace_rows.append(dict(index=i, scenario=s['id'], repetition=t['repetition'], stratum=kind(s), execution=t['execution'], valid=t['valid'],
                               willing=t['willing'] if t['valid'] else None, error=t.get('error', ''), attempts=t['attempts'], elapsed_seconds=t['elapsedSeconds'],
                               provider_model=provider_model,provider_total_tokens=tokens, raw_file='input_snapshot/trials/'+path.name, raw_sha256=digest(path)))
    provider_models=sorted({r['provider_model'] for r in trace_rows if r['provider_model'] and r['valid']})
    require(len(provider_models)<=1,'Multiple provider model identifiers in one run; do not pool a drifting run')
    if formal:require(not provider_models or provider_models==[formal['expectedProviderModel']],'Formal provider version changed')
    eligible_saved = sum(t['kind'] != 'NoGame' for t in trials.values())
    require(reserved >= 3*(eligible_saved+len(interruptions)), 'Reservation ledger cannot account for saved/interrupted dispatches')
    rows = []
    for index, s in enumerate(p['scenarios']):
        saved = [trials[i] for i in range(index*p['repetitions'], (index+1)*p['repetitions']) if i in trials]
        valid = [t for t in saved if t['valid']]
        n, k = len(valid), sum(t['willing'] for t in valid)
        low, high = wilson(k, n)
        ref, rate = probability(s), k/n if n else None
        invalid = sum(t['kind'] != 'NoGame' and not t['valid'] for t in saved)
        missing = p['repetitions']-len(saved)
        eligible = kind(s) != 'NoGame'
        rows.append(dict(scenario=s['id'], stratum=kind(s), **{f:s[f] for f in FACTORS}, planned=p['repetitions'], saved=len(saved), missing=missing,
                         no_game=sum(t['kind']=='NoGame' for t in saved), invalid=invalid, valid=n, willing=k, rate=rate, wilson95_low=low, wilson95_high=high,
                         reference_probability=ref, difference=None if rate is None else rate-ref,
                         difference95_low=None if low is None else low-ref, difference95_high=None if high is None else high-ref,
                         unresolved_lower=k/p['repetitions'] if eligible else None, unresolved_upper=(k+invalid+missing)/p['repetitions'] if eligible else None,
                         http_attempts=sum(t['attempts'] for t in saved), provider_tokens_known=sum(r['provider_total_tokens'] or 0 for r in trace_rows if r['scenario']==s['id']),
                         usage_records=sum(r['provider_total_tokens'] is not None for r in trace_rows if r['scenario']==s['id']), synthetic_validation=mode=='synthetic_test'))
    files = [folder/n for n in ('plan.json', 'ledger.json', 'instructions.txt', 'source.sha256')]
    files += [f for f in (folder/'progress.json', ipath) if f.exists()]
    files += sorted((folder/'trials').glob('*.json'))
    if formal:files+=sorted(f for f in (folder/'study_lock').rglob('*') if f.is_file())
    hashes = {f.relative_to(folder).as_posix(): digest(f) for f in files}
    return dict(plan=p, rows=rows, trace=trace_rows, errors=errors, interruptions=interruptions, reserved=reserved, mode=mode, files=files, hashes=hashes, source=source,providerModels=provider_models,formalLockID=formal['lockID'] if formal else None)


def curves(rows):
    result = []
    for factor in FACTORS:
        groups = defaultdict(list)
        for row in rows:
            if row['stratum'] != 'NoGame':
                groups[(row['stratum'], *(row[f] for f in FACTORS if f != factor))].append(row)
        for key, points in sorted(groups.items()):
            if len(points) >= 2:
                result.append(dict(id=f'{factor}_{len(result)+1:03d}', factor=factor, stratum=key[0],
                                   fixed={f:points[0][f] for f in FACTORS if f != factor}, points=sorted(points, key=lambda r:r[factor])))
    return result


def contrasts(groups):
    rows = []
    for group in groups:
        for a, b in zip(group['points'], group['points'][1:]):
            valid = bool(a['valid'] and b['valid'])
            delta = b['rate']-a['rate'] if valid else None
            low = delta-math.hypot(b['rate']-b['wilson95_low'], a['wilson95_high']-a['rate']) if valid else None
            high = delta+math.hypot(b['wilson95_high']-b['rate'], a['rate']-a['wilson95_low']) if valid else None
            baseline = b['reference_probability']-a['reference_probability']
            rows.append(dict(curve=group['id'], factor=group['factor'], stratum=group['stratum'], scenario_a=a['scenario'], scenario_b=b['scenario'],
                             value_a=a[group['factor']], value_b=b[group['factor']], n_a=a['valid'], n_b=b['valid'], missing_a=a['missing'], missing_b=b['missing'],
                             invalid_a=a['invalid'], invalid_b=b['invalid'], observed_change=delta, change95_low=low, change95_high=high,
                             reference_change=baseline, response_deviation=None if delta is None else delta-baseline,
                             deviation95_low=None if low is None else low-baseline, deviation95_high=None if high is None else high-baseline))
    return rows


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def write_csv(path, rows, fields=None):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plots(data, groups, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': VERSION})
    mark = 'SYNTHETIC VALIDATION — NOT MODEL RESULTS' if data['mode']=='synthetic_test' else 'DESCRIPTIVE MODEL OUTPUTS — NOT HUMAN DATA'
    paths = []
    def save(fig, name):
        fig.text(.5, .015, mark, ha='center', fontsize=9, color='#9a3412')
        fig.tight_layout(rect=(0,.05,1,.97))
        for extension in ('png', 'pdf'):
            path = output/(name+'.'+extension)
            fig.savefig(path, dpi=160, metadata={'CreationDate': None} if extension=='pdf' else None)
            paths.append(path.name)
        plt.close(fig)
    for group in groups:
        points = group['points']
        x = [r[group['factor']] for r in points]
        y = [r['rate'] if r['rate'] is not None else float('nan') for r in points]
        ref = [r['reference_probability'] for r in points]
        fig, axes = plt.subplots(2,1,figsize=(8.6,7),sharex=True)
        # The single-player reference jumps at tau=0; never interpolate that branch.
        axes[0].plot(x,ref,'s' if group['stratum']=='ReferenceBoundary' else 's--',color='#334155',label='Original model (sampled levels)',markersize=4)
        axes[0].plot(x,y,'o-',color='#2563eb',label='Valid choices (95% Wilson)')
        for pos, row in zip(x, points):
            if row['rate'] is not None:
                axes[0].errorbar(pos,row['rate'],yerr=[[row['rate']-row['wilson95_low']],[row['wilson95_high']-row['rate']]],fmt='none',color='#2563eb',capsize=4)
                axes[1].errorbar(pos,row['difference'],yerr=[[row['difference']-row['difference95_low']],[row['difference95_high']-row['difference']]],fmt='o',color='#2563eb',capsize=4)
            axes[0].annotate(f"n={row['valid']}/{row['planned']}", (pos,.02),xycoords=('data','axes fraction'),ha='center',fontsize=8)
        axes[1].axhline(0,color='#64748b',linestyle='--')
        axes[0].set_ylim(-.08,1.08)
        axes[1].set_ylim(-1.08,1.08)
        axes[0].set_ylabel('Participation probability')
        axes[1].set_ylabel('Observed minus reference')
        axes[1].set_xlabel(LABELS[group['factor']])
        if len(x)<=12:axes[1].set_xticks(x)
        fixed=', '.join(f'{k}={v:g}' for k,v in group['fixed'].items())
        axes[0].set_title(group['stratum']+' | '+LABELS[group['factor']]+'\n'+fixed,fontsize=10)
        axes[0].legend(loc='best')
        for ax in axes:ax.grid(alpha=.2)
        save(fig,group['id'])
    for page, start in enumerate(range(0,len(data['rows']),18),1):
        rows=data['rows'][start:start+18]
        fig, ax=plt.subplots(figsize=(10,max(3.8,len(rows)*.4+1.6)))
        left=[0]*len(rows)
        for key,color in [('valid','#2563eb'),('invalid','#dc2626'),('missing','#d97706'),('no_game','#94a3b8')]:
            values=[r[key] for r in rows]
            ax.barh(range(len(rows)),values,left=left,label=key,color=color)
            left=[a+b for a,b in zip(left,values)]
        ax.set_yticks(range(len(rows)),[r['scenario'][:42] for r in rows]);ax.invert_yaxis()
        ax.set_xlabel('Planned trials (no-game is not a model refusal)');ax.set_title('Data completeness');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.15),ncol=4)
        save(fig,f'quality_{page:02d}')
    for stratum in ('ReferenceBoundary','Choice'):
        rows=[r for r in data['rows'] if r['stratum']==stratum]
        for page,start in enumerate(range(0,len(rows),18),1):
            points=rows[start:start+18]
            fig,ax=plt.subplots(figsize=(9,max(3.8,len(points)*.4+1.6)))
            for i,row in enumerate(points):
                ax.plot([row['unresolved_lower']-row['reference_probability'],row['unresolved_upper']-row['reference_probability']],[i,i],color='#cbd5e1',lw=7)
                if row['rate'] is not None:
                    ax.errorbar(row['difference'],i,xerr=[[row['difference']-row['difference95_low']],[row['difference95_high']-row['difference']]],fmt='o',color='#2563eb',capsize=3)
            ax.axvline(0,color='#64748b',linestyle='--');ax.set_xlim(-1.08,1.08)
            ax.set_yticks(range(len(points)),[r['scenario'][:42] for r in points]);ax.invert_yaxis()
            ax.set_xlabel('Observed minus reference');ax.set_title(stratum+' | blue: conditional 95% interval; gray: unresolved-outcome bounds',fontsize=10)
            save(fig,f'differences_{stratum}_{page:02d}')
    return paths, matplotlib.__version__


def report(data, groups, changes, images):
    p, rows = data['plan'], data['rows']
    total = sum(r['planned'] for r in rows)
    counts = {k:sum(r[k] for r in rows) for k in ('valid','invalid','missing','no_game','http_attempts')}
    mode = 'SYNTHETIC VALIDATION — NOT MODEL RESULTS' if data['mode']=='synthetic_test' else 'Descriptive model-output analysis'
    lines = ['# Fixed-state individual decision analysis', '', '**'+mode+'**', '',
             f"Model requested: `{p['model']}`. Provider identifiers observed: {', '.join(data['providerModels']) or 'not supplied'}. Prompt: `{p['promptVersion']}`. Information: Core. Source: `{data['source']}`.", '',
             f"Purpose: {p['purpose']}", '', f"Planned trials: {total}; valid choices: {counts['valid']}; invalid: {counts['invalid']}; missing: {counts['missing']}; saved no-game controls: {counts['no_game']}.", '',
             f"Completed-record HTTP attempts: {counts['http_attempts']}; reserved attempts: {data['reserved']}; interrupted unknown-result dispatches: {len(data['interruptions'])}. Reservations are not actual calls or monetary cost. Interruptions may have incurred extra calls; inspect their raw audits.", '',
             '## Scenario estimates', '',
             '| Scenario | Stratum | Valid / planned | Invalid | Missing | Rate | Reference | Difference |',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    fmt=lambda v:'not estimated' if v is None else f'{v:.4f}'
    for r in rows:
        name=r['scenario'].replace('|','\\|').replace('\n',' ')
        lines.append(f"| {name} | {r['stratum']} | {r['valid']}/{r['planned']} | {r['invalid']} | {r['missing']} | {fmt(r['rate'])} | {fmt(r['reference_probability'])} | {fmt(r['difference'])} |")
    lines += ['', '## Controlled condition responses', '',
              f"Generated {len(groups)} one-factor curves and {len(changes)} adjacent-level contrasts. Other four inputs are held exactly fixed within each curve. X=1 and X>1 are separate strata; no-game states never enter participation curves.", '',
              'If no matched levels exist, no response curve is fabricated. Missing valid samples remain gaps, and contrasts without both estimates are not estimated. A single observation never establishes a stable behavioral tendency.', '',
              '## Interpretation and limitations', '',
              '- Participation rates and Wilson 95% intervals condition on valid responses. Invalid output, no-game and missing work are never coded as refusals.',
              '- Gray bounds assign every unresolved eligible trial (invalid or missing) either decline or participate; these are sensitivity bounds, not confidence intervals.',
              '- Adjacent-level changes use unpaired Newcombe-Wilson intervals. Repetition indices are scheduling labels, not paired random seeds. Subtracting the fixed reference change shifts those intervals.',
              '- Intervals assume independent Bernoulli outputs within a fixed state. Provider dependence or model drift can violate that assumption; these are descriptive, pointwise intervals without multiplicity correction or significance claims.',
              '- Prompt, model, source and execution mode are not pooled across runs. This command analyzes one run only. Requested model names need not pin provider versions; raw provider model identifiers remain in responses.',
              '- The original adjusted behavioral model is a specified reference, not global evacuation optimality or human ground truth. Differences do not establish human realism, irrationality or superiority.',
              '- Explanation text is archived but never used as causal evidence. This report does not estimate evacuation consequences, burden, calibration or population-level effects.',
              '- Hashes establish snapshot consistency, not authenticated provider provenance. A missing provider model identifier cannot rule out hidden version drift.',
              '- Usage totals are included only where the provider supplied them in validated response envelopes. Missing usage, failed requests and interrupted requests are not assigned zero cost.', '',
              '## Traceability', '',
              'See `scenario_summary.csv`, `condition_contrasts.csv`, `trial_index.csv`, `invalid_reasons.csv`, `provenance.json` and `manifest.json`. `input_snapshot/` preserves the analyzed inputs; `analysis_source/` preserves the scripts. No inputs were modified.', '', '## Figures', '']
    for name in images:
        if name.endswith('.png'):lines += [f'![{name}](figures/{name})','']
    return '\n'.join(lines)+'\n'


def analyze(folder, output, allow_synthetic=False):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    require(folder != output and folder not in output.parents and output not in folder.parents, 'Use an output directory separate from the input run')
    require(not output.exists(), 'Output exists; choose a new analysis directory')
    data = audit(folder, allow_synthetic)
    groups = curves(data['rows'])
    changes = contrasts(groups)
    output.parent.mkdir(parents=True,exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output.name+'.pending-',dir=output.parent))
    try:
        for file in data['files']:
            target=staging/'input_snapshot'/file.relative_to(folder)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        require(all(digest(folder/name)==sha and digest(staging/'input_snapshot'/name)==sha for name,sha in data['hashes'].items()), 'Inputs changed during analysis; stop sampling before analysis')
        (staging/'analysis_source').mkdir()
        for name in ('individual_analysis.py','individual_sampling.py'):
            shutil.copyfile(Path(__file__).with_name(name),staging/'analysis_source'/name)
        write_csv(staging/'scenario_summary.csv',data['rows'])
        write_csv(staging/'trial_index.csv',data['trace'],fields=list(data['trace'][0]) if data['trace'] else ['index','scenario','raw_file','raw_sha256'])
        contrast_fields=['curve','factor','stratum','scenario_a','scenario_b','value_a','value_b','n_a','n_b','missing_a','missing_b','invalid_a','invalid_b','observed_change','change95_low','change95_high','reference_change','response_deviation','deviation95_low','deviation95_high']
        write_csv(staging/'condition_contrasts.csv',changes,contrast_fields)
        write_csv(staging/'invalid_reasons.csv',[dict(error=k,count=v) for k,v in sorted(data['errors'].items())],['error','count'])
        write_json(staging/'curves.json',[dict(id=g['id'],factor=g['factor'],stratum=g['stratum'],fixed=g['fixed'],scenarios=[r['scenario'] for r in g['points']]) for g in groups])
        (staging/'figures').mkdir();images, mpl_version=plots(data,groups,staging/'figures')
        write_json(staging/'provenance.json',dict(schema=VERSION,createdAtUtc=datetime.now(timezone.utc).isoformat(),inputDirectory=str(folder),
                   requestedModel=data['plan']['model'],promptVersion=data['plan']['promptVersion'],execution=data['mode'],sourceHash=data['source'],
                   observedProviderModels=data['providerModels'],
                   runBinding=read(folder/'ledger.json')['binding'],instructionsSHA256=digest(folder/'instructions.txt'),inputHashes=data['hashes'],
                   matplotlibVersion=mpl_version,remoteRequestsByAnalysis=0,formalExperiment=bool(data.get('formalLockID')) and data['mode']=='api',formalLockID=data.get('formalLockID'),independentBernoulliAssumption=True,
                   interval='pointwise Wilson 95%; unpaired Newcombe-Wilson adjacent contrasts; no multiplicity correction'))
        (staging/'REPORT.md').write_text(report(data,groups,changes,images),encoding='utf-8')
        require(all(digest(folder/name)==sha for name,sha in data['hashes'].items()), 'Inputs changed during analysis')
        require(sorted(f.name for f in (folder/'trials').glob('*.json'))==sorted(f.name for f in (staging/'input_snapshot'/'trials').glob('*.json')), 'New trials appeared during analysis')
        write_json(staging/'manifest.json',dict(schema='analysis-artifact-sha256-v1',files=[dict(path=f.relative_to(staging).as_posix(),sha256=digest(f),bytes=f.stat().st_size) for f in sorted(staging.rglob('*')) if f.is_file()]))
        # Windows sandbox/filesystems may disallow renaming a populated directory.
        # Publish individual files, then a completion marker; partial output is never publishable.
        output.mkdir()
        for file in sorted(staging.rglob('*')):
            if file.is_file():
                target=output/file.relative_to(staging)
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        write_json(output/'COMPLETE.json',dict(schema=VERSION,manifestSHA256=digest(output/'manifest.json')))
        require(staging.resolve().parent==output.parent and staging.name.startswith(output.name+'.pending-'), 'Unexpected staging cleanup path')
        shutil.rmtree(staging)
    except BaseException:
        # Failed staging is retained for diagnosis; never publish it as a completed report.
        raise
    return data, groups


def publish(output, records_root):
    """Append an English analysis record without replacing the Unity-owned automatic tail."""
    output, records_root=Path(output).resolve(),Path(records_root).resolve()
    verify(output)
    provenance=read(output/'provenance.json')
    with (output/'scenario_summary.csv').open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream))
    identity='analysis_'+hashlib.sha256(str(output).encode()).hexdigest()[:16]
    record=dict(recordID=identity,recordedAtUtc=provenance['createdAtUtc'],kind='individual_fixed_state_analysis',model=provenance['requestedModel'],
                promptVersion=provenance['promptVersion'],execution=provenance['execution'],reportDirectory=str(output),manifestSHA256=digest(output/'manifest.json'),
                valid=sum(int(r['valid']) for r in rows),invalid=sum(int(r['invalid']) for r in rows),missing=sum(int(r['missing']) for r in rows),noGame=sum(int(r['no_game']) for r in rows),remoteRequests=0)
    write_json(output/'analysis_record.json',record)
    try:
        records_root.mkdir(parents=True,exist_ok=True)
        with (records_root/'.notebook.lock').open('a+b') as gate:
            gate.seek(0,2)
            if not gate.tell():gate.write(b' ');gate.flush()
            gate.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
            directory=records_root/'analysis_records';directory.mkdir(exist_ok=True)
            write_json(directory/(identity+'.json'),record)
            catalog=[read(f) for f in sorted(directory.glob('*.json'))]
            write_csv(records_root/'ANALYSIS_CATALOG.csv',catalog)
            notebook=records_root/'EXPERIMENT_LOG.md'
            text=notebook.read_text(encoding='utf-8-sig') if notebook.exists() else '# Experiment and Validation Notebook\n\n<!-- AUTO-RECORDED RUNS -->\n'
            marker='<!-- AUTO-RECORDED RUNS -->'
            require(marker in text, 'Notebook marker missing; publication pending')
            if f'### {identity}' not in text:
                link=os.path.relpath(output,records_root).replace('\\','/')
                entry=f"### {identity}\n\nRecorded (UTC): {record['recordedAtUtc']}. Purpose: describe controlled personal choices versus the original reference; execution: {record['execution']}; model: {record['model']}; prompt: {record['promptVersion']}. Valid {record['valid']}; invalid {record['invalid']}; missing {record['missing']}; saved no-game {record['noGame']}. Analysis made zero API requests. Synthetic data are software validation only; pointwise intervals assume independent model outputs and do not establish human behavior or evacuation outcomes.\n\nData: [analysis report]({link}/REPORT.md). Input/source hashes and raw snapshots are preserved in the report directory.\n\n"
                temp=notebook.with_suffix('.analysis-pending')
                temp.write_text(text.replace(marker,entry+marker,1),encoding='utf-8');os.replace(temp,notebook)
        (output/'publication_pending.json').unlink(missing_ok=True)
        return True
    except (OSError,ValueError) as error:
        write_json(output/'publication_pending.json',dict(recordsRoot=str(records_root),record=record,errorType=type(error).__name__,reason=str(error)))
        return False


def verify(output):
    output=Path(output).resolve()
    require(read(output/'COMPLETE.json')['manifestSHA256']==digest(output/'manifest.json'), 'Incomplete/modified report manifest')
    manifest=read(output/'manifest.json')
    require(manifest.get('schema')=='analysis-artifact-sha256-v1' and isinstance(manifest.get('files'),list), 'Unsupported manifest')
    seen=set()
    for file in manifest['files']:
        path=(output/file['path']).resolve()
        require(file['path'] not in seen and output in path.parents and path.stat().st_size==file['bytes'] and digest(path)==file['sha256'], 'Report artifact changed; refusing verification/publication')
        seen.add(file['path'])
    require({'REPORT.md','scenario_summary.csv','trial_index.csv','provenance.json'}.issubset(seen), 'Incomplete report manifest')
    return len(seen)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path,help='Sampling run, or completed report with --publish-only')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--allow-synthetic',action='store_true')
    parser.add_argument('--records-root',type=Path,default=Path(__file__).resolve().parents[1]/'experiment_records')
    parser.add_argument('--publish-only',action='store_true')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    if args.verify_only:
        print(f'Verified {verify(args.folder)} hashed report artifacts.');return
    if args.publish_only:
        output=args.folder
    else:
        parser.error('--output is required') if args.output is None else None
        analyze(args.folder,args.output,args.allow_synthetic);output=args.output
    recorded=publish(output,args.records_root)
    print(f'Analysis saved: {output}; notebook: '+('recorded' if recorded else 'pending (retry with --publish-only)'))


if __name__=='__main__':
    main()
