// look6_thermal.glsl
// Thermal camera: people glow hot white and orange through cold purples, and
// leave a fading heat print where they've been.
//
// Input 0: presence (red = body mask, green = depth tone)
// Input 1: feedback (this shader's previous frame, heat kept in alpha)
//
// Glow = size of the heat halo. Shape = contour bands. Warp = heat shimmer.

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

vec3 heat(float x)
{
    // black > deep blue > purple > red > orange > yellow > white
    x = clamp(x, 0.0, 1.0);
    vec3 c = mix(vec3(0.0, 0.0, 0.08), vec3(0.15, 0.0, 0.5), smoothstep(0.0, 0.2, x));
    c = mix(c, vec3(0.75, 0.0, 0.35), smoothstep(0.2, 0.4, x));
    c = mix(c, vec3(1.0, 0.35, 0.0), smoothstep(0.4, 0.62, x));
    c = mix(c, vec3(1.0, 0.85, 0.1), smoothstep(0.62, 0.82, x));
    return mix(c, vec3(1.0), smoothstep(0.82, 1.0, x));
}

void main()
{
    vec2 uv = vUV.st;
    float intensity = uA.x, hue = uA.y, hueSpeed = uA.z, trail = uA.w;
    float warp = uB.x, glow = uB.y, shape = uB.z, zoom = uB.w;
    float spin = uC.x;
    float t = uTime;
    vec2 res = uTDOutputInfo.res.zw;

    // Bodies are hottest in the middle (closest), cooling toward the outline
    vec2 wob = vec2(fbm(uv * 6.0 + t * 0.5), fbm(uv * 6.0 - t * 0.4)) - 0.5;
    vec2 suv = uv + wob * warp * 0.01;
    vec4 pres = texture(sTD2DInputs[0], suv);
    float m = pres.r;
    float closeness = m * (1.0 - pres.g * 0.8);
    float halo = 0.0;
    for (int i = 0; i < 8; i++) {
        float a = float(i) * 0.785398;
        halo += body(suv + vec2(cos(a), sin(a)) * uTD2DInfos[0].res.xy * (6.0 + glow * 20.0));
    }
    halo /= 8.0;
    float heatNow = max(closeness * (0.6 + intensity * 0.5), halo * 0.35 * (0.5 + glow));

    // Heat lingers where people were, slowly rising
    vec2 fuv = (uv - 0.5) * (1.0 - zoom * 0.004) + 0.5 + vec2(0.0, 0.0008);
    float prevHeat = texture(sTD2DInputs[1], fuv).a * mix(0.85, 0.985, trail);
    float h = max(heatNow, prevHeat);

    // Shape = contour bands, Hue/Hue speed rotate the palette
    float bands = mix(1.0, 0.75 + 0.25 * step(0.5, fract(h * 12.0)), shape);
    vec3 col = heat(h * bands);
    col = hueShift(col, (hue - 0.55 + t * hueSpeed * 0.1) * 6.28318);
    col *= 0.9 + 0.1 * sin(uv.y * res.y * 1.5 + t * 4.0);              // faint scanlines
    col += vec3(0.0, 0.01, 0.03) * vnoise(uv * res * 0.5 + t * 50.0);   // sensor noise
    // alpha carries the raw heat so the colour mapping never compounds
    fragColor = TDOutputSwizzle(vec4(col, h));
}
