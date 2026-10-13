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


def on_frame():
    c = C()
    now = absTime.seconds
    if not _vid['started']:
        if int(absTime.frame) % 120 == 0:               # retry now and then until clips appear
            next_clip(fade=False)
        return
    if _vid['fading']:
        x = min(1.0, (now - _vid['fade_start']) / max(c.par.Fadetime.eval(), 0.05))
        c.par.Videoxfade = x if _vid['to'] == 1 else 1.0 - x
        if x >= 1.0:
            _vid.update(fading=False, deck=_vid['to'], clip_start=now)
    elif now - _vid['clip_start'] > c.par.Cliplength.eval():
        next_clip()


def reload_library():
    _vid['mtime'] = None
    say(library_summary())
    next_clip()


# ---------- input routing ----------

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
