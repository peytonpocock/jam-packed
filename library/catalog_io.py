"""
catalog_io.py
Read and write library/catalog.yaml without needing any extra Python packages,
so the same code works inside TouchDesigner and from the command line.

The catalog is a simple YAML list of clips:

    - id: neon-tunnel-01
      file: originals/neon_tunnel.mp4
      energy: 4
      tags: [neon, tunnel, abstract]

Only that subset of YAML is supported: one list of flat entries, scalar values
and inline [lists]. Comments (#) and blank lines are ignored.
"""

import os

FIELD_ORDER = [
    'id', 'file', 'enabled',
    'orientation', 'duration_s', 'resolution', 'fps',
    'energy', 'pace', 'brightness', 'colors', 'tags', 'use',
    'tagged_by', 'notes',
]

HEADER = """\
# Jam Packed video catalog
#
# One entry per clip in Videos/. Run library/tools/scan.py (or ask Claude) to add
# new clips; it fills in what it can and never overwrites what you've changed.
#
#   energy      1 (chill) to 5 (peak)
#   pace        slow / medium / fast
#   brightness  dark / medium / bright
#   use         where it may play: backdrop, totem
#   enabled     false hides a clip without deleting its entry
#   tagged_by   auto = guessed by the scanner, edit freely and change to "you"
"""


def _parse_scalar(text):
    t = text.strip()
    if not t:
        return ''
    if t[0] in '"\'' and t[-1] == t[0] and len(t) >= 2:
        return t[1:-1]
    low = t.lower()
    if low in ('true', 'yes'):
        return True
    if low in ('false', 'no'):
        return False
    if low in ('null', '~'):
        return None
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        return t


def _strip_comment(line):
    out, quote = [], None
    for ch in line:
        if quote:
            if ch == quote:
                quote = None
        elif ch in '"\'':
            quote = ch
        elif ch == '#':
            break
        out.append(ch)
    return ''.join(out).rstrip()


def _parse_value(text):
    t = text.strip()
    if t.startswith('[') and t.endswith(']'):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in inner.split(',')]
    return _parse_scalar(t)


def loads(text):
    entries = []
    cur = None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith('- '):
            cur = {}
            entries.append(cur)
            stripped = stripped[2:]
        if cur is None or ':' not in stripped:
            continue
        key, _, val = stripped.partition(':')
        cur[key.strip()] = _parse_value(val)
    return entries


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return loads(f.read())


def _fmt(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(_fmt(x) for x in v) + ']'
    if v is None:
        return 'null'
    if isinstance(v, float):
        return ('%.2f' % v).rstrip('0').rstrip('.')
    s = str(v)
    if s == '' or any(c in s for c in ':#[],') or s.strip() != s or s.lower() in ('true', 'false', 'yes', 'no', 'null'):
        return '"' + s.replace('"', "'") + '"'
    return s


def dumps(entries):
    lines = [HEADER]
    for e in entries:
        keys = [k for k in FIELD_ORDER if k in e] + sorted(k for k in e if k not in FIELD_ORDER)
        for i, k in enumerate(keys):
            prefix = '- ' if i == 0 else '  '
            lines.append('{}{}: {}'.format(prefix, k, _fmt(e[k])))
        lines.append('')
    return '\n'.join(lines)


def save(path, entries):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(dumps(entries))
    os.replace(tmp, path)
