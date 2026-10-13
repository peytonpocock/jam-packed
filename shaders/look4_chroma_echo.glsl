// look4_chroma_echo.glsl
// Everyone leaves rainbow afterimages: red, green and blue copies lag behind
// each other in time, so movement smears into colour.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Shape = how far the colour copies split. Hue tints the freshest outline.

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

    // Three time-delayed copies of everyone, one per colour channel
    float edge = clamp(length(bodyGrad(uv, 1.0 + glow * 4.0)) * 2.5, 0.0, 1.0);
    float m = body(uv);
    float now = max(edge, m * (0.25 + glow * 0.4));

    vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
    c = rot(spin * 0.01) * c * (1.0 - zoom * 0.01);
    vec2 drift = vec2(sin(t * 0.7), cos(t * 0.5)) * warp * 0.004;
    vec2 off = vec2(0.002 + shape * 0.006, 0.0);
    vec2 base = c / vec2(aspect, 1.0) + 0.5 + drift;
    // Each colour channel of the old frames drifts a different way, so trails
    // split into red, green and blue ghosts as they age
    float decay = mix(0.82, 0.975, trail);
    vec3 prev = vec3(texture(sTD2DInputs[1], base + off).r,
                     texture(sTD2DInputs[1], base).g,
                     texture(sTD2DInputs[1], base - off).b) * decay;

    vec3 tint = hsv2rgb(vec3(fract(hue + t * hueSpeed * 0.1), 0.35, 1.0));
    vec3 col = max(prev, tint * now * (0.5 + intensity * 1.1));
    fragColor = TDOutputSwizzle(vec4(min(col, vec3(4.0)), 1.0));
}
