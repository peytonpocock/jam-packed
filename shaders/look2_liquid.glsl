// look2_liquid.glsl
// A slow flowing liquid colour field that people push around as they move.
// Looks good with nobody in view too.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Shape = size of the swirls. Zoom = slow drift of the previous frame.

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
    float aspect = uTDOutputInfo.res.z / uTDOutputInfo.res.w;

    float m = body(uv);
    vec2 g = bodyGrad(uv, 2.0 + glow * 4.0);
    float edge = clamp(length(g) * 2.5, 0.0, 1.0);

    vec2 p = (uv - 0.5) * vec2(aspect, 1.0) * mix(1.5, 5.0, shape);
    p = rot(t * spin * 0.1) * p;
    p += g * warp * 4.0;                       // bodies shove the fluid
    float tt = t * (0.05 + intensity * 0.25);

    vec2 q = vec2(fbm(p + vec2(0.0, tt)), fbm(p + vec2(5.2, 1.3) - tt));
    float w = 4.0 * (0.3 + warp);
    vec2 r = vec2(fbm(p + w * q + vec2(1.7, 9.2) + tt * 0.6),
                  fbm(p + w * q + vec2(8.3, 2.8) - tt * 0.4));
    float f = fbm(p + 3.0 * r + m * 1.5);

    float h = fract(hue + t * hueSpeed * 0.1 + f * 0.35 + length(q) * 0.2);
    vec3 col = hsv2rgb(vec3(h, 0.75, 1.0)) * smoothstep(0.15, 0.9, f) * (0.35 + intensity * 0.9);
    col += hsv2rgb(vec3(fract(h + 0.5), 0.5, 1.0)) * (m * 0.35 + edge * 0.8) * (0.3 + glow);

    vec2 fuv = (uv - 0.5) * (1.0 - zoom * 0.01) + 0.5 + g * 0.01;
    vec3 prev = texture(sTD2DInputs[1], fuv).rgb;
    col = mix(col, prev, trail * 0.9);

    fragColor = TDOutputSwizzle(vec4(min(col, vec3(4.0)), 1.0));
}
