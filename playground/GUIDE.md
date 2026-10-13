# Kinect visuals playground: tonight's setup guide

Goal for tonight: the Kinect sees people, three shader looks react to them, and a
handful of sliders (future MIDI faders) change the vibe.

## What's in the kit

```
!JamPacked/
  shaders/
    presence.glsl             turns the Kinect image into a clean body mask
    look1_neon_ghosts.glsl    neon outlines with swirling smoke trails
    look2_liquid.glsl         flowing liquid colour that people push around
    look3_kaleido_tunnel.glsl outlines mirrored into a kaleidoscope tunnel
    demo_people.glsl          fake dancers, so you can play before the Kinect works
    master.glsl               overall brightness / blackout
  presets/looks.json          6 starting presets (keys 1 to 6)
  playground/
    build_playground.py       builds the whole TouchDesigner network for you
    engine.py                 presets, keyboard shortcuts, calibration
```

## Step 1: Kinect drivers (Windows)

**Which Kinect is it?** Check the label underneath.
- *Kinect for Xbox One* (v2, the boxy one): you need the Kinect Adapter for Windows
  (a power brick with a USB 3 cable).
- *Kinect for Xbox 360* (v1, the long thin one): you need its power/USB adapter
  cable. Tell me if this is yours and I'll switch the build to v1.

**For v2:**
1. Install **Kinect for Windows SDK 2.0** (Microsoft download, file name
   `KinectSDK-v2.0_1409-Setup.exe`). Restart afterwards.
2. Plug the adapter's power into the wall and its USB into a **USB 3** port
   on the PC (blue inside, or marked SS). The light on the adapter box should be on.
3. Windows will spend a minute installing devices. Then open **Kinect Studio v2.0**
   (Start menu), click the plug icon top left to connect, and you should see
   the depth image. If it connects, you're done here. Close Kinect Studio.
4. If it won't connect: run **Kinect Configuration Verifier** (also in the Start
   menu). A yellow warning on "USB Controller" is common and usually fine; red on
   USB means try another USB 3 port (rear ports on the motherboard work best).

**For v1:** install **Kinect for Windows SDK 1.8**, plug in, and check with
the "Developer Toolkit Browser" depth samples.

## Step 2: TouchDesigner

1. Install TouchDesigner from derivative.ca and sign in with a free account
   (Non-Commercial is fine; it caps output at 1280 wide, which is what we use).
2. Open TouchDesigner, then **File > Save As** into
   `!JamPacked/playground/` and name it `playground.toe`.
   (The build script finds the shaders relative to where this file is saved.)
3. Open the **Textport** with **Alt+T** and paste this line, then press Enter:

   ```
   exec(open(project.folder + '/build_playground.py').read())
   ```

4. After a second the Textport says either *"All shaders compiled"* or lists
   errors. If there are errors, paste the whole Textport output to me in the
   thread and I'll fix it.
5. Double click the new **jam** node to go inside. The **out** node shows the
   result. It starts on your **webcam**. Until you capture the empty room (Step 3) it just reacts to bright areas. Click **controls** and
   press **P** if the slider panel isn't open: those are your faders.

## Step 3: camera setup (webcam now, Kinect later)

**Webcam:** press **C**, step out of view within 3 seconds, and come back. Now only people light up, with simulated depth shading. Use **Sensitivity** if bits of the room show up or parts of you go missing. Not working? Set Source to **Demo dancers** to keep playing.

**Kinect (once its USB issue is fixed):**

1. On the **controls** node, open the **Camera** page and set **Source** to **Kinect**.
2. Press **D** (or tick *Show body mask*) to see what the Kinect thinks is a person.
   Right now the whole room probably lights up. That's expected.
3. Press **C**, then **walk out of view within 3 seconds**. It snapshots the
   empty room. Walk back in: now only you should light up.
4. Background specks showing up? Lower **Sensitivity**. Parts of you missing?
   Raise it. Moved the Kinect or furniture? Press **C** again.
5. Press **D** again to go back to the visuals.

If **src_kinect** shows a red error: check Kinect Studio is closed, then on
src_kinect make sure *Hardware Version* is Kinect 2 and *Image* is Depth.

## Step 4: play

| Key | What it does |
|---|---|
| 1 to 9 | presets (Neon ghosts, Neon smoke, Liquid ember, Liquid lagoon, Kaleido tunnel, Mandala rush, Chroma echo, Embers, Crystal) |
| L | next look |
| V | next video clip |
| M | next video blend mode |
| R | randomize everything |
| B | blackout on/off (trails keep running underneath) |
| F | open/close the output window |
| D | show the body mask |
| C | capture the empty room (3 second countdown) |
| X | clear the room capture |

The keys work when the **output window** has focus (press F, click on it).
In the network editor some letters are TouchDesigner shortcuts, so use the
slider panel there instead.

**Sliders (the future MIDI faders):** Intensity, Hue, Hue speed, Trail, Warp,
Glow, Shape, Zoom, Spin, Master. They glide smoothly to new values, so preset
changes crossfade instead of jumping. Shape means something different per look:
trail colour drift (neon), swirl size (liquid), number of mirror segments (kaleido).

**Saving your own looks:** tweak the sliders, set **Preset slot**, press
**Save preset**. It writes to `presets/looks.json`. Slots 10 to 14 hold more
starters (Thermal, Glitch, and three video combos); 15 and up are free.

**Projector:** select **window1**, set *Monitor* to the projector, then press F.

## Step 5: videos and effects

**Adding videos:** drop clips into `!JamPacked/Videos/originals`, then ask Claude
to scan them (or run `python library/tools/scan.py` if you have Python and
ffmpeg). Each clip gets an entry in `library/catalog.yaml` with its orientation,
length, a guessed energy (1 to 5), pace, brightness, colours and tags. Edit any of
those by hand; the scanner never overwrites your changes. Press **Reload catalog**
on the Video page to pick up changes.

**Video page:** the player picks random clips that match your filters (energy
range, orientation, where it's playing, tags) and crossfades every few seconds.
Blend modes (**M** cycles them):

| Mode | What it does |
|---|---|
| Screen | the camera look glows over the video |
| Reveal | the video only shows inside people's silhouettes |
| Cutout | people cut holes in the video |
| Warp | people bend and push the video around |
| Paint | the look's colours paint the video |

**FX page:** bloom, RGB split, scanlines, pixelate, mirror, kaleidoscope,
posterize, beat pulse (set the BPM), invert, hue rotate, vignette and grain. All
off at 0, and presets switch off any effect they don't use.

**8 looks:** Neon ghosts, Liquid, Kaleido tunnel, Chroma echo, Embers, Thermal,
Crystal, Glitch. **L** cycles through them.

## Tomorrow: setup tips

- Put the Kinect at about waist to chest height, with people 1.5 to 4 m away.
  It works in the dark (it uses infrared), so you can kill the lights.
- Do the **C** capture once everything is set up and the space is empty.
- Shiny surfaces, mirrors and direct sunlight confuse it.
- If the Kinect plays up mid party, switch Source to **Demo dancers** or
  **Webcam** and it keeps going.

## Later: MIDI

Every slider lives on the **controls** node, and the visuals only read from
there. Hooking up the fader box later means adding a MIDI In CHOP that writes
into those same parameters, so presets, smoothing and the keyboard all keep working.

## Auto beat from the mic or PC audio

On the FX page, **Auto beat** (key A) makes the Beat pulse follow the music:

- **Off**: pulses at the BPM slider.
- **Hits**: one pulse on every kick drum.
- **Tempo**: works out the BPM (the slider moves on its own) and pulses in time, staying locked to the kicks.

Turn **Beat pulse** up to see it. **Bass level** shows what it hears, and **Beat sensitivity** catches more or fewer hits.

It listens to the `audio_in` node, which starts on your default recording device (the mic). To use what the PC is playing instead, open Windows Sound settings, Recording tab, right click, Show disabled devices, enable **Stereo Mix**, then pick it in `audio_in`'s Device menu.

## Drops

Press **G** (or **DROP!** on the Drop page) as the drop lands. Everything goes wild in time with the BPM for a few bars, then eases back to exactly how you had it. Press G again to end it early.

- **Style**: Chaos, Glitch, Kaleido, Colour or Warp.
- **Bars**: how long it lasts (4 by default).
- **How wild**: how far the sliders get pushed.
- **Ease back**: how many bars it takes to settle.
- **Video cuts**: hard cuts to new clips every bar, every 2 beats or every beat.
- **Change look every bar**: cycles the looks, then lands back on yours.

It uses the BPM slider for timing, so it's tightest with Auto beat on Tempo.

## AI body mask (MediaPipe)

A neural net finds people instead of comparing against the empty room, so it copes with moving lights, crowds and people standing still. It runs on any GPU (including AMD).

1. Download **release.zip** of the free **MediaPipe TouchDesigner** plugin (github.com/torinmb/mediapipe-touchdesigner, Releases, not the green Code button) and unzip it into `!JamPacked/plugins/release/`. The real `MediaPipe.tox` is about 180 MB.
2. Drag `toxes/MediaPipe.tox` into `/project1` (not inside `jam`) and tick **Enable External .tox**. Pick your webcam, turn every detector off except **Image segmentation**, and turn **Show overlays** off.
3. On the Camera page press **Find AI mask**. It points the mask at MediaPipe's output and switches Source to the AI body mask.
4. Once MediaPipe is linked it owns the webcam (Windows only lets one program use it). Webcam mode then reads MediaPipe's plain camera picture, and the playground switches MediaPipe's segmentation on in AI mode and off in the others by itself. MediaPipe already mirrors the picture, so leave **Mirror camera** off.
5. If people show up inverted or blank, try **AI mask is in**: Brightness, Alpha or Red. **Sensitivity** moves the edge in or out.
