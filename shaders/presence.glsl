// presence.glsl
// Turns the raw camera image into a clean "where are people" image.
// Output: red = body mask (0..1), green = depth tone inside the near/far window.
//
// Input 0: raw source (Kinect depth, webcam or the demo dancers)
// Input 1: background snapshot (captured with the C key)

uniform vec4 uDepth;   // x Near, y Far, z Source (0 Kinect, 1 webcam, 2 demo), w Mirror
uniform vec4 uBg;      // x Use background, y Sensitivity

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
        float l = dot(src.rgb, vec3(0.299, 0.587, 0.114));
        if (source == 1 && useBg) {
            // Webcam: anything that differs from the empty room snapshot
            float thr = mix(0.35, 0.06, sens);
            mask = smoothstep(thr, thr * 1.5, length(src.rgb - bg.rgb));
        } else {
            mask = smoothstep(0.35, 0.65, l);
        }
        tone = l;
    }

    fragColor = TDOutputSwizzle(vec4(mask, tone * mask, 0.0, 1.0));
}
