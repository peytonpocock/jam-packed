"""
scan.py
Finds videos in Videos/originals, adds them to library/catalog.yaml and fills in
what it can measure: orientation, length, resolution, plus a first guess at
energy, pace, brightness and colours from the footage itself.

It never overwrites a field you've already set, and it saves a contact sheet per
clip in Videos/thumbs so tags can be checked by eye (Claude uses these too).

Needs ffmpeg/ffprobe on the PATH, plus numpy.

    python library/tools/scan.py            # scan and update the catalog
    python library/tools/scan.py --rescan   # re-guess auto-tagged clips too
"""

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
REPO = os.path.dirname(LIB)
sys.path.insert(0, LIB)
import catalog_io  # noqa: E402

VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.mkv', '.webm', '.avi', '.wmv'}
HUE_NAMES = [(15, 'red'), (40, 'orange'), (65, 'yellow'), (160, 'green'),
             (195, 'cyan'), (255, 'blue'), (290, 'purple'), (335, 'magenta'), (360, 'red')]


def slug(name):
    s = re.sub(r'[^a-z0-9]+', '-', os.path.splitext(name)[0].lower()).strip('-')
    return s or 'clip'


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams',
                          '-show_format', path], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next(s for s in info['streams'] if s.get('codec_type') == 'video')
    w, h = int(v['width']), int(v['height'])
    rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            rot = int(sd['rotation'])
    rot = int(v.get('tags', {}).get('rotate', rot))
    if abs(rot) in (90, 270):
        w, h = h, w
    dur = float(info['format'].get('duration') or v.get('duration') or 0)
    num, _, den = (v.get('avg_frame_rate') or '0/1').partition('/')
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return w, h, dur, fps


def frames(path, dur, n=24, size=(96, 54)):
    """Grab n evenly spaced small RGB frames."""
    fps = n / max(dur, 0.5)
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf',
                          'fps={:.5f},scale={}:{}'.format(fps, *size),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    arr = np.frombuffer(out, np.uint8)
    count = arr.size // (size[0] * size[1] * 3)
    return arr[:count * size[0] * size[1] * 3].reshape(count, size[1], size[0], 3).astype(np.float32) / 255.0


def motion(path, size=(64, 36)):
    """Average frame to frame change over the first 20 seconds at 10 fps."""
    out = subprocess.run(['ffmpeg', '-v', 'error', '-t', '20', '-i', path, '-vf',
                          'fps=10,scale={}:{}'.format(*size), '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True, check=True).stdout
    arr = np.frombuffer(out, np.uint8).astype(np.float32) / 255.0
    n = arr.size // (size[0] * size[1])
    if n < 2:
        return 0.0
    arr = arr[:n * size[0] * size[1]].reshape(n, -1)
    return float(np.mean(np.abs(np.diff(arr, axis=0))))


def colour_stats(fr):
    rgb = fr.reshape(-1, 3)
    mx, mn = rgb.max(1), rgb.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb.T
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    keep = (sat > 0.35) & (mx > 0.2)
    names = []
    if keep.mean() > 0.03:
        hist = {}
        for hv in hue[keep]:
            name = next(n for lim, n in HUE_NAMES if hv < lim)
            hist[name] = hist.get(name, 0) + 1
        total = sum(hist.values())
        names = [n for n, c in sorted(hist.items(), key=lambda x: -x[1]) if c / total > 0.15][:3]
    if not names:
        names = ['monochrome']
    return float(mx.mean()), float(sat.mean()), names


def contact_sheet(fr, path):
    from PIL import Image
    idx = np.linspace(0, len(fr) - 1, min(6, len(fr))).astype(int)
    tiles = [(fr[i] * 255).astype(np.uint8) for i in idx]
    h, w, _ = tiles[0].shape
    sheet = np.zeros((h * 2, w * 3, 3), np.uint8)
    for k, t in enumerate(tiles):
        sheet[(k // 3) * h:(k // 3 + 1) * h, (k % 3) * w:(k % 3 + 1) * w] = t
    Image.fromarray(sheet).resize((w * 3 * 2, h * 2 * 2)).save(path, quality=85)


def guess(w, h, dur, mot, bright, sat):
    pace = 'slow' if mot < 0.025 else 'medium' if mot < 0.07 else 'fast'
    score = min(mot / 0.12, 1.0) * 0.6 + sat * 0.25 + bright * 0.15
    energy = int(min(5, max(1, round(1 + score * 4.5))))
    brightness = 'dark' if bright < 0.3 else 'medium' if bright < 0.6 else 'bright'
    return pace, energy, brightness


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--videos', default=os.path.join(REPO, 'Videos'))
    ap.add_argument('--rescan', action='store_true', help='re-guess clips still tagged_by auto')
    ap.add_argument('--limit', type=int, default=0, help='stop after this many clips (run again to continue)')
    args = ap.parse_args()

    originals = os.path.join(args.videos, 'originals')
    thumbs = os.path.join(args.videos, 'thumbs')
    os.makedirs(thumbs, exist_ok=True)
    cat_path = os.path.join(LIB, 'catalog.yaml')
    entries = catalog_io.load(cat_path)
    by_file = {e.get('file'): e for e in entries}
    ids = {e.get('id') for e in entries}

    found = []
    for root, _, files in os.walk(originals):
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in VIDEO_EXT:
                found.append(os.path.relpath(os.path.join(root, f), args.videos).replace('\\', '/'))

    added = updated = 0
    for rel in found:
        e = by_file.get(rel)
        is_new = e is None
        if not is_new and not (args.rescan and e.get('tagged_by') == 'auto'):
            continue
        path = os.path.join(args.videos, rel)
        try:
            w, h, dur, fps = probe(path)
            fr = frames(path, dur)
            mot = motion(path)
        except Exception as ex:
            print('  skipped {} ({})'.format(rel, ex))
            continue
        bright, sat, colours = colour_stats(fr)
        pace, energy, brightness = guess(w, h, dur, mot, bright, sat)
        if is_new:
            base = slug(os.path.basename(rel))
            cid, k = base, 2
            while cid in ids:
                cid, k = '{}-{}'.format(base, k), k + 1
            ids.add(cid)
            e = {'id': cid, 'file': rel, 'enabled': True, 'tags': [], 'use': ['backdrop', 'totem'],
                 'tagged_by': 'auto'}
            entries.append(e)
            by_file[rel] = e
            added += 1
        else:
            updated += 1
        measured = {'orientation': 'vertical' if h > w * 1.05 else 'horizontal' if w > h * 1.05 else 'square',
                    'duration_s': round(dur, 2), 'resolution': '{}x{}'.format(w, h), 'fps': round(fps, 2)}
        e.update(measured)                                   # facts are always refreshed
        guesses = {'energy': energy, 'pace': pace, 'brightness': brightness, 'colors': colours}
        for k, v in guesses.items():
            if is_new or e.get('tagged_by') == 'auto' or k not in e:
                e[k] = v
        e['motion'] = round(mot, 4)
        contact_sheet(fr, os.path.join(thumbs, e['id'] + '.jpg'))
        print('  {:28s} {:10s} {:6.1f}s energy {} {:6s} {}'.format(
            e['id'][:28], e['orientation'], dur, e['energy'], e['pace'], ','.join(e['colors'])), flush=True)
        catalog_io.save(cat_path, entries)                   # save as we go, so a stopped scan keeps its work
        if args.limit and added + updated >= args.limit:
            break

    missing = [e['id'] for e in entries if e.get('file') not in found]
    catalog_io.save(cat_path, entries)
    print('Catalog: {} clips ({} new, {} re-guessed). Saved {}'.format(len(entries), added, updated, cat_path))
    if missing:
        print('Not found on disk (left in catalog): ' + ', '.join(missing))


if __name__ == '__main__':
    main()
