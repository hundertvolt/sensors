"""Merge harvest agent outputs (out_H*.md) into audit/HARVEST.md + audit/harvest/<AREA>.md."""
import collections, glob, os, re, sys
sys.path.insert(0, '/home/user/sensors/audit/sweeps')
from owner_of import classify

H = os.path.dirname(os.path.abspath(__file__))
REPO = '/home/user/sensors'
PLAN = open(f'{REPO}/PROJECT_AUDIT_PLAN.md').read()
AREAS = "XCUT CORE ALGO BUS SENS STOR UART NET REST LED GEN TOOL SCR CI WEB TEST TWIN HW SEC MEM PERF PLAT PAR DOC LIC".split()
AREA_NAMES = dict(XCUT='System-wide contracts', CORE='Core runtime modules', ALGO='Pure algorithms and codecs', BUS='Bus layer',
    SENS='Sensor drivers', STOR='FRAM storage', UART='UART protocol', NET='Networking', REST='Web server and HTTP surface',
    LED='Notification and LED', GEN='Build generator and device definitions', TOOL='Toolchain installer and build overrides',
    SCR='Scripts and test orchestration', CI='CI, dependency pins and supply chain', WEB='Website', TEST='Software test tiers',
    TWIN='Digital twin', HW='Real-hardware tier', SEC='Security', MEM='Memory safety', PERF='Timing and capacity budgets',
    PLAT='MicroPython/RP2040 platform facts', PAR='Legacy parity and field migration', DOC='Documentation set', LIC='Licensing and attribution')
KINDS = "SETTLED INVAR MIRROR LIMIT RISK ASSUME PLATFORM WORKAROUND SUPPRESS TODO OPENQ DRIFT NOTE".split()
DEFINED = set(re.findall(r'\*\*((?:' + '|'.join(AREAS + ['ENV']) + r')\.[ST]\d\d)\*\*', PLAN))
REDACT = [('pta2ToWIVkFIYHm7SDne', '<redacted: bench PSK, HW.T11>')]
ITEM = re.compile(r'^- (?:\[\d+\] )?\**([A-Z][A-Z /]{1,30}?)\**\s*\|.*\|')
ALIAS = {'SECURITY': 'SEC', 'PLATFORM': 'PLAT', 'DOCS': 'DOC', 'TESTS': 'TEST', 'LEGACY': 'PAR', 'ENV': 'SCR'}


def parse(path):
    agent = re.search(r'out_(H\d+)', path).group(1)
    items, src, cur, stop = [], '(top)', None, False
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        for a, b in REDACT:
            line = line.replace(a, b)
        if line.startswith('## '):
            if cur: items.append(cur); cur = None
            head = line[3:].strip()
            if re.match(r'(Coverage|Totals|Top ?10|Untracked|Summary|Notes)', head, re.I):
                stop = head.lower().startswith(('coverage', 'totals', 'top', 'summary'))
                src = head
                continue
            stop = False
            src = head
            continue
        if stop:
            continue
        if ITEM.match(line):
            if cur: items.append(cur)
            cur = dict(agent=agent, src=src, text=re.sub(r'^\[\d+\] ', '', line[2:].strip()))
        elif cur and line.startswith((' ', '\t')) and line.strip():
            cur['text'] += ' ' + line.strip()
        elif cur and not line.strip():
            items.append(cur); cur = None
    if cur: items.append(cur)
    out = []
    for it in items:
        f = [x.strip() for x in it['text'].split(' | ')]
        toks = [x.strip() for x in f[0].strip('*').split('/')]
        kind = next((x for x in toks if x in KINDS), 'NOTE')
        hint = next((x for x in toks if x in AREAS), None)
        ai = max((i for i, x in enumerate(f) if x.lower().startswith('area:')), default=None)
        if ai is None:
            area, cov, mid = '?', '', f[2:]
        else:
            area = f[ai].split(':', 1)[1].strip()
            cov = ' | '.join(f[ai + 1:])
            mid = f[2:ai]
        code = re.split(r'[\s/,(+]', area.upper().strip('` '))[0]
        code = ALIAS.get(code, code)
        if code not in AREAS and hint:
            code = hint
        if code not in AREAS:
            pm = re.match(r'`?([\w./-]+\.[\w]+)', f[1] if len(f) > 1 else '')
            own = classify(pm.group(1)) if pm else []
            code = 'PAR' if own == ['REFERENCE'] or agent == 'H16' else (own[0] if own and own[0] in AREAS else 'DOC' if pm and pm.group(1).endswith('.md') else 'UNSORTED')
        quote = mid[0] if mid else ''
        desc = ' | '.join(mid[1:]) if len(mid) > 1 else ''
        refs = re.findall(r'\b((?:' + '|'.join(AREAS + ['ENV']) + r')\.[ST]\d\d)\b', cov)
        bad = [r for r in refs if r not in DEFINED]
        out.append(dict(agent=it['agent'], src=it['src'], kind=kind, rawkind=f[0].strip('*'), anchor=f[1] if len(f) > 1 else '', quote=quote,
                        desc=desc, area=code, area_raw=area, cov=cov, bad=bad))
    return out


def key(it):
    return (it['kind'], re.sub(r'\s+', '', it['anchor'].strip('`')).lower())


def main():
    files = sorted(glob.glob(f'{H}/out_H*.md'))
    items = [i for f in files for i in parse(f)]
    seen, merged = {}, []
    for it in items:
        k = key(it)
        if k in seen and k[1]:
            seen[k].setdefault('also', []).append(it['agent'])
            continue
        seen[k] = it
        merged.append(it)
    by_area = collections.defaultdict(list)
    for it in merged:
        by_area[it['area']].append(it)
    return files, items, merged, by_area


if __name__ == '__main__':
    files, items, merged, by_area = main()
    print(f'{len(files)} files, {len(items)} items, {len(merged)} after exact dedup')
    for a in AREAS + ['UNSORTED']:
        if by_area.get(a):
            c = collections.Counter(i['kind'] for i in by_area[a])
            print(f'{a:8} {len(by_area[a]):5}  ' + ' '.join(f'{k}={c[k]}' for k in KINDS if c[k]))
    bad = [i for i in merged if i['bad']]
    print('unknown plan IDs cited:', len(bad), sorted({b for i in bad for b in i['bad']})[:30])
    uns = [i for i in merged if i['area'] == 'UNSORTED']
    print('unsorted area values:', collections.Counter(i['area_raw'] for i in uns).most_common(15))


WT = f'{H}/../wt'
_files = {}


def lines_of(path):
    if path not in _files:
        p = os.path.join(WT, path)
        _files[path] = open(p, encoding='utf-8', errors='replace').read().split('\n') if os.path.isfile(p) else None
    return _files[path]


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[`*_>#]|\\', '', s)).strip().lower()


def check_anchor(it):
    """Return (status, found_line): ok / moved / quote-not-found / no-quote / not-a-file / out-of-bounds."""
    m = re.match(r'`?([\w./-]+\.[\w]+):(\d[\d,\s-]*)', it['anchor'])
    if not m:
        return 'not-a-file', None
    path = m.group(1)
    nums = [int(x) for x in re.findall(r'\d+', m.group(2))]
    L = lines_of(path)
    if L is None or not nums:
        return 'not-a-file', None
    oob = any(n < 1 or n > len(L) + 1 for n in nums)
    q = it['quote']
    frags = re.findall(r'"([^"]{12,})"', q) or re.findall(r'“([^”]{12,})”', q) or [q.strip().strip('"')]
    frags = [norm(y) for f in frags for y in re.split(r'…|\.\.\.|\[\.\.\.\]', f)]
    frags = [f for f in frags if len(f) >= 12]
    if not frags:
        return ('out-of-bounds' if oob else 'no-quote'), None
    frag = max(frags, key=len)[:40]
    lo, hi = min(nums), max(nums)
    win = norm(' '.join(L[max(0, lo - 6):min(len(L), hi + 5)]))
    if frag in win:
        return ('out-of-bounds' if oob else 'ok'), None
    hits = [i + 1 for i in range(len(L)) if frag in norm(' '.join(L[i:i + 3]))]
    if hits:
        return 'moved', min(hits, key=lambda h: abs(h - lo))
    return ('out-of-bounds' if oob else 'quote-not-found'), None


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'check':
    files, items, merged, by_area = main()
    c = collections.Counter(); ex = collections.defaultdict(list)
    for it in merged:
        s, fx = check_anchor(it)
        c[s] += 1; ex[s].append((it['agent'], it['anchor'], it['quote'][:60], fx))
    print(c)
    for s in ('out-of-bounds', 'quote-not-found', 'moved'):
        for e in ex[s][:8]:
            print(s, e)
    print(collections.Counter(e[0] for e in ex['quote-not-found']))
    print(collections.Counter(e[0] for e in ex['moved']))


def wrap(text, first, cont, width=104):
    words, out, cur = text.split(' '), [], first
    for w in words:
        if not w:
            continue
        cand = cur + w if cur in (first, cont) else cur + ' ' + w
        if len(cand) > width and cur.strip() and cur not in (first, cont) and cur.count('`') % 2 == 0:
            out.append(cur.rstrip()); cur = cont + w
        else:
            cur = cand
    out.append(cur.rstrip())
    return out


def section(text, head_re):
    m = re.search(r'^## ' + head_re + r'.*?$(.*?)(?=^## |\Z)', text, re.M | re.S | re.I)
    return m.group(1).strip() if m else ''


def render():
    files, items, merged, by_area = main()
    stats = collections.Counter()
    os.makedirs(f'{REPO}/audit/harvest', exist_ok=True)
    table = []
    for a in AREAS + (['UNSORTED'] if by_area.get('UNSORTED') else []):
        its = by_area.get(a, [])
        if not its:
            continue
        kc = collections.Counter(i['kind'] for i in its)
        table.append((a, len(its), kc))
        L = [f'# Harvest — {a}: {AREA_NAMES.get(a, "unsorted")}', '',
             'What the project\'s own comments, docs and history already record for this area (snapshot `2a88cc8`).',
             'Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.', '',
             'Kinds: ' + ', '.join(f'{k} {kc[k]}' for k in KINDS if kc[k]) + f' — {len(its)} items.', '']
        n, cursrc = 0, None
        for it in its:
            if it['src'] != cursrc:
                cursrc = it['src']
                L += ['', f'## {cursrc}', '']
            n += 1
            st, found = check_anchor(it)
            stats[st] += 1
            anchor = it['anchor'].strip('`')
            tag = ''
            if st == 'moved':
                tag = f' ⟨re-anchored: quote found at line {found}⟩'
                anchor = re.sub(r':(\d+)', f':{found}', anchor, count=1) + f' (agent cited {it["anchor"].strip("`")})'
            elif st == 'quote-not-found':
                tag = ' ⟨quote not matched at the anchor⟩'
            elif st == 'out-of-bounds':
                tag = ' ⟨anchor out of bounds⟩'
            cov = it['cov'] if it['cov'] and it['cov'] != '-' else ''
            also = f' (also {", ".join(sorted(set(it["also"])))})' if it.get('also') else ''
            kl = it['kind'] if it['kind'] != 'NOTE' else f"NOTE({it['rawkind']})"
            body = f'**{a}.N{n:03d}** {kl} · `{anchor}` — {it["quote"]} — {it["desc"]}'
            if cov:
                body += f' · {cov}'
            body += f' · [{it["agent"]}{also}]{tag}'
            L += wrap(body, '- ', '  ')
        open(f'{REPO}/audit/harvest/{a}.md', 'w').write('\n'.join(L) + '\n')
    return files, items, merged, table, stats


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'render':
    files, items, merged, table, stats = render()
    print(len(items), len(merged), stats)
    for a, n, kc in table:
        print(a, n)


PARTS = {
    'H01': 'src/, first half (14 files)', 'H02': 'src/, second half, plus ext/ (22 files)',
    'H03': 'tests/ part A: helpers, fakes, first test files (28)', 'H04': 'tests/ part B (10 large files)',
    'H05': 'tests/ part C (35)', 'H06': 'digital_twin/ and every tests/test_digital_twin_* (50)',
    'H07': 'tests_hardware/ code (97)', 'H08': 'tests_hardware/README.md, the queue, the handover, dev_legacy/, mockdata/ (37)',
    'H09': 'scripts/, toolchain/, buildgen/, .github/, devices/, root Python config (57)', 'H10': 'tests_scripts/ (65)',
    'H11': 'js/, html/, tests_js/, web config (37)', 'H12': 'SPECIFICATION.md lines 1-3421 (Parts A-E)',
    'H13': 'SPECIFICATION.md lines 3422-6785 (Parts F-M)', 'H14': 'CLAUDE.md, README.md, DEVICE_REFERENCE.md, update_and_install.txt',
    'H15': 'BACKLOG.md, HEAP_FRAGMENTATION_MEASUREMENTS.md (+ archive at 12640c2), UART_C_PORT_CHANGELOG.md, licences',
    'H16': 'legacy tree: python/, modules/, html_raw/, build-*.sh (parity oracle only)',
    'H17': 'all commit messages to 2a88cc8, GitHub issues and pull requests (read-only)'}
PARTIAL = [
    'H02: `src/voc_algorithm.py` comments all read, code read at 1-330 and 700-797, the rest grepped; `ext/microdot.py` read in full only on the code paths this project uses.',
    'H15: the `12640c2` heap-measurement archive (5,553 lines) keyword-scanned end to end, ~1,300 lines read in full.',
    'H16: legacy `voc_algorithm.py` lines 430-911 (uncommented) scanned only; `python/CommonDrivers/microdot.py` provenance only.',
    'Every other partition: every file read in full (comments via the extractor, docs in full text); nothing reported unreadable.']


def index(files, items, merged, table, stats):
    L = ['# Audit harvest — what the project already records', '',
         'Every limitation, accepted risk, settled decision, assumption, workaround, unenforced invariant, mirror',
         'obligation, suppression, open question and piece of drift that the project\'s own comments, docstrings,',
         'docs, commit messages and GitHub discussions state — recorded, not verified, triaged or solved (owner,',
         '`PROJECT_AUDIT_PLAN.md` 3.1; validation step V10). Snapshot: commit `2a88cc8`; line anchors resolve there.',
         'Per-area catalogs: `audit/harvest/<AREA>.md`; item IDs `<AREA>.Nnnn` are stable once committed.', '',
         '## How to read an item', '',
         '`**AREA.Nnnn** KIND · anchor — "verbatim quote" — what it declares · plan cross-reference · [agent]`',
         '',
         '- **Kinds**: TODO (deferred work), LIMIT (known limitation, gap, fidelity gap of a fake/twin), RISK',
         '  (accepted risk), SETTLED (owner decision / deliberate — check it is still accurate, never reopen), ASSUME',
         '  (assumption, unverified claim, single dated measurement), WORKAROUND (external defect worked around),',
         '  INVAR (contract kept by convention only, or the named enforcer), MIRROR (duplicate/mirror obligation),',
         '  SUPPRESS (lint/type/test suppressions and gates), PLATFORM (version- or silicon-specific fact), OPENQ',
         '  (open question), DRIFT (doc/comment vs code or doc, stale fact, dangling reference), NOTE(<label>) (an',
         '  agent\'s own finer label such as LIC, PAR, MEM or REVERT, kept as given).',
         '- **Plan cross-reference**: `covered-by: <ID>` — a plan topic/seed already covers it; `related: <ID>` —',
         '  partial overlap; none — new to the plan. Agents set these; the audit re-checks them.',
         '- **Anchor tags**: a script compared every quote with the snapshot at its anchor. Untagged: the quote is',
         '  there (or the anchor is not a file line: a SPECIFICATION Part, a commit, a PR). `⟨re-anchored⟩`: the',
         '  quote was found elsewhere in the same file and the anchor now points there. `⟨quote not matched⟩`: a',
         '  paraphrased or composite quote — check before relying on it. The bench PSK is redacted (`HW.T11`).', '',
         '## Size and anchor check', '',
         f'{len(items)} items from 17 agents; {len(items) - len(merged)} exact duplicates (same kind and anchor) folded;',
         f'{len(merged)} catalogued. Anchor check: ' + ', '.join(f'{k} {v}' for k, v in stats.most_common()) + '.', '',
         '| Area | Items | ' + ' | '.join(KINDS) + ' |', '|---|---|' + '---|' * len(KINDS)]
    for a, n, kc in table:
        L.append(f'| [{a}](harvest/{a}.md) | {n} | ' + ' | '.join(str(kc[k] or '') for k in KINDS) + ' |')
    L += ['', '## Partitions (read-only agents, one each)', '']
    for f in files:
        ag = re.search(r'out_(H\d+)', f).group(1)
        n = sum(1 for i in items if i['agent'] == ag)
        L.append(f'- **{ag}** ({n} items): {PARTS[ag]}')
    L += ['', 'Partial reads, as reported:', ''] + [f'- {p}' for p in PARTIAL]
    h17 = open(f'{H}/out_H17.md', encoding='utf-8').read()
    unt = section(h17, r'Untracked')
    if unt:
        L += ['', '## Untracked deferred work from git history and GitHub (H17, verbatim)', '',
              'Deferred items found in commit messages or PR/issue discussions that no later commit, doc or BACKLOG',
              'entry picks up. Their catalog entries carry the same text in the owning area.', '', unt]
    L += ['', '## Each agent\'s own top 10 (verbatim; anchors are the agent\'s)', '']
    for f in files:
        ag = re.search(r'out_(H\d+)', f).group(1)
        top = section(open(f, encoding='utf-8').read(), r'Top ?10')
        for x, y in REDACT:
            top = top.replace(x, y)
        if top:
            L += [f'### {ag} — {PARTS[ag]}', '', top, '']
    open(f'{REPO}/audit/HARVEST.md', 'w').write('\n'.join(L).rstrip() + '\n')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'all':
    import shutil
    shutil.rmtree(f'{REPO}/audit/harvest', ignore_errors=True)
    files, items, merged, table, stats = render()
    index(files, items, merged, table, stats)
    print(len(items), len(merged), stats)
