// look8_glitch.glsl
// Broken-signal look: bodies split into RGB, slices tear sideways, blocks pixelate.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Intensity = how often it glitches. Warp = how far slices tear.
// Shape = slice count. Glow = RGB split.

// Shared controls (same on every look, so one set of faders drives them all)
uniform float uTime;
uniform vec4 uA;   // x Intensity, y Hue, z Hue speed, w Trail
uniform vec4 uB;   // x Warp, y Glow, z Shape, w Zoom
uniform vec4 uC;   // x Spin

layout(location = 0) out vec4 fragColor;

vec3 hsv2rgb(vec3 c)
{
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

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

float vnoise(vec2 p)
{
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
               mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p)
{
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * vnoise(p);
        p = p * 2.03 + 17.1;
        a *= 0.5;
    }
    return v;
}

mat2 rot(float a)
{
    float c = cos(a);
    float s = sin(a);
    return mat2(c, -s, s, c);
}

float body(vec2 uv)
{
    return texture(sTD2DInputs[0], uv).r;
}

vec2 bodyGrad(vec2 uv, float radius)
{
    vec2 px = uTD2DInfos[0].res.xy * radius;
    return vec2(body(uv + vec2(px.x, 0.0)) - body(uv - vec2(px.x, 0.0)),
                body(uv + vec2(0.0, px.y)) - body(uv - vec2(0.0, px.y)));
}

void main()
{
    vec2 uv = vUV.st;
    float intensity = uA.x, hue = uA.y, hueSpeed = uA.z, trail = uA.w;
    float warp = uB.x, glow = uB.y, shape = uB.z, zoom = uB.w;
    float spin = uC.x;
    float t = uTime;
    vec2 res = uTDOutputInfo.res.zw;

    // Horizontal slices jump sideways at random moments (Intensity = how often)
    float rows = mix(12.0, 80.0, shape);
    float row = floor(uv.y * rows);
    float tick = floor(t * (2.0 + intensity * 14.0));
    float r1 = hash21(vec2(row, tick));
    float jump = (r1 > 1.0 - intensity * 0.5) ? (hash21(vec2(row, tick + 3.1)) - 0.5) * warp * 0.25 : 0.0;
    vec2 guv = vec2(uv.x + jump, uv.y);

    // Blocky pixelation on some frames
    float blocky = step(0.85, hash21(vec2(tick, 9.0)));
    vec2 block = vec2(16.0, 9.0) * mix(4.0, 12.0, hash21(vec2(tick, 4.0)));
    guv = mix(guv, (floor(guv * block) + 0.5) / block, blocky * intensity);

    float split = (0.003 + glow * 0.012) * (1.0 + abs(jump) * 20.0);
    float mr = body(guv + vec2(split, 0.0));
    float mg = body(guv);
    float mb = body(guv - vec2(split, 0.0));
    float edge = clamp(length(bodyGrad(guv, 1.5)) * 2.5, 0.0, 1.0);

    float h = fract(hue + t * hueSpeed * 0.1);
    vec3 tint = hsv2rgb(vec3(h, 0.7, 1.0));
    vec3 col = vec3(mr, mg, mb) * mix(vec3(1.0), tint, 0.5) * (0.4 + intensity * 0.6);
    col += tint * edge * 0.8;

    // Old frames smear and slide down the slices
    vec2 fuv = vec2(uv.x + jump * 0.3, uv.y - zoom * 0.004);
    fuv = (fuv - 0.5) * (1.0 + spin * 0.01) + 0.5;
    vec3 prev = texture(sTD2DInputs[1], fuv).rgb * mix(0.6, 0.95, trail);
    col = max(col, prev);
    col *= 0.85 + 0.15 * step(0.5, fract(uv.y * res.y * 0.25));    // scanlines
    fragColor = TDOutputSwizzle(vec4(min(col, vec3(4.0)), 1.0));
}
