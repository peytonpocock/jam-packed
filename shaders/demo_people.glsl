// demo_people.glsl
// Stand-in for the Kinect: a few soft "people" wandering and waving,
// so every look can be tuned before the camera is plugged in.

uniform float uTime;

layout(location = 0) out vec4 fragColor;

float capsule(vec2 p, float h, float r)
{
    p.y -= clamp(p.y, -h, h);
    return length(p) - r;
}

void main()
{
    vec2 uv = vUV.st;
    float aspect = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
    vec2 p = (uv - 0.5) * vec2(aspect, 1.0);
    float v = 0.0;

    for (int i = 0; i < 4; i++) {
        float fi = float(i);
        float t = uTime * (0.25 + fi * 0.07) + fi * 2.1;
        vec2 c = vec2(sin(t) * 0.65, -0.05 + sin(t * 0.7 + fi) * 0.05);
        vec2 q = p - c;
        float scale = 0.85 + 0.15 * sin(fi * 3.7);
        q /= scale;

        float d = capsule(q - vec2(0.0, -0.08), 0.13, 0.07);          // torso and legs
        d = min(d, length(q - vec2(0.0, 0.17)) - 0.055);                // head
        float wave = sin(uTime * (2.0 + fi * 0.6) + fi) * 0.6;
        vec2 arm = q - vec2(0.0, 0.06);
        for (int s = -1; s <= 1; s += 2) {
            float side = float(s);
            float a = 0.4 + wave * side;
            vec2 dir = vec2(side * cos(a), sin(a));
            float along = clamp(dot(arm, dir), 0.0, 0.17);
            d = min(d, length(arm - dir * along) - 0.025);              // arms
        }
        v = max(v, smoothstep(0.012, -0.004, d));
    }

    fragColor = TDOutputSwizzle(vec4(vec3(v), 1.0));
}
