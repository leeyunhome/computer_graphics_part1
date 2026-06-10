# 픽셀 버퍼 애니메이션

C++/DirectX 11에서 CPU로 픽셀 버퍼를 채운 뒤 GPU 텍스처로 업로드하는 구조를 WebGPU로 재현.  
강의 예제와 동일하게 **16×12 픽셀** 캔버스에 ImGui 슬라이더로 배경색을 실시간 제어합니다.

<div style="border: 1px solid #4c1d95; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="demo.html" width="100%" height="720" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>

## 핵심 개념

- **픽셀 버퍼**: `canvasWidth=16, canvasHeight=12` (1280÷80, 960÷80) — 각 픽셀이 화면에서 큰 사각형으로 표시
- **배경색 제어**: ImGui `SliderFloat3("RGB(0.0->1.0)")` 로 R·G·B 각각 0~1 범위 조절
- **GPU 업로드**: `D3D11_MAPPED_SUBRESOURCE`로 CPU 픽셀 데이터를 매 프레임 텍스처에 복사

## C++/DX11 → WebGPU 대응

| DX11 | WebGPU (WGSL) |
|---|---|
| `RWTexture2D<float4>` (UAV) | `texture_storage_2d<rgba8unorm, write>` |
| `[numthreads(4,3,1)]` | `@workgroup_size(4, 3)` |
| `SV_DispatchThreadID` | `@builtin(global_invocation_id)` |
| `cbuffer { float4 bg; }` | `var<uniform> p : Params` |
| `output[id.xy] = float4(bg, 1)` | `textureStore(output_tex, id.xy, bg)` |
| `ID3D11DeviceContext::Dispatch` | `dispatchWorkgroups(4, 4)` |
