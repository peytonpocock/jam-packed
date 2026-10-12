// look3_kaleido_tunnel.glsl
// People leave glowing outlines that get mirrored into a kaleidoscope and pour
// outward down an endless tunnel.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Shape = number of mirror segments (3 to 12). Zoom = tunnel speed.
// Warp = how much the kaleidoscope centre wanders.
// Intensity also sets the pulse rate.

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

    // People drawn where they really are
    float m = body(uv);
    float edge = clamp(length(bodyGrad(uv, 1.5 + glow * 5.0)) * 2.5, 0.0, 1.0);

    // Fold the previous frame into mirrored wedges, then pull it outward (the tunnel).
    // Anything drawn gets copied around the circle and streams away from the centre.
    vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
    c += vec2(sin(t * 0.3), cos(t * 0.23)) * warp * 0.04;
    float segs = floor(mix(3.0, 12.0, shape) + 0.5);
    float sector = 6.28318 / segs;
    float r = length(c);
    float a = atan(c.y, c.x) + t * spin * 0.2;
    a = mod(a, sector);
    a = abs(a - sector * 0.5);
    vec2 k = vec2(cos(a), sin(a)) * r;
    k = rot(0.01 + spin * 0.02) * k * (0.97 - zoom * 0.04);
    vec3 prev = texture(sTD2DInputs[1], k / vec2(aspect, 1.0) + 0.5).rgb;
    vec3 straight = texture(sTD2DInputs[1], c * (0.97 - zoom * 0.04) / vec2(aspect, 1.0) + 0.5).rgb;
    prev = mix(straight, prev, 0.85);
    prev = hueShift(prev, 0.03 + hueSpeed * 0.1);
    prev *= mix(0.65, 0.92, trail) * (1.0 - 0.1 * r);

    float beat = 0.75 + 0.25 * sin(t * (1.0 + intensity * 6.0));
    float h = fract(hue + t * hueSpeed * 0.1 + r * 0.5);
    vec3 now = hsv2rgb(vec3(h, 0.9, 1.0)) * (edge * (0.8 + glow * 1.5) + m * 0.2) * (0.5 + intensity) * beat;

    vec3 col = min(max(prev, now), vec3(4.0));
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
