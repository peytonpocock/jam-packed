// vidmix.glsl
// Crossfades the two video decks, each cropped to fill the frame.
//
// Input 0: video deck A
// Input 1: video deck B

uniform vec4 uVid;    // y A/B crossfade

layout(location = 0) out vec4 fragColor;

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

void main()
{
    vec2 uv = vUV.st;
    vec3 a = texture(sTD2DInputs[0], fillUV(uv, uTD2DInfos[0].res.zw)).rgb;
    vec3 b = texture(sTD2DInputs[1], fillUV(uv, uTD2DInfos[1].res.zw)).rgb;
    fragColor = TDOutputSwizzle(vec4(mix(a, b, clamp(uVid.y, 0.0, 1.0)), 1.0));
}
