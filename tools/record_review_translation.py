from pathlib import Path
import json,hashlib,msvcrt,os
R=Path(__file__).resolve().parents[1];H=R/'report/human_review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
status=read(H/'REVIEW_STATUS.json');assert sha(H/'sample.public.json')==status['sampleSHA256']
zh=read(H/'translations.zh-TW.json')['items'];assert set(zh)=={f'H{i:02d}' for i in range(1,49)}
assert all(v['prompt'] and v['explanation'] for v in zh.values())
status.update(readingTranslation='zh-TW',translationType='AI-assisted; no ratings supplied',englishOriginalRetained=True);write(H/'REVIEW_STATUS.json',status)
p=R/'report/PACKAGE_COMPLETE.json';receipt=read(p);receipt['humanReview']['readingTranslation']='zh-TW; AI-assisted translation, not coding'
receipt['files']=[{'path':x.relative_to(R/'report').as_posix(),'sha256':sha(x)} for x in sorted((R/'report').rglob('*')) if x.is_file() and '.build' not in x.parts and x!=p and not x.name.startswith('~$')];write(p,receipt)
p=R/'report/README.md';s=p.read_text(encoding='utf-8');s+='\n## Chinese reading assistance\n\nThe review form now has Traditional Chinese translations of all 48 response explanations and full request contexts, with Chinese option labels. Exact English source messages and explanations remain available. Evidence quotes must still be copied from the English explanation. Rating codes and the original public sample are unchanged. Existing browser storage uses the same key; exported ratings record translation assistance. This is reading support only; no quality judgments have been supplied. The English report itself was not revised by this translation step.\n';p.write_text(s,encoding='utf-8')
# Refresh the changed README hash after its write.
p=R/'report/PACKAGE_COMPLETE.json';receipt=read(p)
for x in receipt['files']:
    if x['path']=='README.md':x['sha256']=sha(R/'report/README.md')
write(p,receipt)
entry='''## V-054 — Chinese reading translation for human review (2026-11-19, Asia/Taipei)

Purpose: make the 48-item review packet easier for the author to read. Added AI-assisted Traditional Chinese translations for every original explanation and full scenario context, translated option labels and brief field definitions. Original English messages, numerical inputs and explanations remain available. Translation preserves ambiguous or incorrect source claims rather than repairing them. No AI coding labels are shown and no ratings are entered. Evidence quotes remain in English; human notes can be Chinese. Exported review files and the scorer retain translation-assistance metadata, including after importing a previous saved file.

Verification: original sample SHA256 unchanged, all H01-H48 translations present, rating code values/schema and browser storage key unchanged. Mocked-DOM form construction and JSON export checks passed. No native browser-layout test or automatic page refresh was performed. The report and all experiment data remain unchanged. New API calls and Unity runs: 0. Human review remains pending. Files: report/human_review/Review.html and translations.zh-TW.json. Prior English-content form retained under local_archive/20261119_review_translation.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as lock:
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-054 ' not in s
        t=p.with_suffix('.translation.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
print('Recorded translation assistance; sample unchanged and human ratings pending.')
