# build_playground.py
# Builds the whole reactive visuals network inside TouchDesigner.
#
# How to run (once):
#   1. Save a new TouchDesigner project as  !JamPacked/playground/playground.toe
#   2. Open the Textport (Alt+T) and paste:
#        exec(open(project.folder + '/build_playground.py').read())
#   3. Look inside /project1/jam. Re-running rebuilds it from scratch
#      (your presets are safe, they live in presets/looks.json).
#
# Every shader is linked to its .glsl file on disk, so editing a shader file
# updates the visuals live.

import os

ROOT = project.folder.replace('\\', '/')            # .../!JamPacked/playground
REPO = os.path.dirname(ROOT)
SHADERS = REPO + '/shaders'
PRESETS = REPO + '/presets/looks.json'
OUT_W, OUT_H = 1280, 720                            # Non-Commercial caps output at 1280
PRES_W, PRES_H = 640, 360

problems = []


def log(msg):
    print('[build] ' + msg)


def warn(msg):
    problems.append(msg)
    log('WARNING ' + msg)


def setpar(o, name, value):
    p = getattr(o.par, name, None)
    if p is None:
        warn('{} has no parameter "{}"'.format(o.name, name))
        return False
    try:
        p.val = value
        return True
    except Exception as e:
        warn('{}.{} = {!r} failed: {}'.format(o.name, name, value, e))
        return False


def setexpr(o, name, expr):
    p = getattr(o.par, name, None)
    if p is None:
        warn('{} has no parameter "{}"'.format(o.name, name))
        return
    p.expr = expr


def setmenu(o, name, *wants):
    """Pick a menu entry by exact name first, then by partial match on name or label."""
    p = getattr(o.par, name, None)
    if p is None:
        warn('{} has no parameter "{}"'.format(o.name, name))
        return False
    names = list(p.menuNames)
    labels = list(p.menuLabels)
    for w in wants:
        if w in names:
            p.val = w
            return True
    for w in wants:
        for n, l in zip(names, labels):
            if w.lower() in n.lower() or w.lower() in l.lower():
                p.val = n
                return True
    warn('{}.{}: none of {} in {}'.format(o.name, name, wants, names))
    return False


def place(o, x, y):
    o.nodeX, o.nodeY = x * 200, -y * 150


def shader_dat(net, name, filename, x, y):
    d = net.create(textDAT, name)
    path = SHADERS + '/' + filename
    setpar(d, 'file', path)
    if getattr(d.par, 'syncfile', None) is not None:
        d.par.syncfile = True                        # live reload when the file changes
    else:
        d.text = open(path).read()
    place(d, x, y)
    return d


def glsl(net, name, filename, x, y, w, h, float_fmt=False):
    g = net.create(glslTOP, name)
    dat = shader_dat(net, name + '_pixel', filename, x, y + 1)
    g.par.pixeldat = dat.name
    setmenu(g, 'outputresolution', 'custom')
    setpar(g, 'resolutionw', w)
    setpar(g, 'resolutionh', h)
    if float_fmt:
        setmenu(g, 'format', 'rgba16float', '16-bit float (RGBA)', '16float')
    place(g, x, y)
    return g


def set_uniforms(g, uniforms):
    """uniforms: list of (name, [x, y, z, w]); items may be numbers or expression strings."""
    new_style = getattr(g.par, 'vec0name', None) is not None
    if new_style:
        try:
            g.seq.vec.numBlocks = max(g.seq.vec.numBlocks, len(uniforms))
        except Exception as e:
            warn('{}: could not add uniform slots: {}'.format(g.name, e))
    for i, (uname, vals) in enumerate(uniforms):
        if new_style:
            namep = getattr(g.par, 'vec{}name'.format(i), None)
            comps = [getattr(g.par, 'vec{}value{}'.format(i, c), None) for c in 'xyzw']
        else:
            namep = getattr(g.par, 'uniname{}'.format(i), None)
            comps = [getattr(g.par, 'value{}{}'.format(i, c), None) for c in 'xyzw']
        if namep is None:
            warn('{}: no uniform slot {} for {}'.format(g.name, i, uname))
            continue
        namep.val = uname
        for p, v in zip(comps, vals):
            if p is None or v is None:
                continue
            if isinstance(v, str):
                p.expr = v
            else:
                p.val = v


def connect(dst, *srcs):
    for i, s in enumerate(srcs):
        dst.inputConnectors[i].connect(s)


# ------------------------------------------------------------------ network

host = op('/project1') or op('/')
old = host.op('jam')
if old:
    log('Removing the previous build')
    old.destroy()
jam = host.create(containerCOMP, 'jam')
jam.nodeX, jam.nodeY = 0, 0
log('Building in ' + jam.path)

# ---- Controls: every on-screen slider. MIDI will write to these same parameters later.
c = jam.create(baseCOMP, 'controls')
place(c, 0, -2)
pg = c.appendCustomPage('Look')


def fl(name, label, default, lo=0.0, hi=1.0, page=None):
    p = (page or pg).appendFloat(name, label=label)[0]
    p.normMin, p.normMax = lo, hi
    p.default = default
    p.val = default
    return p


look = pg.appendMenu('Look', label='Look')[0]
look.menuNames = ['neon', 'liquid', 'kaleido']
look.menuLabels = ['1  Neon ghosts', '2  Liquid', '3  Kaleido tunnel']
fl('Intensity', 'Intensity', 0.7)
fl('Hue', 'Hue', 0.55)
fl('Huespeed', 'Hue speed', 0.15)
fl('Trail', 'Trail', 0.8)
fl('Warp', 'Warp', 0.4)
fl('Glow', 'Glow', 0.3)
fl('Shape', 'Shape', 0.2)
fl('Zoom', 'Zoom', 0.25, -1.0, 1.0)
fl('Spin', 'Spin', 0.05, -1.0, 1.0)
fl('Master', 'Master', 1.0)
pg.appendPulse('Randomize', label='Randomize (R)')
pg.appendPulse('Blackout', label='Blackout (B)')
pg.appendInt('Slot', label='Preset slot')[0].normMax = 9
c.par.Slot = 1
c.par.Slot.min = 1
c.par.Slot.clampMin = True
pg.appendPulse('Loadpreset', label='Load preset')
pg.appendPulse('Savepreset', label='Save preset')

pc = c.appendCustomPage('Camera')
src = pc.appendMenu('Source', label='Source')[0]
src.menuNames = ['kinect', 'webcam', 'demo']
src.menuLabels = ['Kinect', 'Webcam', 'Demo dancers']
c.par.Source = 'webcam'
pc.appendToggle('Mirror', label='Mirror')
c.par.Mirror = True
pc.appendPulse('Calibrate', label='Capture empty room (C)')
pc.appendPulse('Clearbg', label='Clear room capture (X)')
pc.appendToggle('Usebg', label='Use room capture')
fl('Sensitivity', 'Sensitivity', 0.5, page=pc)
fl('Near', 'Near', 0.0, 0.0, 10.0, page=pc)
fl('Far', 'Far', 10.0, 0.0, 10.0, page=pc)
c.par.Far = 10.0
pc.appendToggle('Debug', label='Show body mask (D)')
pc.appendPulse('Fullscreen', label='Output window (F)')

# Smoothed copies of the sliders, so preset changes and MIDI glide instead of jump
ctrl_raw = jam.create(parameterCHOP, 'ctrl_raw')
setpar(ctrl_raw, 'ops', c.path)
setpar(ctrl_raw, 'parameters', '*')
setpar(ctrl_raw, 'custom', True)
setpar(ctrl_raw, 'builtin', False)
place(ctrl_raw, 1, -2)
ctrl = jam.create(filterCHOP, 'ctrl')
connect(ctrl, ctrl_raw)
setpar(ctrl, 'width', 0.4)
place(ctrl, 2, -2)
ctrl.cook(force=True)
try:
    have_ctrl = 'Intensity' in [ch.name for ch in ctrl.chans()]
except Exception:
    have_ctrl = False
if not have_ctrl:
    warn('Smoothing CHOP has no channels, wiring the sliders directly instead')


def S(name):
    return "op('ctrl')['{}']".format(name) if have_ctrl else "op('controls').par.{}".format(name)


# ---- Sources
k = jam.create(kinectTOP, 'src_kinect')
setmenu(k, 'hwversion', 'version2', 'Kinect 2', '2')
setmenu(k, 'image', 'depth', 'Depth')
place(k, 0, 0)

cam = jam.create(videodeviceinTOP, 'src_webcam')
place(cam, 0, 1)

demo = glsl(jam, 'src_demo', 'demo_people.glsl', 0, 2, PRES_W, PRES_H)
set_uniforms(demo, [('uTime', ['absTime.seconds', 0, 0, 0])])
place(demo, 0, 2)
jam.op('src_demo_pixel').nodeY = -3 * 150 - 200

srcsw = jam.create(switchTOP, 'src_switch')
connect(srcsw, k, cam, demo)
setexpr(srcsw, 'index', "op('controls').par.Source.menuIndex")
place(srcsw, 1, 1)

bg = jam.create(cacheTOP, 'bg')
connect(bg, srcsw)
setpar(bg, 'cachesize', 1)
setpar(bg, 'active', True)                           # grab one frame so it is never empty
run("op('{}').par.active = False".format(bg.path), delayFrames=5)
place(bg, 2, 2)

# ---- Body mask
pres = glsl(jam, 'presence', 'presence.glsl', 3, 1, PRES_W, PRES_H, float_fmt=True)
connect(pres, srcsw, bg)
set_uniforms(pres, [
    ('uDepth', ["op('controls').par.Near", "op('controls').par.Far",
                "op('controls').par.Source.menuIndex", "op('controls').par.Mirror"]),
    ('uBg', ["op('controls').par.Usebg", "op('controls').par.Sensitivity", 0, 0]),
])
blur = jam.create(blurTOP, 'presence_blur')
connect(blur, pres)
setpar(blur, 'size', 4)
place(blur, 4, 1)

# ---- Looks, each with its own feedback loop
blank = jam.create(constantTOP, 'blank')
setmenu(blank, 'outputresolution', 'custom')
setpar(blank, 'resolutionw', OUT_W)
setpar(blank, 'resolutionh', OUT_H)
setmenu(blank, 'format', 'rgba16float', '16-bit float (RGBA)', '16float')
for ch in ('colorr', 'colorg', 'colorb'):
    setpar(blank, ch, 0)
setpar(blank, 'alpha', 1)
place(blank, 4, 3)

look_uniforms = [
    ('uTime', ['absTime.seconds', 0, 0, 0]),
    ('uA', [S('Intensity'), S('Hue'), S('Huespeed'), S('Trail')]),
    ('uB', [S('Warp'), S('Glow'), S('Shape'), S('Zoom')]),
    ('uC', [S('Spin'), 0, 0, 0]),
]
looks = []
for i, f in enumerate(['look1_neon_ghosts.glsl', 'look2_liquid.glsl', 'look3_kaleido_tunnel.glsl']):
    fb = jam.create(feedbackTOP, 'fb{}'.format(i + 1))
    connect(fb, blank)
    place(fb, 5, i * 2 - 1)
    g = glsl(jam, 'look{}'.format(i + 1), f, 6, i * 2 - 1, OUT_W, OUT_H, float_fmt=True)
    connect(g, blur, fb)
    setpar(fb, 'top', g.name)
    set_uniforms(g, look_uniforms)
    looks.append(g)
    jam.op('look{}_pixel'.format(i + 1)).nodeX = 6 * 200 + 160
    jam.op('look{}_pixel'.format(i + 1)).nodeY = g.nodeY

looksw = jam.create(switchTOP, 'look_switch')
connect(looksw, *looks)
setpar(looksw, 'blend', True)                        # crossfade between looks
setexpr(looksw, 'index', S('Look') if have_ctrl else "op('controls').par.Look.menuIndex")
place(looksw, 7, 1)

viewsw = jam.create(switchTOP, 'view_switch')
connect(viewsw, looksw, blur)
setexpr(viewsw, 'index', "op('controls').par.Debug")
place(viewsw, 8, 1)

final = glsl(jam, 'final', 'master.glsl', 9, 1, OUT_W, OUT_H)
connect(final, viewsw)
set_uniforms(final, [('uMaster', [S('Master'), 0, 0, 0])])

out = jam.create(nullTOP, 'out')
connect(out, final)
place(out, 10, 1)
out.viewer = True

win = jam.create(windowCOMP, 'window1')
setpar(win, 'winop', out.path)
setpar(win, 'borders', False)
place(win, 10, -1)

# ---- Logic: engine, slider buttons, keyboard
eng = jam.create(textDAT, 'engine')
code = open(ROOT + '/engine.py').read()
code = code.replace("JAM = '/project1/jam'", "JAM = {!r}".format(jam.path))
code = code.replace("PRESETS = ''", "PRESETS = {!r}".format(PRESETS))
eng.text = code
place(eng, 0, -4)

pe = jam.create(parameterexecuteDAT, 'controls_exec')
setpar(pe, 'op', c.path)
setpar(pe, 'pars', '*')
setpar(pe, 'onpulse', True)
setpar(pe, 'valuechange', False)
pe.text = "def onPulse(par):\n    op('engine').module.on_pulse(par.name)\n    return\n"
place(pe, 1, -4)

kb = jam.create(keyboardinCHOP, 'keys')
setpar(kb, 'keys', '1 2 3 4 5 6 7 8 9 r c x d b f')
place(kb, 2, -4)
ke = jam.create(chopexecuteDAT, 'keys_exec')
setpar(ke, 'chop', kb.name)
setpar(ke, 'offtoon', True)
for p in ('ontooff', 'whileon', 'whileoff', 'valuechange'):
    setpar(ke, p, False)
ke.text = ("def onOffToOn(channel, sampleIndex, val, prev):\n"
           "    op('engine').module.on_key(channel.name)\n"
           "    return\n")
place(ke, 3, -4)

# Show the output inside the jam container and open the slider panel
jam.par.w, jam.par.h = OUT_W // 2, OUT_H // 2
try:
    jam.viewer = True
    c.openParameters()
except Exception:
    pass


def _report():
    bad = []
    for o in jam.children:
        e = o.errors()
        if e and o.name not in ('src_kinect', 'src_webcam'):
            bad.append('{}: {}'.format(o.name, e))
    for m in problems:
        log('setup note: ' + m)
    if bad:
        log('ERRORS (send these to Claude):')
        for b in bad:
            log('  ' + b)
    else:
        log('All shaders compiled. You should see the visuals in jam/out.')
    for name in ('src_kinect', 'src_webcam'):
        e = jam.op(name).errors()
        if e:
            log('{} says: {} (fine if that device is not plugged in yet)'.format(name, e))


run("args[0]()", _report, delayFrames=30)
log('Done building. Checking for errors in a moment...')
