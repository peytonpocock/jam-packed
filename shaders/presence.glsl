// presence.glsl
// Turns the raw camera image into a clean "where are people" image.
// Output: red = body mask (0..1), green = depth tone inside the near/far window.
//
// Input 0: raw source (Kinect depth, webcam, demo dancers or an AI body mask)
// Input 1: background snapshot (captured with the C key)
// Input 2: AI body mask (used by the hybrid source, which also needs the plain camera on input 0)

uniform vec4 uDepth;   // x Near, y Far, z Source (0 Kinect, 1 webcam, 2 demo, 3 AI mask, 4 hybrid), w Mirror
uniform vec4 uBg;      // x Use background, y Sensitivity, z AI mask channel (0 brightness, 1 alpha, 2 red)
uniform vec4 uHy;      // hybrid: x combine (0 either, 1 both, 2 mix, 3 AI + room edges), y mix weight (0 AI .. 1 room), z room sensitivity

layout(location = 0) out vec4 fragColor;

// Fill the output frame with the source image, cropping instead of stretching.
vec2 fillUV(vec2 uv, vec2 srcRes)
{
    vec2 dstRes = uTDOutputInfo.res.zw;
    float sa = srcRes.x / srcRes.y;
    float da = dstRes.x / dstRes.y;
    vec2 c = uv - 0.5;
    if (da > sa) c.y *= sa / da; else c.x *= da / sa;
    return c + 0.5;
}

// AI matte: Sensitivity moves the cut-off
float aiMask(vec4 m, float sens)
{
    int ch = int(uBg.z + 0.5);
    float v = ch == 1 ? m.a : (ch == 2 ? m.r : dot(m.rgb, vec3(0.299, 0.587, 0.114)));
    float mid = mix(0.75, 0.25, sens);
    return smoothstep(mid - 0.15, mid + 0.15, v);
}

// Anything that differs from the empty room snapshot
float roomMask(vec3 cam, vec3 bg, float sens)
{
    float thr = mix(0.35, 0.06, sens);
    return smoothstep(thr, thr * 1.5, length(cam - bg));
}

// Body mask for the webcam, demo, AI and hybrid sources (no real depth available).
float camMask(vec2 uv, int source, bool useBg, float sens)
{
    vec4 src = texture(sTD2DInputs[0], uv);
    if (source == 3)
        return aiMask(src, sens);
    if (source == 4) {
        float a = aiMask(texture(sTD2DInputs[2], uv), sens);
        float r = roomMask(src.rgb, texture(sTD2DInputs[1], uv).rgb, clamp(uHy.z, 0.0, 1.0));
        int mode = int(uHy.x + 0.5);
        if (mode == 0) return max(a, r);                       // either one sees you
        if (mode == 1) return min(a, r);                       // both have to agree
        if (mode == 2) return mix(a, r, clamp(uHy.y, 0.0, 1.0));
        // AI shape, plus whatever the room capture finds right next to it (arms, hair, props)
        float near = 0.0;
        vec2 px = uTD2DInfos[2].res.xy * 12.0;
        for (int k = 0; k < 8; k++) {
            float ang = float(k) * 0.785398;
            near = max(near, aiMask(texture(sTD2DInputs[2], uv + vec2(cos(ang), sin(ang)) * px), sens));
        }
        return max(a, r * near * clamp(uHy.y * 2.0, 0.0, 1.0));
    }
    if (source == 1 && useBg)
        return roomMask(src.rgb, texture(sTD2DInputs[1], uv).rgb, sens);
    float l = dot(src.rgb, vec3(0.299, 0.587, 0.114));
    return smoothstep(0.35, 0.65, l);
}

void main()
{
    vec2 uv = vUV.st;
    if (uDepth.w > 0.5) uv.x = 1.0 - uv.x;
    uv = fillUV(uv, uTD2DInfos[0].res.zw);

    vec4 src = texture(sTD2DInputs[0], uv);
    vec4 bg = texture(sTD2DInputs[1], uv);
    bool useBg = uBg.x > 0.5;
    float sens = clamp(uBg.y, 0.0, 1.0);
    int source = int(uDepth.z + 0.5);

    float mask = 0.0;
    float tone = 0.0;

    if (source == 0) {
        // Kinect depth. Works whatever units the depth comes in, because
        // near/far are set by calibration and the background test is relative.
        float d = src.r;
        float nearD = uDepth.x;
        float farD = max(uDepth.y, uDepth.x + 1e-5);
        float soft = (farD - nearD) * 0.03 + 1e-6;
        float valid = step(1e-6, d);
        float inWindow = smoothstep(nearD - soft, nearD + soft, d)
                       * (1.0 - smoothstep(farD - soft, farD + soft, d));
        mask = valid * inWindow;
        if (useBg && bg.r > 1e-6) {
            float diff = abs(d - bg.r) / bg.r;
            float thr = mix(0.12, 0.02, sens);
            mask *= smoothstep(thr, thr * 1.6, diff);
        }
        tone = clamp((d - nearD) / (farD - nearD), 0.0, 1.0);
    } else {
        // Simulated depth: the deeper inside a silhouette a pixel is, the
        // "closer" it counts as, so bodies get rounded 3D-ish shading like the
        // Kinect gives. Same output format, so the Kinect can swap straight in.
        mask = camMask(uv, source, useBg, sens);
        vec2 px = uTD2DInfos[0].res.xy;
        float inner = 0.0;
        for (int ring = 1; ring <= 3; ring++) {
            float r = float(ring) * 7.0;
            for (int k = 0; k < 8; k++) {
                float a = float(k) * 0.785398 + float(ring) * 0.4;
                inner += camMask(uv + vec2(cos(a), sin(a)) * px * r, source, useBg, sens);
            }
        }
        inner /= 24.0;
        tone = 1.0 - inner;
    }

    fragColor = TDOutputSwizzle(vec4(mask, tone * mask, 0.0, 1.0));
}
