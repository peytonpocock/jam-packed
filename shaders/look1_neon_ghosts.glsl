// look1_neon_ghosts.glsl
// Glowing neon outlines of everyone in view, leaving smoky trails that swirl away.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Shape = how fast trail colours drift. Zoom = trails expand outward (+) or suck in (-).

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

    vec4 pres = texture(sTD2DInputs[0], uv);
    float m = pres.r;
    float depth = pres.g;
    float edge = clamp(length(bodyGrad(uv, 1.5 + glow * 6.0)) * 2.5, 0.0, 1.0);

    // Previous frame, swirled and pushed along a slowly moving noise flow
    vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
    c = rot(spin * 0.02) * c;
    c *= 1.0 - zoom * 0.015;
    float ang = fbm(uv * 3.0 + t * 0.1) * 12.566;
    c += vec2(cos(ang), sin(ang)) * warp * 0.006;
    vec3 prev = texture(sTD2DInputs[1], c / vec2(aspect, 1.0) + 0.5).rgb;
    prev = hueShift(prev, shape * 0.12);
    prev *= mix(0.80, 0.985, trail);

    float h = fract(hue + t * hueSpeed * 0.1 + depth * 0.4);
    vec3 edgeCol = hsv2rgb(vec3(h, 0.85, 1.0)) * edge * (0.6 + glow * 1.5);
    vec3 fillCol = hsv2rgb(vec3(fract(h + 0.5), 0.6, 1.0)) * m * 0.07;
    vec3 now = (edgeCol + fillCol) * (0.4 + intensity * 1.2);

    vec3 col = min(max(prev, now), vec3(4.0));
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
