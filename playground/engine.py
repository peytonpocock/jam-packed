# engine.py
# Runtime logic for the playground: presets, keyboard shortcuts, calibration.
# The build script loads this file into a Text DAT called "engine" inside the
# "jam" network. Edit it here; press R in the build Text DAT or re-run the
# build to pick up changes.

import json
import os
import random

# Filled in by build_playground.py
JAM = '/project1/jam'
PRESETS = ''

LOOK_PARS = ['Intensity', 'Hue', 'Huespeed', 'Trail', 'Warp', 'Glow', 'Shape', 'Zoom', 'Spin']
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
    c.par.Look.menuIndex = int(p.get('Look', 0))
    for name in LOOK_PARS:
        if name in p:
            getattr(c.par, name).val = p[name]
    c.par.Slot = int(slot)
    say('Preset {}: {}'.format(slot, p.get('name', '')))


def save_preset():
    c = C()
    slot = str(int(c.par.Slot))
    data = load_presets()
    old = data.get(slot, {})
    p = {'name': old.get('name', 'Preset ' + slot), 'Look': c.par.Look.menuIndex}
    for name in LOOK_PARS:
        p[name] = round(float(getattr(c.par, name).eval()), 3)
    data[slot] = p
    with open(PRESETS, 'w') as f:
        json.dump(data, f, indent=2)
    say('Saved preset {} ({}). Rename it in presets/looks.json if you like.'.format(slot, p['name']))


def randomize():
    c = C()
    c.par.Look.menuIndex = random.randint(0, 2)
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
