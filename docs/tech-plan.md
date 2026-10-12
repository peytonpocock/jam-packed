# Rave visuals: tech plan

## The recommendation

**Use TouchDesigner as the live engine for both systems, but keep everything that matters as plain text files in a git repo.** Videos are tagged in a text catalog, shaders are `.glsl` files, logic is `.py` files, and "vibes" are presets in a config file. The TouchDesigner networks themselves stay thin: they load those files and wire inputs to outputs.

This gives us the best of both:

- TouchDesigner already does the hard real time parts well: smooth multi video playback on the GPU, audio analysis, MIDI in, Kinect in, LED out, and live tweaking with a visual interface while you watch the result.
- I can read, write and review every text file directly, track changes in git, and you never have to describe a node network to me from screenshots for the parts that change most often (tags, shaders, presets, playlist rules).

## Why not the alternatives

| Option | Verdict |
|---|---|
| **Resolume Arena / Avenue** | Great for a pure VJ backdrop, but it has no real concept of a tagged library you can query, Kinect needs extra plugins, and its setups are GUI only, so it is hard for us to version or change together. Would not cover the beer garden piece well. |
| **VDMX** | Mac only, same GUI only problem, weak Kinect story. |
| **Notch** | Powerful but expensive, Windows only, and overkill here. |
| **Fully custom web stack** (browser + WebGL shaders + WebMIDI) | The most Claude friendly option, since I could write and test the whole thing. The weak spots are exactly your hardware: the Kinect needs a separate bridge program, LEDs need another bridge, and a browser is a less battle tested live playback engine. It is our fallback if TouchDesigner licensing is a blocker (see below). |
| **openFrameworks / Processing / Python** | All code, but we would rebuild video playback, MIDI mapping and LED output that TouchDesigner gives us for free, for no real gain. |

## Defaults I've picked (tell me if any are wrong)

- **OS:** Windows 11. TouchDesigner's Kinect support is Windows only, so this matters.
- **Kinect:** Xbox One Kinect (v2) with the Kinect Adapter for Windows. If yours is the older Xbox 360 one (v1), it still works in TouchDesigner, just with lower depth resolution. The label on the bottom will say which.
- **Machines:** one PC or laptop per system with a decent NVIDIA GPU, since the stage and beer garden are in different places. They share the same repo and video folder.
- **Audio for the backdrop:** a line feed from the DJ mixer's booth or record output into a small USB audio interface. Much more reliable than a mic in a loud room.
- **LEDs:** addressable strips (WS2812B or SK6812) driven by an ESP32 running WLED. TouchDesigner samples colours from the screen image and sends them over the network (Art-Net or DDP). Cheap, robust, and no custom firmware.
- **MIDI:** one controller for you (for vibe changes, something with pads and knobs, like an Akai MIDImix or Korg nanoKONTROL2) and a sturdier, simple fader box for the public on the standing unit.

## Licensing (worth checking early)

TouchDesigner Non-Commercial is free, but it caps output at 1280x1280 and is meant for non-paid use. A 1080p projector and a paid event both point to the Commercial licence, which is a one-off paid licence (it was around US$600 last I knew, so check derivative.ca for current pricing). Non-Commercial is fine for all of development; you would only need to buy before the event. If that cost is a dealbreaker, the custom web stack becomes the recommendation instead.

## The shared video library

This is the foundation both systems sit on, and it lives outside either TouchDesigner project so it can serve future projects too.

```
jam-packed-visuals/            (git repo)
  library/
    catalog.yaml               one entry per video, the tags you edit
    tools/scan.py              finds new videos, fills in what it can
  shaders/                     .glsl overlay effects, shared by both systems
  presets/vibes.yaml           named looks: shader mix, colours, energy range
  backdrop/                    TouchDesigner project for the DJ projector
  totem/                       TouchDesigner project for the beer garden unit
  shared/                      reusable TouchDesigner components (.tox)

Videos/                        (NOT in git, too big; a synced folder)
  originals/                   what you collect
  hap/                         playback copies, made by scan.py
```

A catalog entry looks like this:

```yaml
- id: neon-tunnel-01
  file: originals/neon_tunnel.mp4
  orientation: horizontal      # auto filled
  duration_s: 42               # auto filled
  resolution: 1920x1080        # auto filled
  energy: 4                    # you set, 1 (chill) to 5 (peak)
  pace: fast                   # you set: slow / medium / fast
  tags: [neon, tunnel, abstract]
  use: [backdrop, totem]       # where it is allowed to play
```

How it works:

1. You drop new videos into `Videos/originals/`.
2. You run `scan.py`. It adds an entry for each new file, auto fills orientation, length and resolution, and converts a HAP copy (a codec built for smooth, low CPU playback in TouchDesigner).
3. You fill in energy, pace and any tags, either in the YAML file or by asking me to.
4. Each system asks the catalog for what it needs, for example "horizontal, backdrop, energy 3 to 5", and builds its playlist from that. Changing a vibe preset changes the query, so the pool shifts with the night.

## System 1: DJ backdrop projector

- **Playback:** two video players crossfading, fed from the catalog query for the current vibe.
- **Audio reaction:** audio analysis splits the feed into bass, mids, highs and beat detection, which drive shader parameters (pulse, distortion, colour shift, strobe on drops).
- **Your controls:** MIDI pads switch vibe presets (warm up, build, peak, cool down), knobs ride intensity, colour and how hard the visuals react, plus a manual "next clip" and a blackout.
- **Output:** fullscreen to the projector, with a simple control window on the laptop screen.

## System 2: beer garden standing unit

- **Playback:** vertical clips from the catalog (or horizontal ones cropped), one or more screens.
- **Audience faders:** each fader maps to a shader parameter with a safe range, so nobody can make it look broken. After a minute of no input it drifts back to a default look.
- **Kinect:** body or depth data drives the overlay, for example silhouettes, particles that follow people, or ripples where someone stands. Distance from the unit can control intensity.
- **LEDs:** colours sampled from zones of the screen image, so the strips match what is on screen, with a pulse when someone moves a fader.
- **Robustness:** auto starts on boot and recovers if a cable gets yanked, since it will run unattended.

## Build order

1. **Library first.** Repo, catalog format, `scan.py`. Useful immediately and independent of the engine choice.
2. **Backdrop MVP.** Catalog driven playlist + one audio reactive shader + crossfades.
3. **Vibe presets and your MIDI controls.**
4. **Totem MVP.** Vertical playlist + faders driving shaders.
5. **LEDs** via WLED.
6. **Kinect** interaction.
7. **Hardening:** auto start, failsafes, a rehearsal run at full length.
