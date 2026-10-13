// composite.glsl
// Puts the camera look on top of the video library.
//
// Input 0: the current look
// Input 1: presence (red = body mask, green = depth tone)
// Input 2: video deck A
// Input 3: video deck B

uniform float uTime;
uniform vec4 uVid;    // x Video amount, y A/B crossfade, z Blend mode, w React
uniform vec4 uVid2;   // x Video hue shift, y Video saturation, z Look amount

layout(location = 0) out vec4 fragColor;

vec3 hueShift(vec3 col, float a)
{
    const vec3 k = vec3(0.57735);
    float c = cos(a);
    return col * c + cross(k, col) * sin(a) + k * dot(k, col) * (1.0 - c);
}

// Fill the frame with a video, cropping rather than stretching
vec2 fillUV(vec2 uv, vec2 srcRes)
{
    vec2 dstRes = uTDOutputInfo.res.zw;
    float sa = srcRes.x / max(srcRes.y, 1.0);
    float da = dstRes.x / dstRes.y;
    vec2 c = uv - 0.5;
    if (da > sa) c.y *= sa / da; else c.x *= da / sa;
    return c + 0.5;
}

vec3 video(vec2 uv)
{
    vec3 a = texture(sTD2DInputs[2], fillUV(uv, uTD2DInfos[2].res.zw)).rgb;
    vec3 b = texture(sTD2DInputs[3], fillUV(uv, uTD2DInfos[3].res.zw)).rgb;
    return mix(a, b, clamp(uVid.y, 0.0, 1.0));
}

void main()
{
    vec2 uv = vUV.st;
    float amount = uVid.x;
    int mode = int(uVid.z + 0.5);
    float react = uVid.w;
    float lookAmt = uVid2.z;

    vec3 look = texture(sTD2DInputs[0], uv).rgb;
    float m = texture(sTD2DInputs[1], uv).r;

    // Bodies push the video around (React). Mode 3 pushes much harder.
    vec2 px = uTD2DInfos[1].res.xy * 4.0;
    vec2 g = vec2(texture(sTD2DInputs[1], uv + vec2(px.x, 0.0)).r - texture(sTD2DInputs[1], uv - vec2(px.x, 0.0)).r,
                  texture(sTD2DInputs[1], uv + vec2(0.0, px.y)).r - texture(sTD2DInputs[1], uv - vec2(0.0, px.y)).r);
    float lumL = dot(look, vec3(0.333));
    vec2 push = g * react * (mode == 3 ? 0.25 : 0.05) + (mode == 3 ? vec2(sin(lumL * 6.0), cos(lumL * 6.0)) * react * 0.02 : vec2(0.0));
    vec3 v = video(uv - push);

    float grey = dot(v, vec3(0.299, 0.587, 0.114));
    v = mix(vec3(grey), v, uVid2.y);
    v = hueShift(v, uVid2.x * 6.28318) * amount;
    vec3 l = clamp(look * lookAmt, 0.0, 1.5);

    vec3 col;
    if (mode == 1) {
        col = v * m + l * (1.0 - m * 0.8);            // Reveal: video only inside people
    } else if (mode == 2) {
        col = v * (1.0 - m) + l;                      // Cutout: people cut holes in the video
    } else if (mode == 4) {
        float lum = dot(v, vec3(0.299, 0.587, 0.114)) / max(amount, 0.001);
        vec3 paint = clamp(look * 1.5, 0.0, 1.0) + 0.15;
        col = lum * paint * amount + l * 0.3;   // Paint: the look colours the video
    } else {
        col = 1.0 - (1.0 - clamp(v, 0.0, 1.0)) * (1.0 - clamp(l, 0.0, 1.0));   // Screen (0) and Warp (3)
    }
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
