// post.glsl
// Effects applied to the whole picture at the end, each with its own slider.
// Every effect is off at 0.
//
// Input 0: the composited picture

uniform float uTime;
uniform vec4 uFx1;   // x Bloom, y RGB split, z Scanlines, w Pixelate
uniform vec4 uFx2;   // x Mirror (0 off, 1 left/right, 2 top/bottom, 3 quad), y Posterize, z Pulse, w Invert
uniform vec4 uFx3;   // x Vignette, y Grain, z Kaleido segments (0 off), w Hue rotate
uniform vec4 uFx4;   // x BPM, y beat phase from audio, z auto beat (0 off, 1 hits, 2 tempo)

layout(location = 0) out vec4 fragColor;

vec3 hueShift(vec3 col, float a)
{
    const vec3 k = vec3(0.57735);
    float c = cos(a);
    return col * c + cross(k, col) * sin(a) + k * dot(k, col) * (1.0 - c);
}

float hash21(vec2 p)
{
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

vec3 img(vec2 uv)
{
    return texture(sTD2DInputs[0], uv).rgb;
}

void main()
{
    vec2 uv = vUV.st;
    vec2 res = uTDOutputInfo.res.zw;
    float aspect = res.x / res.y;
    float t = uTime;

    // Mirror
    int mirror = int(uFx2.x + 0.5);
    if (mirror == 1 || mirror == 3) uv.x = 0.5 - abs(uv.x - 0.5);
    if (mirror == 2 || mirror == 3) uv.y = 0.5 - abs(uv.y - 0.5);

    // Kaleidoscope
    float segs = floor(uFx3.z + 0.5);
    if (segs >= 2.0) {
        vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
        float sector = 6.28318 / segs;
        float a = mod(atan(c.y, c.x) + t * 0.05, sector);
        a = abs(a - sector * 0.5);
        uv = vec2(cos(a), sin(a)) * length(c) / vec2(aspect, 1.0) + 0.5;
    }

    // Pixelate
    if (uFx1.w > 0.001) {
        vec2 cells = vec2(aspect, 1.0) * mix(240.0, 18.0, uFx1.w);
        uv = (floor(uv * cells) + 0.5) / cells;
    }

    // RGB split, stronger toward the edges
    vec2 dir = (uv - 0.5) * uFx1.y * 0.04 + vec2(uFx1.y * 0.004, 0.0);
    vec3 col = vec3(img(uv + dir).r, img(uv).g, img(uv - dir).b);

    // Bloom: soft glow around bright areas
    if (uFx1.x > 0.001) {
        vec3 glow = vec3(0.0);
        vec2 px = 1.0 / res;
        for (int ring = 1; ring <= 3; ring++) {
            float r = float(ring * ring) * 4.0;
            for (int k = 0; k < 8; k++) {
                float a = float(k) * 0.785398 + float(ring);
                vec3 s = img(uv + vec2(cos(a), sin(a)) * px * r);
                glow += max(s - 0.45, 0.0);
            }
        }
        col += glow / 24.0 * uFx1.x * 3.0;
    }

    // Posterize
    if (uFx2.y > 0.001) {
        float levels = mix(24.0, 3.0, uFx2.y);
        col = floor(col * levels + 0.5) / levels;
    }

    col = hueShift(col, uFx3.w * 6.28318);
    col = mix(col, 1.0 - clamp(col, 0.0, 1.0), uFx2.w);

    // Pulse: a smooth brightness throb on the beat (no hard strobe)
    float beat = uFx4.z > 0.5 ? clamp(uFx4.y, 0.0, 1.0) : fract(t * max(uFx4.x, 1.0) / 60.0);
    col *= 1.0 + uFx2.z * (pow(1.0 - beat, 3.0) * 0.9 - 0.25);

    // Scanlines, vignette, grain
    col *= 1.0 - uFx1.z * 0.35 * (0.5 + 0.5 * sin(vUV.t * res.y * 3.14159));
    vec2 vc = (vUV.st - 0.5) * vec2(aspect, 1.0);
    col *= 1.0 - uFx3.x * smoothstep(0.35, 1.0, length(vc));
    col += (hash21(vUV.st * res + fract(t) * 91.7) - 0.5) * uFx3.y * 0.25;

    fragColor = TDOutputSwizzle(vec4(max(col, 0.0), 1.0));
}
