// look7_crystal.glsl
// A stained-glass mosaic that shatters into tiny shards wherever people stand.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Shape = shard size. Glow = lead line thickness. Warp = bodies bend the glass.

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

// Returns (distance to nearest cell centre, distance to edge, cell id hash)
vec3 voronoi(vec2 p, float t)
{
    vec2 n = floor(p), f = fract(p);
    float d1 = 8.0, d2 = 8.0, id = 0.0;
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 g = vec2(float(i), float(j));
        float h = hash21(n + g);
        vec2 o = 0.5 + 0.4 * sin(t + 6.2831 * vec2(h, hash21(n + g + 7.7)));
        float d = length(g + o - f);
        if (d < d1) { d2 = d1; d1 = d; id = h; } else if (d < d2) { d2 = d; }
    }
    return vec3(d1, d2 - d1, id);
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
    vec2 g = bodyGrad(uv, 3.0);

    // Glass shards: big cells in empty space, tiny shattered cells over people
    vec2 p = (uv - 0.5) * vec2(aspect, 1.0);
    p = rot(t * spin * 0.05) * p;
    p *= mix(4.0, 12.0, shape) * (1.0 + m * 1.5) * (1.0 + zoom * 0.3 * sin(t * 0.2));
    p += g * warp * 6.0;
    vec3 v = voronoi(p, t * (0.2 + intensity * 0.8));

    float h = fract(hue + t * hueSpeed * 0.1 + v.z * 0.25 + m * 0.3);
    vec3 cellCol = hsv2rgb(vec3(h, 0.65, 1.0)) * (0.15 + 0.5 * v.z) * (0.3 + intensity * 0.6);
    cellCol *= 1.0 - smoothstep(0.0, 0.9, v.x) * 0.6;
    float line = 1.0 - smoothstep(0.0, 0.03 + glow * 0.05, v.y);
    vec3 col = cellCol + hsv2rgb(vec3(fract(h + 0.5), 0.4, 1.0)) * line * (0.4 + m * 1.2) * (0.5 + glow);
    col += hsv2rgb(vec3(h, 0.3, 1.0)) * m * 0.15;

    vec3 prev = texture(sTD2DInputs[1], uv).rgb;
    col = mix(col, max(col, prev * 0.92), trail);
    fragColor = TDOutputSwizzle(vec4(min(col, vec3(4.0)), 1.0));
}
