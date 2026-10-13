# engine.py
# Runtime logic for the playground: presets, keyboard shortcuts, calibration.
# The build script loads this file into a Text DAT called "engine" inside the
# "jam" network. Edit it here; press R in the build Text DAT or re-run the
# build to pick up changes.

import json
import os
import random
import sys

# Filled in by build_playground.py
JAM = '/project1/jam'
PRESETS = ''
LIBDIR = ''
VIDEOS = ''

LOOK_PARS = ['Intensity', 'Hue', 'Huespeed', 'Trail', 'Warp', 'Glow', 'Shape', 'Zoom', 'Spin']
VIDEO_PARS = ['Videomix', 'Lookmix', 'React', 'Videohue', 'Videosat']
FX_PARS = ['Bloom', 'Rgbsplit', 'Scanlines', 'Pixelate', 'Posterize', 'Pulse', 'Invert',
           'Huerotate', 'Vignette', 'Grain', 'Kaleido']
MENU_PARS = ['Look', 'Videoblend', 'Mirror']
_state = {'master': 1.0, 'blackout': False}


def J(name=''):
    return op(JAM + ('/' + name if name else ''))


def C():
    return J('controls')


def say(msg):
    print('[jam] ' + msg)
    try:
        ui.status = msg
    except Exception:
        pass


# ---------- presets ----------

def load_presets():
    try:
        with open(PRESETS) as f:
            return json.load(f)
    except Exception as e:
        say('Could not read presets: {}'.format(e))
        return {}


def apply_preset(slot):
    p = load_presets().get(str(slot))
    if not p:
        say('Preset {} is empty. Set Slot to {} and press Save preset to fill it.'.format(slot, slot))
        return
    c = C()
    for name in MENU_PARS:
        if name in p:
            getattr(c.par, name).menuIndex = int(p[name])
    for name in LOOK_PARS + VIDEO_PARS + FX_PARS:
        if name in p:
            getattr(c.par, name).val = p[name]
    for name in FX_PARS + ['Mirror']:                   # effects a preset doesn't mention switch off
        if name not in p:
            par = getattr(c.par, name)
            par.val = par.default
    c.par.Slot = int(slot)
    say('Preset {}: {}'.format(slot, p.get('name', '')))


def save_preset():
    c = C()
    slot = str(int(c.par.Slot))
    data = load_presets()
    old = data.get(slot, {})
    p = {'name': old.get('name', 'Preset ' + slot)}
    for name in MENU_PARS:
        p[name] = getattr(c.par, name).menuIndex
    for name in LOOK_PARS + VIDEO_PARS + FX_PARS:
        p[name] = round(float(getattr(c.par, name).eval()), 3)
    data[slot] = p
    with open(PRESETS, 'w') as f:
        json.dump(data, f, indent=2)
    say('Saved preset {} ({}). Rename it in presets/looks.json if you like.'.format(slot, p['name']))


def randomize():
    c = C()
    c.par.Look.menuIndex = random.randint(0, len(c.par.Look.menuNames) - 1)
    c.par.Intensity = random.uniform(0.4, 0.9)
    c.par.Hue = random.random()
    c.par.Huespeed = random.uniform(0.0, 0.6)
    c.par.Trail = random.uniform(0.5, 0.95)
    c.par.Warp = random.uniform(0.1, 0.9)
    c.par.Glow = random.uniform(0.2, 0.7)
    c.par.Shape = random.random()
    c.par.Zoom = random.uniform(-0.3, 0.8)
    c.par.Spin = random.uniform(-0.5, 0.5)
    say('Randomized')


# ---------- calibration ----------

def calibrate():
    """Step out of view after pressing: captures the empty room in 3 seconds."""
    say('Capturing the empty room in 3 seconds. Step out of view!')
    run("op('{}').module.capture_background()".format(J('engine').path), delayMilliSeconds=3000)


def capture_background():
    c = C()
    if c.par.Source.menuIndex == 0:
        try:
            import numpy
            arr = J('src_kinect').numpyArray()[:, :, 0]
            valid = arr[arr > 0]
            if valid.size > 500:
                lo, hi = numpy.percentile(valid, [1, 99])
                c.par.Near.normMax = float(hi) * 1.5
                c.par.Far.normMax = float(hi) * 1.5
                c.par.Near = float(lo) * 0.5
                c.par.Far = float(hi) * 1.02
            else:
                say('The Kinect image looks empty. Check src_kinect for errors.')
        except Exception as e:
            say('Depth range check skipped: {}'.format(e))
    bg = J('bg')
    bg.par.active = True
    run("op('{}').par.active = False".format(bg.path), delayFrames=4)
    c.par.Usebg = True
    say('Background captured. Only people should light up now (D shows the mask).')


def clear_background():
    C().par.Usebg = False
    say('Background cleared')


# ---------- show controls ----------

def toggle_blackout():
    c = C()
    if _state['blackout']:
        c.par.Master = _state['master']
        _state['blackout'] = False
        say('Blackout off')
    else:
        _state['master'] = c.par.Master.eval() or 1.0
        c.par.Master = 0.0
        _state['blackout'] = True
        say('Blackout on')


def toggle_debug():
    c = C()
    c.par.Debug = not c.par.Debug.eval()


def toggle_fullscreen():
    w = J('window1')
    is_open = getattr(w, 'isOpen', False)
    if is_open:
        w.par.winclose.pulse()
    else:
        w.par.winopen.pulse()


def next_look():
    c = C()
    c.par.Look.menuIndex = (c.par.Look.menuIndex + 1) % len(c.par.Look.menuNames)
    say('Look: ' + c.par.Look.menuLabels[c.par.Look.menuIndex])


def next_blend():
    c = C()
    c.par.Videoblend.menuIndex = (c.par.Videoblend.menuIndex + 1) % len(c.par.Videoblend.menuNames)
    say('Blend: ' + c.par.Videoblend.menuLabels[c.par.Videoblend.menuIndex])


# ---------- video library ----------

_vid = {'started': False, 'deck': 0, 'fading': False, 'to': 0, 'fade_start': 0.0,
        'clip_start': 0.0, 'current': None, 'cat': [], 'mtime': None, 'warned': False}


def _catalog():
    path = LIBDIR + '/catalog.yaml'
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        _vid['cat'] = []
        return []
    if mtime != _vid['mtime']:
        if LIBDIR not in sys.path:
            sys.path.insert(0, LIBDIR)
        import catalog_io
        try:
            _vid['cat'] = catalog_io.load(path)
            _vid['mtime'] = mtime
        except Exception as e:
            say('Could not read catalog.yaml: {}'.format(e))
    return _vid['cat']


def _as_list(v):
    if isinstance(v, list):
        return [str(x).lower() for x in v]
    return [str(v).lower()] if v not in (None, '') else []


def candidates():
    c = C()
    lo, hi = int(c.par.Energymin), int(c.par.Energymax)
    orient = c.par.Orientation.eval()
    use = c.par.Usefor.eval()
    want = [t.strip().lower() for t in c.par.Tags.eval().split(',') if t.strip()]
    out = []
    for e in _catalog():
        if e.get('enabled') is False or not e.get('file'):
            continue
        if not os.path.exists(os.path.join(VIDEOS, e['file'])):
            continue
        energy = e.get('energy')
        if isinstance(energy, (int, float)) and not (lo <= energy <= hi):
            continue
        if orient != 'any' and e.get('orientation') not in (orient, 'square'):
            continue
        if use != 'any' and use not in _as_list(e.get('use')):
            continue
        if want:
            words = _as_list(e.get('tags')) + _as_list(e.get('colors')) + [str(e.get('id', '')).lower(),
                                                                         str(e.get('pace', '')).lower()]
            if not any(w in words for w in want):
                continue
        out.append(e)
    return out


def library_summary():
    cat = _catalog()
    ok = candidates()
    if not cat:
        return 'Video library: no catalog yet. Put clips in Videos/originals and ask Claude to scan them.'
    return 'Video library: {} clips in the catalog, {} match the current Video filters.'.format(len(cat), len(ok))


def _load(deck_index, entry):
    deck = J(('vid_a', 'vid_b')[deck_index])
    deck.par.file = os.path.join(VIDEOS, entry['file']).replace('\\', '/')
    deck.par.play = True
    for name in ('cuepulse',):
        p = getattr(deck.par, name, None)
        if p is not None:
            try:
                p.pulse()
            except Exception:
                pass


def next_clip(fade=True):
    pool = candidates()
    if not pool:
        if not _vid['warned']:
            say(library_summary())
            _vid['warned'] = True
        _vid['clip_start'] = absTime.seconds
        return
    _vid['warned'] = False
    choices = [e for e in pool if e is not _vid['current'] and e.get('id') != (_vid['current'] or {}).get('id')]
    entry = random.choice(choices or pool)
    c = C()
    now = absTime.seconds
    if not _vid['started'] or not fade or c.par.Fadetime.eval() <= 0.01:
        _load(_vid['deck'], entry)
        c.par.Videoxfade = float(_vid['deck'])
        _vid['clip_start'] = now
    else:
        target = 1 - _vid['deck']
        _load(target, entry)
        _vid.update(fading=True, to=target, fade_start=now)
    _vid['current'] = entry
    _vid['started'] = True
    c.par.Nowplaying = '{}  (energy {}, {})'.format(entry.get('id'), entry.get('energy', '?'),
                                                  ', '.join(_as_list(entry.get('tags'))[:4]) or 'no tags')



# ---------- audio beat detection ----------
# Listens to the audio_in CHOP (mic, or "Stereo Mix" for what the PC is playing),
# finds kick drum hits in the bass band, and estimates the tempo from the gaps
# between them. Autobeat on the FX page picks how the Beat pulse uses it.

_beat = {'prev_bass': 0.0, 'flux_mean': 0.0, 'flux_var': 0.0, 'floor': 0.0, 'peak': 1e-6,
         'last_hit': -10.0, 'hits': [], 'bpm': None, 'anchor': 0.0, 'phase': 1.0}


def _bass_level():
    """Bass (40 to 160 Hz) energy and overall loudness of the latest audio chunk."""
    a = J('audio_in')
    if a is None or a.numChans == 0 or a.numSamples < 64:
        return None
    import numpy as np
    x = a.numpyArray()
    x = x.mean(axis=0) if x.ndim > 1 else x
    n = len(x)
    rate = max(a.rate, 1.0)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    f = np.fft.rfftfreq(n, 1.0 / rate)
    band = spec[(f >= 40) & (f <= 160)]
    bass = float(band.mean()) if len(band) else 0.0
    return bass, float(np.sqrt(np.mean(x * x)))


def _tempo(hits):
    """Median gap between recent hits, folded into 80 to 170 BPM."""
    gaps = [b - a for a, b in zip(hits, hits[1:]) if 0.2 < b - a < 2.0]
    if len(gaps) < 4:
        return None
    bpms = []
    for g in gaps:
        bpm = 60.0 / g
        while bpm < 80:
            bpm *= 2
        while bpm > 170:
            bpm /= 2
        bpms.append(bpm)
    bpms.sort()
    mid = bpms[len(bpms) // 2]
    near = [b for b in bpms if abs(b - mid) < mid * 0.05]   # average around the median, frames are coarse
    return sum(near) / len(near)


def beat_frame(c, now):
    mode = c.par.Autobeat.eval()
    if mode == 'off':
        return
    got = _bass_level()
    if got is None:
        return
    bass, loud = got
    b = _beat
    # meter: bass level relative to the loudest recent bass
    b['peak'] = max(bass, b['peak'] * 0.995)
    c.par.Audiolevel = min(1.0, bass / max(b['peak'], 1e-6))

    # onset: a jump in bass well above its usual frame-to-frame jumps
    flux = max(0.0, bass - b['prev_bass'])
    b['prev_bass'] = bass
    k = 0.03
    b['flux_mean'] += k * (flux - b['flux_mean'])
    b['flux_var'] += k * ((flux - b['flux_mean']) ** 2 - b['flux_var'])
    sens = c.par.Beatsens.eval()
    thresh = b['flux_mean'] + (3.2 - 2.4 * sens) * (b['flux_var'] ** 0.5)
    hit = flux > thresh and bass > 0.15 * b['peak'] and now - b['last_hit'] > 0.22

    if hit:
        b['last_hit'] = now
        b['hits'] = [t for t in b['hits'] if now - t < 8.0] + [now]
        bpm = _tempo(b['hits'])
        if bpm:
            b['bpm'] = bpm if b['bpm'] is None else b['bpm'] + 0.25 * (bpm - b['bpm'])
            c.par.Bpm = round(b['bpm'], 1)

    if mode == 'hits':
        # each kick fires one pulse that fades over half a beat
        period = 60.0 / (b['bpm'] or c.par.Bpm.eval())
        b['phase'] = min(1.0, (now - b['last_hit']) / max(period, 0.2))
    else:
        # tempo: steady clock at the detected BPM, pulled into line by each kick
        period = 60.0 / max(c.par.Bpm.eval(), 1.0)
        if hit:
            ph = ((now - b['anchor']) / period) % 1.0
            if ph < 0.3 or ph > 0.7:
                b['anchor'] = now                      # close to a beat: snap to it
        b['phase'] = ((now - b['anchor']) / period) % 1.0
    c.par.Beatphase = b['phase']


def next_autobeat():
    c = C()
    p = c.par.Autobeat
    names = list(p.menuNames)
    p.val = names[(names.index(p.eval()) + 1) % len(names)]
    say('Auto beat: ' + p.menuLabels[p.menuIndex])



# ---------- drop ----------
# Press G (or the Drop button) when the drop lands: everything goes wild for a
# few bars in time with the BPM, then eases back to exactly how it was.
# The Drop page sets how long, how wild, which style and what else changes.

DROP_STYLES = {
    # par: value at full drop. A function gets the beat count and returns a value.
    'chaos': {'Pulse': 1.0, 'Rgbsplit': 0.6, 'Bloom': 0.7, 'Warp': 0.9, 'Glow': 0.8, 'Zoom': 0.6,
              'Spin': 0.5, 'Huespeed': 0.8, 'Intensity': 1.0, 'Kaleido': 6, 'Grain': 0.3,
              'Huerotate': lambda beat: (beat * 0.125) % 1.0},
    'glitch': {'Pulse': 1.0, 'Rgbsplit': 0.9, 'Pixelate': 0.5, 'Scanlines': 0.7, 'Posterize': 0.5,
               'Grain': 0.5, 'Warp': 0.6},
    'kaleido': {'Pulse': 0.8, 'Kaleido': 8, 'Mirror': 3, 'Spin': 0.8, 'Zoom': 0.7, 'Bloom': 0.5,
                'Glow': 0.6, 'Huespeed': 0.5},
    'colour': {'Pulse': 1.0, 'Bloom': 0.6, 'Glow': 0.9, 'Huespeed': 1.0, 'Videosat': 2.0,
               'Intensity': 1.0, 'Huerotate': lambda beat: (beat * 0.25) % 1.0,
               'Videohue': lambda beat: (beat * 0.0625) % 1.0},
    'warp': {'Pulse': 0.8, 'Warp': 1.0, 'React': 1.0, 'Zoom': -0.6, 'Spin': -0.5, 'Rgbsplit': 0.3,
             'Bloom': 0.4, 'Videoblend': 3},
}
_drop = {'on': False, 'start': 0.0, 'saved': {}, 'beat': -1}


def _beat_len():
    return 60.0 / max(C().par.Bpm.eval(), 1.0)


def trigger_drop():
    """Start a drop, or end the current one early (it still eases back)."""
    c = C()
    now = absTime.seconds
    if _drop['on']:
        bars = c.par.Dropbars.eval()
        held = (now - _drop['start']) / (_beat_len() * 4)
        if held < bars:                                  # jump to the ease-back
            _drop['start'] = now - bars * 4 * _beat_len()
        return
    style = DROP_STYLES.get(c.par.Dropstyle.eval(), DROP_STYLES['chaos'])
    names = set(style) | {'Look', 'Videoblend'}
    _drop.update(on=True, start=now, beat=-1,
                 saved={n: getattr(c.par, n).eval() for n in names if getattr(c.par, n, None) is not None})
    say('DROP! {} for {} bars'.format(c.par.Dropstyle.eval(), c.par.Dropbars.eval()))


def _set(par, value):
    if par.isMenu:
        par.menuIndex = int(round(value)) % len(par.menuNames)
    elif par.isInt:
        par.val = int(round(value))
    elif par.isToggle:
        par.val = bool(value >= 0.5)
    else:
        par.val = value


def drop_frame(c, now):
    if not _drop['on']:
        return
    beat_len = _beat_len()
    beats = (now - _drop['start']) / beat_len
    hold = c.par.Dropbars.eval() * 4
    ease = c.par.Dropreturn.eval() * 4
    amount = c.par.Dropamount.eval()
    if beats < hold:
        e = 1.0
    elif beats < hold + ease and ease > 0:
        x = (beats - hold) / ease
        e = 1.0 - x * x * (3 - 2 * x)                    # smooth ease back
    else:
        e = 0.0

    if e <= 0.0:
        for n, v in _drop['saved'].items():               # back to exactly how it was
            p = getattr(c.par, n, None)
            if p is not None:
                try:
                    p.val = v
                except Exception:
                    pass
        _drop['on'] = False
        c.par.Dropstate = ''
        say('Drop finished')
        return

    style = DROP_STYLES.get(c.par.Dropstyle.eval(), DROP_STYLES['chaos'])
    for n, target in style.items():
        p = getattr(c.par, n, None)
        if p is None or n not in _drop['saved']:
            continue
        base = _drop['saved'][n]
        if p.isMenu:
            base = p.menuNames.index(base) if base in p.menuNames else 0
        tv = target(beats) if callable(target) else target
        if p.isMenu or p.isInt or p.isToggle:
            _set(p, tv if e * amount > 0.5 else base)
        else:
            _set(p, float(base) + (tv - float(base)) * e * amount)

    # things that happen on the beat while the drop is held
    whole = int(beats)
    if beats < hold and whole != _drop['beat']:
        _drop['beat'] = whole
        every = {'off': 0, 'bar': 4, 'half': 2, 'beat': 1}.get(c.par.Dropcuts.eval(), 0)
        if every and whole > 0 and whole % every == 0:
            next_clip(fade=False)
        if c.par.Droplooks.eval() and whole > 0 and whole % 4 == 0:
            next_look()
    if beats < hold:
        c.par.Dropstate = 'DROP  bar {} of {}'.format(int(beats // 4) + 1, int(hold // 4))
    else:
        c.par.Dropstate = 'easing back'
    if beats >= hold and 'Look' in _drop['saved'] and c.par.Droplooks.eval():
        c.par.Look = _drop['saved']['Look']             # land back on your look as it eases out


def on_frame():
    c = C()
    now = absTime.seconds
    try:
        beat_frame(c, now)
    except Exception as e:
        if not _beat.get('err'):
            say('Audio beat detection problem: {}'.format(e))
            _beat['err'] = True
    try:
        drop_frame(c, now)
    except Exception as e:
        _drop['on'] = False
        say('Drop problem: {}'.format(e))
    if not _vid['started']:
        if int(absTime.frame) % 120 == 0:               # retry now and then until clips appear
            next_clip(fade=False)
        return
    if _vid['fading']:
        x = min(1.0, (now - _vid['fade_start']) / max(c.par.Fadetime.eval(), 0.05))
        c.par.Videoxfade = x if _vid['to'] == 1 else 1.0 - x
        if x >= 1.0:
            _vid.update(fading=False, deck=_vid['to'], clip_start=_vid['fade_start'])
    elif now - _vid['clip_start'] > clip_seconds(_vid['current'], c):
        next_clip()


def clip_seconds(entry, c):
    """How long to show a clip: its own length (finishing the crossfade as it ends), or Cliplength."""
    if c.par.Wholeclip.eval():
        try:
            dur = float((entry or {}).get('duration_s') or 0)
        except (TypeError, ValueError):
            dur = 0
        if dur > 0:
            return max(2.0, dur - c.par.Fadetime.eval())
    return c.par.Cliplength.eval()


def reload_library():
    _vid['mtime'] = None
    say(library_summary())
    next_clip()


# ---------- input routing ----------

def find_ai_mask(quiet=False):
    """Point Aimask at the MediaPipe plugin's segmentation image, wherever it was dropped in."""
    c = C()
    jam = J()
    best = None
    for o in op('/').findChildren(type=TOP, maxDepth=6):
        if o.path.startswith(jam.path + '/'):
            continue
        n = o.path.lower()
        if o.name == 'seg_data' or 'segment' in n or 'mask' in n and 'mediapipe' in n:
            score = (o.name == 'seg_data') * 10 + ('mediapipe' in n) * 2 + ('out' in o.name.lower()) + (o.name.lower().endswith('segmentation'))
            if best is None or score > best[0]:
                best = (score, o)
    if best:
        c.par.Aimask = best[1].path
        c.par.Source = 'ai'
        say('AI mask: using ' + best[1].path)
    elif not quiet:
        say('No AI mask found. Drop the MediaPipe plugin into the project, turn on its segmentation, then press Find AI mask.')
    return best is not None


def on_pulse(name):
    actions = {
        'Calibrate': calibrate,
        'Clearbg': clear_background,
        'Savepreset': save_preset,
        'Loadpreset': lambda: apply_preset(int(C().par.Slot)),
        'Randomize': randomize,
        'Blackout': toggle_blackout,
        'Fullscreen': toggle_fullscreen,
        'Nextclip': next_clip,
        'Reloadlib': reload_library,
        'Drop': trigger_drop,
        'Findai': find_ai_mask,
    }
    if name in actions:
        actions[name]()


def on_key(channel_name):
    key = channel_name[-1:].lower()
    if key.isdigit() and key != '0':
        apply_preset(int(key))
    elif key == 'r':
        randomize()
    elif key == 'c':
        calibrate()
    elif key == 'x':
        clear_background()
    elif key == 'd':
        toggle_debug()
    elif key == 'b':
        toggle_blackout()
    elif key == 'f':
        toggle_fullscreen()
    elif key == 'l':
        next_look()
    elif key == 'v':
        next_clip()
    elif key == 'm':
        next_blend()
    elif key == 'a':
        next_autobeat()
    elif key == 'g':
        trigger_drop()
