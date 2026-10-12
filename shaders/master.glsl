// master.glsl
// Final stage: overall brightness (blackout lives here so trails keep running).

uniform float uMaster;

layout(location = 0) out vec4 fragColor;

void main()
{
    vec3 c = texture(sTD2DInputs[0], vUV.st).rgb;
    fragColor = TDOutputSwizzle(vec4(clamp(c, 0.0, 1.0) * uMaster, 1.0));
}
