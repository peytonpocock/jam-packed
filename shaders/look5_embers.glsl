// look5_embers.glsl
// People throw off glowing sparks that drift upward like embers from a fire.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame)
//
// Intensity = how many sparks. Zoom = rise speed (negative sinks).
// Warp = sideways wind. Shape = colour change as they rise.

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
    vec2 res = uTDOutputInfo.res.zw;

    float m = body(uv);
    float edge = clamp(length(bodyGrad(uv, 1.5)) * 2.5, 0.0, 1.0);

    // Sparks: random pixels on the outlines ignite each frame
    vec2 cell = floor(uv * res / 2.0);
    float rnd = hash21(cell + floor(t * 30.0) * 17.31);
    float density = mix(0.97, 0.80, intensity);
    float spark = step(density, rnd) * edge;
    spark = max(spark, step(0.995, rnd) * m * glow);       // a few from inside bodies too

    // Old sparks float upward (Zoom sets the speed, negative sinks them),
    // wobbling sideways through a noise wind (Warp)
    float wind = (fbm(uv * 4.0 + vec2(0.0, t * 0.3)) - 0.5) * 2.0;
    vec2 vel = vec2(wind * warp * 0.004, 0.0015 + zoom * 0.004);
    vel = rot(spin * 0.5) * vel;
    vec3 prev = texture(sTD2DInputs[1], uv - vel).rgb;
    prev *= mix(0.90, 0.985, trail);
    prev = hueShift(prev, shape * 0.05);                    // embers change colour as they rise

    float h = fract(hue + t * hueSpeed * 0.1 + rnd * 0.1);
    vec3 col = prev + hsv2rgb(vec3(h, 0.8, 1.0)) * spark * 2.0;
    col += hsv2rgb(vec3(h, 0.6, 1.0)) * edge * 0.06 * (0.3 + glow);   // faint outline
    fragColor = TDOutputSwizzle(vec4(min(col, vec3(4.0)), 1.0));
}
