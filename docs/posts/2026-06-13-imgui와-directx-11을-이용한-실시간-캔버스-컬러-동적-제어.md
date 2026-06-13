# ImGui와 DirectX 11을 이용한 실시간 캔버스 컬러 동적 제어

이 커밋은 학습자가 **DirectX 11(DX11)의 텍스처 업데이트 파이프라인**과 **ImGui 라이브러리**를 연동하여, 사용자의 UI 입력(슬라이더)에 따라 화면의 픽셀 데이터를 실시간으로 변경하는 인터랙티브 그래픽스 어플리케이션의 기초를 성공적으로 구현했음을 보여줍니다.

---

## 1. 학습자가 직접 구현하며 이해한 핵심 그래픽스 개념

### (1) 실시간 대화형 루프 (Interactive Frame Loop)의 확보
기존 코드에 존재하던 `Sleep(300)` 코드가 주석 처리되었습니다. 이는 프레임 레이트(Frame Rate) 제한을 해제하여 사용자의 입력(ImGui 슬라이더 조작)이 화면에 지연 없이 즉각적으로 반영되는 **실시간 렌더링 환경(Real-time Rendering Environment)**을 구축하기 위한 필수적인 단계입니다.

### (2) CPU-GPU 메모리 바인딩 및 데이터 흐름 (Data Flow)
학습자는 메인 루프(`main.cpp`)의 ImGui UI가 제어하는 데이터 영역과 실제 렌더링 엔진(`Example.h`)의 캔버스 데이터 영역을 `example->backgroundColor`라는 구조체 멤버 변수를 통해 동기화했습니다. 

1. **ImGui UI 단계**: 사용자가 마우스로 슬라이더를 조작하면 `example->backgroundColor` 배열의 값이 변경됩니다.
2. **CPU 캔버스 업데이트 단계**: `Update()` 함수 내에서 CPU 메모리에 픽셀 배열(`std::vector<Vec4> pixels`)을 생성하고 이 값을 배경색으로 채웁니다.
3. **GPU 업로드 단계**: 이후 CPU의 픽셀 데이터를 `D3D11_MAPPED_SUBRESOURCE`를 통해 GPU의 텍스처 버퍼로 복사(Map/Unmap)하여 화면에 렌더링합니다.

### (3) 1차원 픽셀 배열과 화면 좌표계의 매핑
화면의 크기가 가로 $W$, 세로 $H$일 때, 전체 픽셀의 개수 $N$은 다음과 같습니다.

$$ N = W \times H $$

각 픽셀은 4차원 벡터(RGBA)로 표현되며, 메모리상에는 1차원 배열로 평탄화(Flattening)되어 저장됩니다. 임의의 2차원 좌표 $(x, y)$에 해당하는 1차원 배열 인덱스 $i$는 다음과 같은 공식으로 매핑됩니다.

$$ i = x + y \times W $$

학습자는 기존에 픽셀 하나하나를 순차적으로 테스트하던 루프 코드를 걷어내고, 전체 $N$개의 픽셀 벡터를 ImGui 슬라이더에서 전달된 배경색 벡터 $\mathbf{C}_{\text{bg}}$로 한 번에 초기화하도록 구현했습니다.

$$ \mathbf{P}[i] = \mathbf{C}_{\text{bg}} = \begin{bmatrix} R_{\text{bg}} \\ G_{\text{bg}} \\ B_{\text{bg}} \\ 1.0 \end{bmatrix} \quad (\text{for } 0 \le i < N) $$

---

## 2. 핵심 알고리즘 및 렌더링 루프 (추상화)

학습자가 구현한 인터랙티브 그래픽스 파이프라인의 프레임별 동작 흐름은 다음과 같은 추상적인 형태로 요약할 수 있습니다.

```python
# Frame Loop
while window_is_running():
    # 1. Input & UI Processing (ImGui)
    imgui.start_new_frame()
    imgui.begin_window("Background Color")
    
    # UI 슬라이더를 통해 CPU 상의 전역 상태 변수(RGB)를 직접 제어
    imgui.slider_float3("RGB", example.backgroundColor)
    imgui.end_window()
    imgui.render_draw_data()

    # 2. CPU-side Image Buffer Reconstruction
    canvas_width, canvas_height = example.get_dimensions()
    pixel_buffer = allocate_memory(canvas_width * canvas_height * sizeof(Vec4))
    
    # 모든 픽셀을 사용자가 UI로 지정한 배경색으로 채움
    fill_buffer(pixel_buffer, color=example.backgroundColor)

    # 3. CPU to GPU Memory Copy (DX11 Map/Unmap)
    gpu_texture_resource = example.get_texture_resource()
    gpu_memory_pointer = gpu_texture_resource.map_discard()
    copy_memory(dest=gpu_memory_pointer, src=pixel_buffer)
    gpu_texture_resource.unmap()

    # 4. Rasterization & Presentation
    example.render_quad_with_texture() # GPU 텍스처를 화면에 그리기
    dx11_present_frame() # 백버퍼와 프론트버퍼 스왑
```

---

## 3. WebGPU 인터랙티브 데모로 구현 시 시각화 구상

이 구조를 웹 표준 차세대 그래픽스 API인 **WebGPU**와 **Compute Shader**를 활용하여 브라우저에서 실행 가능한 데모로 변환한다면 훨씬 더 효율적인 렌더링 파이프라인을 구축할 수 있습니다.

```
[ HTML5 / lil-gui (UI) ]
         │ (Color Uniform: vec4f)
         ▼
[ WebGPU GPUBuffer (Uniform) ] ──(Every Frame binding)──┐
                                                        ▼
                                             [ WebGPU Compute Shader ]
                                                        │ (Write to)
                                                        ▼
                                             [ Texture (Storage) ]
                                                        │
                                                        ▼
                                             [ HTML5 Canvas (Screen) ]
```

### (1) WebGPU 환경에서의 아키텍처 개선점
기존 DX11 예제는 CPU에서 $W \times H$ 크기의 거대한 픽셀 버퍼 배열을 매 프레임 생성하고 이를 GPU로 전송(Upload)하는 병목(Bottleneck) 구조를 가지고 있습니다.
WebGPU 데모에서는 이를 개선하여 **Uniform Buffer**를 통해 3개의 float(RGB) 값만 GPU로 전송하고, 실제 배경색을 채우는 연산은 GPU의 **Compute Shader**에서 병렬로 처리하도록 설계합니다.

### (2) WebGPU Compute Shader (WGSL) 의사코드
모든 픽셀을 병렬로 채우는 WebGPU 커널 코드는 다음과 같이 작성될 수 있습니다.

```wgsl
// WGSL (WebGPU Shading Language)

// 1. UI에서 전달받을 배경색 유니폼 버퍼 정의
struct CanvasUniform {
    bgColor : vec4<f32>,
};
@group(0) @binding(0) var<uniform> config : CanvasUniform;

// 2. 출력이 이루어질 화면 텍스처 정의
@group(0) @binding(1) var o_texture : texture_storage_2d<rgba8unorm, write>;

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) global_id : vec3<u32>) {
    let tex_size = textureDimensions(o_texture);
    
    // 스레드가 이미지 영역 내부를 가리키는지 확인
    if (global_id.x >= tex_size.x || global_id.y >= tex_size.y) {
        return;
    }
    
    let coords = vec2<i32>(global_id.xy);
    
    // CPU 전송 없이 GPU 내부에서 직접 텍스처에 배경색 쓰기 (대단히 빠름)
    textureStore(o_texture, coords, config.bgColor);
}
```

### (3) 데모 동작 요약
* **인터페이스**: 브라우저 화면 우측 상단에 `dat.gui` 혹은 `lil-gui` 슬라이더가 배치되어 RGB 채널 값을 제어합니다.
* **시각화 결과**: 사용자가 슬라이더를 드래그하는 순간, WebGPU Compute Shader가 2D 텍스처의 수백만 픽셀을 워크그룹 단위($16 \times 16$ 스레드 블록)로 동시에 병렬 처리하여 밀리초($\text{ms}$) 미만의 속도로 캔버스 배경색을 완벽히 동기화해 냅니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/imgui와-directx-11을-이용한-실시간-캔버스-컬러-동적-제어/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
