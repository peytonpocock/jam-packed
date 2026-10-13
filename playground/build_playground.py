# build_playground.py
# Builds the whole reactive visuals network inside TouchDesigner.
#
# How to run (once):
#   1. Save a new TouchDesigner project as  !JamPacked/playground/playground.toe
#   2. Open the Textport (Alt+T) and paste:
#        exec(open(project.folder + '/build_playground.py').read())
#   3. Look inside /project1/jam. Re-running rebuilds it from scratch. Your
#      slider settings and webcam choice carry over, presets live in
#      presets/looks.json and the video tags in library/catalog.yaml.
#
# Every shader is linked to its .glsl file on disk, so editing a shader file
# updates the visuals live.

import os

ROOT = project.folder.replace('\\', '/')            # .../!JamPacked/playground
REPO = os.path.dirname(ROOT)
SHADERS = REPO + '/shaders'
PRESETS = REPO + '/presets/looks.json'
LIBDIR = REPO + '/library'
VIDEOS = REPO + '/Videos'
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
    """Wire srcs into dst's inputs 0, 1, 2... in order, then check it worked."""
    for i, s in enumerate(srcs):
        conns = dst.inputConnectors
        if i >= len(conns):
            # some ops only grow a new empty slot after they cook
            try:
                dst.cook(force=True)
            except Exception:
                pass
            conns = dst.inputConnectors
        if i < len(conns):
            conns[i].connect(s)
        else:
            s.outputConnectors[0].connect(dst)
    got = [o.name if o else None for o in dst.inputs]
    want = [s.name for s in srcs]
    if got[:len(want)] != want:
        warn('{} inputs are {}, expected {}'.format(dst.name, got, want))


# ------------------------------------------------------------------ network

LOOKS = [
    ('neon', 'Neon ghosts', 'look1_neon_ghosts.glsl'),
    ('liquid', 'Liquid', 'look2_liquid.glsl'),
    ('kaleido', 'Kaleido tunnel', 'look3_kaleido_tunnel.glsl'),
    ('echo', 'Chroma echo', 'look4_chroma_echo.glsl'),
    ('embers', 'Embers', 'look5_embers.glsl'),
    ('thermal', 'Thermal', 'look6_thermal.glsl'),
    ('crystal', 'Crystal', 'look7_crystal.glsl'),
    ('glitch', 'Glitch', 'look8_glitch.glsl'),
]

host = op('/project1') or op('/')
old = host.op('jam')
saved, saved_device = {}, None
if old:
    oc = old.op('controls')
    if oc:
        for p in oc.customPars:
            if not p.isPulse and p.name not in ('Usebg', 'Videoxfade', 'Nowplaying'):
                saved[p.name] = p.eval()
    ow = old.op('src_webcam')
    if ow is not None and getattr(ow.par, 'device', None) is not None:
        saved_device = ow.par.device.eval()
    log('Removing the previous build (keeping your slider settings)')
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


def menu(page, name, label, names, labels, default=None):
    p = page.appendMenu(name, label=label)[0]
    p.menuNames = names
    p.menuLabels = labels
    p.default = default or names[0]
    p.val = p.default
    return p


menu(pg, 'Look', 'Look (L)', [k for k, _, _ in LOOKS],
     ['{}  {}'.format(i + 1, n) for i, (_, n, _) in enumerate(LOOKS)])
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
pg.appendInt('Slot', label='Preset slot')[0].normMax = 20
c.par.Slot = 1
c.par.Slot.min = 1
c.par.Slot.clampMin = True
pg.appendPulse('Loadpreset', label='Load preset')
pg.appendPulse('Savepreset', label='Save preset')

# Video library page
pv = c.appendCustomPage('Video')
fl('Videomix', 'Video amount', 0.8, page=pv)
fl('Lookmix', 'Look amount', 1.0, 0.0, 1.5, page=pv)
menu(pv, 'Videoblend', 'Blend mode (M)', ['screen', 'reveal', 'cutout', 'warp', 'paint'],
     ['Screen: look over video', 'Reveal: video inside people', 'Cutout: people cut holes',
      'Warp: people bend the video', 'Paint: look colours the video'])
fl('React', 'Bodies push video', 0.3, page=pv)
fl('Videohue', 'Video hue shift', 0.0, page=pv)
fl('Videosat', 'Video saturation', 1.0, 0.0, 2.0, page=pv)
fl('Cliplength', 'Seconds per clip', 15.0, 3.0, 60.0, page=pv)
fl('Fadetime', 'Crossfade seconds', 2.0, 0.0, 8.0, page=pv)
pv.appendInt('Energymin', label='Energy from')[0].normMin = 1
pv.appendInt('Energymax', label='Energy to')[0].normMax = 5
for n, v in (('Energymin', 1), ('Energymax', 5)):
    p = getattr(c.par, n)
    p.normMin, p.normMax, p.min, p.max = 1, 5, 1, 5
    p.clampMin = p.clampMax = True
    p.default = v
    p.val = v
menu(pv, 'Orientation', 'Orientation', ['any', 'horizontal', 'vertical'], ['Any', 'Horizontal', 'Vertical'])
menu(pv, 'Usefor', 'Playing on', ['any', 'backdrop', 'totem'], ['Anything', 'Backdrop', 'Totem'])
pv.appendStr('Tags', label='Only tags (comma list)')
pv.appendPulse('Nextclip', label='Next clip (V)')
pv.appendPulse('Reloadlib', label='Reload catalog')
pv.appendStr('Nowplaying', label='Now playing')
c.par.Nowplaying.readOnly = True
fl('Videoxfade', 'A/B fade (automatic)', 0.0, page=pv)

# Effects page: post-processing over the whole picture, all off at 0
pf = c.appendCustomPage('FX')
fl('Bloom', 'Bloom', 0.0, page=pf)
fl('Rgbsplit', 'RGB split', 0.0, page=pf)
fl('Scanlines', 'Scanlines', 0.0, page=pf)
fl('Pixelate', 'Pixelate', 0.0, page=pf)
menu(pf, 'Mirror', 'Mirror', ['off', 'lr', 'tb', 'quad'], ['Off', 'Left / right', 'Top / bottom', 'Quad'])
pf.appendInt('Kaleido', label='Kaleido segments (0 off)')
c.par.Kaleido.normMax = 12
c.par.Kaleido.min = 0
c.par.Kaleido.clampMin = True
c.par.Kaleido.default = 0
fl('Posterize', 'Posterize', 0.0, page=pf)
fl('Pulse', 'Beat pulse', 0.0, page=pf)
fl('Bpm', 'BPM', 124.0, 60.0, 180.0, page=pf)
fl('Invert', 'Invert', 0.0, page=pf)
fl('Huerotate', 'Hue rotate', 0.0, page=pf)
fl('Vignette', 'Vignette', 0.3, page=pf)
fl('Grain', 'Grain', 0.0, page=pf)

pc = c.appendCustomPage('Camera')
menu(pc, 'Source', 'Source', ['kinect', 'webcam', 'demo'], ['Kinect', 'Webcam', 'Demo dancers'], 'webcam')
pc.appendToggle('Flip', label='Mirror camera')
c.par.Flip = True
pc.appendPulse('Calibrate', label='Capture empty room (C)')
pc.appendPulse('Clearbg', label='Clear room capture (X)')
pc.appendToggle('Usebg', label='Use room capture')
fl('Sensitivity', 'Sensitivity', 0.5, page=pc)
fl('Near', 'Near', 0.0, 0.0, 10.0, page=pc)
fl('Far', 'Far', 10.0, 0.0, 10.0, page=pc)
c.par.Far = 10.0
pc.appendToggle('Debug', label='Show body mask (D)')
pc.appendPulse('Fullscreen', label='Output window (F)')

# Put back what you had before the rebuild
for name, val in saved.items():
    p = getattr(c.par, name, None)
    if p is not None and not p.readOnly:
        try:
            p.val = val
        except Exception:
            pass
if 'Mirror' in saved and isinstance(saved['Mirror'], (bool, int)) and 'Flip' not in saved:
    c.par.Flip = bool(saved['Mirror'])                # the camera mirror toggle used to be called Mirror
    c.par.Mirror = 'off'

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


def P(name):
    return "op('controls').par.{}".format(name)


def M(name):
    return "op('controls').par.{}.menuIndex".format(name)


# ---- Sources
k = jam.create(kinectTOP, 'src_kinect')
setmenu(k, 'hwversion', 'version2', 'Kinect 2', '2')
setmenu(k, 'image', 'depth', 'Depth')
place(k, 0, 0)

cam = jam.create(videodeviceinTOP, 'src_webcam')
place(cam, 0, 1)
if saved_device:
    setpar(cam, 'device', saved_device)

demo = glsl(jam, 'src_demo', 'demo_people.glsl', 0, 2, PRES_W, PRES_H)
set_uniforms(demo, [('uTime', ['absTime.seconds', 0, 0, 0])])
place(demo, 0, 2)
jam.op('src_demo_pixel').nodeY = -3 * 150 - 200

srcsw = jam.create(switchTOP, 'src_switch')
connect(srcsw, k, cam, demo)
setexpr(srcsw, 'index', M('Source'))
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
    ('uDepth', [P('Near'), P('Far'), M('Source'), P('Flip')]),
    ('uBg', [P('Usebg'), P('Sensitivity'), 0, 0]),
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
place(blank, 4, 4)

look_uniforms = [
    ('uTime', ['absTime.seconds', 0, 0, 0]),
    ('uA', [S('Intensity'), S('Hue'), S('Huespeed'), S('Trail')]),
    ('uB', [S('Warp'), S('Glow'), S('Shape'), S('Zoom')]),
    ('uC', [S('Spin'), 0, 0, 0]),
]
looks = []
for i, (_, _, f) in enumerate(LOOKS):
    y = i * 1.6 - 4
    fb = jam.create(feedbackTOP, 'fb{}'.format(i + 1))
    connect(fb, blank)
    place(fb, 5, y)
    g = glsl(jam, 'look{}'.format(i + 1), f, 6, y, OUT_W, OUT_H, float_fmt=True)
    connect(g, blur, fb)
    setpar(fb, 'top', g.name)
    set_uniforms(g, look_uniforms)
    looks.append(g)
    jam.op('look{}_pixel'.format(i + 1)).nodeX = 6 * 200 + 160
    jam.op('look{}_pixel'.format(i + 1)).nodeY = g.nodeY

looksw = jam.create(switchTOP, 'look_switch')
connect(looksw, *looks)
setpar(looksw, 'blend', True)                        # crossfade between looks
setexpr(looksw, 'index', S('Look') if have_ctrl else M('Look'))
place(looksw, 7, 1)

# ---- Video library: two decks that crossfade, driven by engine.py
decks = []
for i, name in enumerate(('vid_a', 'vid_b')):
    d = jam.create(moviefileinTOP, name)
    setpar(d, 'play', True)
    for pn in ('extendright', 'extend'):   # name differs between TD builds; movies loop by default anyway
        if getattr(d.par, pn, None) is not None:
            setmenu(d, pn, 'loop', 'Loop')
            break
    place(d, 7, 3 + i)
    decks.append(d)

comp = glsl(jam, 'composite', 'composite.glsl', 8, 1, OUT_W, OUT_H)
connect(comp, looksw, blur, decks[0], decks[1])
set_uniforms(comp, [
    ('uTime', ['absTime.seconds', 0, 0, 0]),
    ('uVid', [S('Videomix'), P('Videoxfade'), M('Videoblend'), S('React')]),
    ('uVid2', [S('Videohue'), S('Videosat'), S('Lookmix'), 0]),
])

post = glsl(jam, 'post', 'post.glsl', 9, 1, OUT_W, OUT_H)
connect(post, comp)
set_uniforms(post, [
    ('uTime', ['absTime.seconds', 0, 0, 0]),
    ('uFx1', [S('Bloom'), S('Rgbsplit'), S('Scanlines'), S('Pixelate')]),
    ('uFx2', [M('Mirror'), S('Posterize'), S('Pulse'), S('Invert')]),
    ('uFx3', [S('Vignette'), S('Grain'), P('Kaleido'), S('Huerotate')]),
    ('uFx4', [P('Bpm'), 0, 0, 0]),
])

viewsw = jam.create(switchTOP, 'view_switch')
connect(viewsw, post, blur)
setexpr(viewsw, 'index', P('Debug'))
place(viewsw, 10, 1)

final = glsl(jam, 'final', 'master.glsl', 11, 1, OUT_W, OUT_H)
connect(final, viewsw)
set_uniforms(final, [('uMaster', [S('Master'), 0, 0, 0])])

out = jam.create(nullTOP, 'out')
connect(out, final)
place(out, 12, 1)
out.viewer = True

win = jam.create(windowCOMP, 'window1')
setpar(win, 'winop', out.path)
setpar(win, 'borders', False)
place(win, 12, -1)

# ---- Logic: engine, slider buttons, keyboard, per-frame video playlist
eng = jam.create(textDAT, 'engine')
code = open(ROOT + '/engine.py').read()
code = code.replace("JAM = '/project1/jam'", "JAM = {!r}".format(jam.path))
code = code.replace("PRESETS = ''", "PRESETS = {!r}".format(PRESETS))
code = code.replace("LIBDIR = ''", "LIBDIR = {!r}".format(LIBDIR))
code = code.replace("VIDEOS = ''", "VIDEOS = {!r}".format(VIDEOS))
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
setpar(kb, 'keys', '1 2 3 4 5 6 7 8 9 r c x d b f l v m')
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

fe = jam.create(executeDAT, 'frame_exec')
for p in ('start', 'create', 'exit', 'frameend', 'playstatechange', 'devicechange'):
    if getattr(fe.par, p, None) is not None:
        setpar(fe, p, False)
setpar(fe, 'framestart', True)
fe.text = "def onFrameStart(frame):\n    op('engine').module.on_frame()\n    return\n"
place(fe, 4, -4)

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
        e = o.errors() or ''
        w = o.warnings() or ''
        if 'compile' in w.lower():
            e = (e + ' ' + w).strip()
        if e and o.name not in ('src_kinect', 'src_webcam', 'vid_a', 'vid_b'):
            bad.append('{}: {} inputs={}'.format(o.name, e, [i.name if i else None for i in o.inputs]))
            if o.isTOP and o.OPType == 'glslTOP' and not any('compile log' in b for b in bad):
                info = jam.create(infoDAT, 'diag_info')
                info.par.op = o.path
                info.cook(force=True)
                bad.append('compile log for {}:\n{}'.format(o.name, info.text[:1500]))
                info.destroy()
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
    log(jam.op('engine').module.library_summary())


run("args[0]()", _report, delayFrames=30)
log('Done building. Checking for errors in a moment...')
