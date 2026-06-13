# 학습자 커밋 분석: add source code

학습자님의 "add source code" 커밋은 그래픽스 스터디의 중요한 첫걸음을 의미하는 경우가 많습니다. 비록 구체적인 코드 변경사항은 없지만, DirectX 11/C++ 환경에서 이 커밋 메시지는 주로 **렌더링 파이프라인의 핵심 구성 요소를 초기화하고 기본 기하 도형을 화면에 그리기 위한 코드**가 추가되었음을 시사합니다.

이는 화면에 아무것도 보이지 않는 상태에서, 가상의 3D 공간을 설정하고 가장 기본적인 형태인 삼각형을 그리기 위해 필요한 모든 준비 작업을 수행하는 과정입니다. 학습자님이 직접 구현하며 이해했을 개념들을 중심으로 살펴보겠습니다.

## 학습자가 이해한 핵심 개념

이 커밋은 DirectX 11 애플리케이션의 뼈대를 만드는 과정으로, 다음과 같은 핵심 개념들을 직접 구현하며 이해했을 것입니다.

### 1. DirectX 디바이스 및 스왑 체인 초기화 (Device & Swap Chain Initialization)

화면에 그림을 그리기 위한 하드웨어 인터페이스(Device)와, 그려진 이미지를 최종적으로 화면에 표시하는 과정(Swap Chain)을 설정합니다. 이는 DirectX 11 애플리케이션의 가장 기본적인 요구사항입니다.

*   `D3D11CreateDeviceAndSwapChain` 함수를 호출하여 그래픽 카드와 통신할 장치 객체(`ID3D11Device`)와 렌더링 결과를 저장하고 화면에 표시할 스왑 체인(`IDXGISwapChain`)을 생성합니다.
*   `D3D_FEATURE_LEVEL`을 설정하여 어떤 DirectX 버전을 사용할지 명시합니다 (예: `D3D_FEATURE_LEVEL_11_0`).
*   `DXGI_SWAP_CHAIN_DESC` 구조체를 채워 스왑 체인의 버퍼 수, 해상도, 포맷, 사용 방식 등을 정의합니다.

### 2. 렌더 타겟 뷰 및 깊이/스텐실 뷰 설정 (Render Target View & Depth/Stencil View)

DirectX가 최종적으로 그림을 그릴 대상(렌더 타겟)과 3D 오브젝트의 깊이 정보를 관리하여 올바른 순서로 렌더링되도록 하는(깊이/스텐실) 리소스를 설정합니다.

*   스왑 체인의 백 버퍼(Back Buffer)에 접근하여 `ID3D11Texture2D` 리소스를 얻습니다.
*   이 텍스처를 대상으로 `ID3D11RenderTargetView`를 생성하여 픽셀 쉐이더가 최종 색상을 출력할 곳을 지정합니다.
*   별도의 깊이/스텐실 텍스처를 생성하고, 이를 기반으로 `ID3D11DepthStencilView`를 생성하여 깊이 테스트 및 스텐실 테스트를 활성화합니다.

### 3. 뷰포트 설정 (Viewport Setup)

렌더 타겟 내에서 실제로 그림이 그려질 영역을 정의합니다. 이는 화면의 특정 부분에만 렌더링하고 싶을 때 유용합니다.

*   `D3D11_VIEWPORT` 구조체를 채워 뷰포트의 좌상단 좌표(TopLeftX, TopLeftY), 너비(Width), 높이(Height), 최소 깊이(MinDepth), 최대 깊이(MaxDepth)를 설정합니다.
*   이 뷰포트를 `RSSetViewports` 함수를 통해 래스터라이저 스테이지에 바인딩합니다.

### 4. 입력 어셈블러 스테이지 (Input Assembler Stage)

3D 모델의 정점 데이터(위치, 색상, 노멀 등)를 GPU가 이해할 수 있는 형태로 조직화하는 단계입니다.

*   **정점 버퍼 (Vertex Buffer)**: 3D 모델의 각 정점 데이터를 저장하는 GPU 메모리입니다.
*   **인덱스 버퍼 (Index Buffer)**: 정점 버퍼의 정점들을 어떤 순서로 연결하여 삼각형을 만들지 지정하는 인덱스 데이터를 저장합니다. 이를 통해 중복되는 정점 데이터를 줄일 수 있습니다.
*   **입력 레이아웃 (Input Layout)**: 정점 버퍼에 저장된 데이터가 어떻게 구성되어 있는지 GPU에게 설명하는 역할을 합니다 (예: 첫 12바이트는 위치, 다음 12바이트는 색상).

### 5. 쉐이더 생성 및 바인딩 (Shader Creation & Binding)

GPU에서 실행될 프로그램을 로드하고 파이프라인에 연결합니다.

*   **정점 쉐이더 (Vertex Shader)**: 각 정점에 대해 한 번씩 실행되며, 주로 3D 공간 변환(World, View, Projection 변환)을 수행합니다.
*   **픽셀 쉐이더 (Pixel Shader)**: 래스터화된 각 픽셀에 대해 한 번씩 실행되며, 최종 색상을 결정합니다.

```cpp
// 의사코드: 렌더링 파이프라인 설정 및 렌더링 루프의 핵심
FUNCTION InitializeDirectXGraphics():
    // 1. 디바이스 및 스왑 체인 생성
    device, swapChain = CreateD3D11DeviceAndSwapChain()

    // 2. 렌더 타겟 뷰 생성 (백 버퍼를 렌더링 대상으로)
    backBufferTexture = GetSwapChainBackBuffer(swapChain)
    renderTargetView = CreateRenderTargetView(device, backBufferTexture)

    // 3. 깊이/스텐실 버퍼 및 뷰 생성
    depthStencilTexture = CreateDepthStencilTexture(device, WIDTH, HEIGHT)
    depthStencilView = CreateDepthStencilView(device, depthStencilTexture)

    // 4. 뷰포트 설정 (렌더링 영역 지정)
    viewport = { TopLeftX: 0, TopLeftY: 0, Width: WIDTH, Height: HEIGHT, MinDepth: 0.0, MaxDepth: 1.0 }
    SetViewports(deviceContext, viewport)

    // 5. 정점 버퍼, 인덱스 버퍼, 입력 레이아웃 생성 및 바인딩
    vertexBuffer = CreateBuffer(device, VERTEX_DATA)
    indexBuffer = CreateBuffer(device, INDEX_DATA)
    inputLayout = CreateInputLayout(device, VERTEX_SHADER_BYTECODE, INPUT_ELEMENT_DESC)
    SetInputAssemblerStage(deviceContext, PRIMITIVE_TOPOLOGY_TRIANGLELIST, vertexBuffer, indexBuffer, inputLayout)

    // 6. 정점 쉐이더 및 픽셀 쉐이더 로드 및 바인딩
    vertexShader = LoadVertexShader(device, "vertexShader.hlslc")
    pixelShader = LoadPixelShader(device, "pixelShader.hlslc")
    SetVertexShader(deviceContext, vertexShader)
    SetPixelShader(deviceContext, pixelShader)

    // (선택) 상수 버퍼 생성 및 바인딩 (MVP 행렬 등)
    constantBuffer = CreateConstantBuffer(device, sizeof(MVP_Matrices))
    SetConstantBuffers(deviceContext, VS_STAGE, 0, constantBuffer)
END FUNCTION

FUNCTION RenderFrame():
    // 렌더 타겟 및 깊이 버퍼 초기화
    ClearRenderTargetView(deviceContext, renderTargetView, CLEAR_COLOR)
    ClearDepthStencilView(deviceContext, depthStencilView, D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL, 1.0f, 0)

    // 렌더 타겟 및 깊이 스텐실 뷰 설정 (출력 병합 스테이지)
    SetRenderTargets(deviceContext, renderTargetView, depthStencilView)

    // (선택) 상수 버퍼 업데이트 (MVP 행렬 변경 등)
    UpdateConstantBuffer(deviceContext, constantBuffer, CURRENT_MVP_MATRICES)

    // 그리기 호출 (예: 인덱스 버퍼를 사용한 그리기)
    DrawIndexed(deviceContext, NUM_INDICES, 0, 0)

    // 최종 결과 화면에 표시
    Present(swapChain)
END FUNCTION
```

### 6. 월드-뷰-프로젝션 (MVP) 변환 행렬 (World-View-Projection Matrix)

3D 공간의 오브젝트를 2D 화면에 올바르게 표현하기 위한 핵심적인 수학적 변환입니다. 학습자님은 이를 직접 계산하고 쉐이더에 전달하는 과정을 구현했을 것입니다.

*   **월드 행렬($M_{world}$)**: 오브젝트의 지역 공간(local space) 좌표를 월드 공간(world space) 좌표로 변환합니다. 오브젝트의 위치, 회전, 크기를 정의합니다.
*   **뷰 행렬($M_{view}$)**: 월드 공간 좌표를 카메라 관점의 뷰 공간(view space) 좌표로 변환합니다. 카메라의 위치와 방향을 정의합니다.
*   **투영 행렬($M_{proj}$)**: 뷰 공간 좌표를 2D 화면에 매핑하기 위한 투영 공간(projection space, 또는 클립 공간 clip space) 좌표로 변환합니다. 원근 투영(perspective) 또는 직교 투영(orthographic)이 있습니다.

이 세 가지 행렬은 다음과 같이 곱해져 최종 변환 행렬이 됩니다.

$$V_{clip} = M_{proj} \times M_{view} \times M_{world} \times V_{local}$$

여기서 $V_{local}$은 모델의 지역 공간 정점이고, $V_{clip}$은 최종 클립 공간 정점입니다. 이 클립 공간 좌표는 래스터라이저를 거쳐 화면 좌표로 변환됩니다.

## WebGPU 인터랙티브 데모

학습자님이 구현한 **월드-뷰-프로젝션 변환**의 개념은 WebGPU Compute Shader를 통해 매우 직관적이고 인터랙티브하게 시각화할 수 있습니다.

**데모 아이디어:**
화면에 정점들의 그리드를 띄우고, 이 그리드에 World, View, Projection 행렬을 실시간으로 적용하여 변환 과정을 시각적으로 보여주는 데모입니다.

1.  **초기 상태:** 3D 공간에 평평한 정점 그리드(예: 100x100)를 배치하고, 각 정점은 고유한 색상을 가집니다. (Local Space)
2.  **WebGPU Compute Shader:**
    *   입력 버퍼: 초기 정점 그리드 데이터 (`V_{local}`).
    *   유니폼 버퍼: World, View, Projection 행렬 데이터 (`M_{world}`, `M_{view}`, `M_{proj}`).
    *   출력 버퍼: 변환된 정점 데이터 (`V_{clip}`).
    *   Compute Shader는 각 정점에 대해 위에서 언급된 행렬 곱셈 연산($V_{clip} = M_{proj} \times M_{view} \times M_{world} \times V_{local}$)을 병렬로 수행합니다.
3.  **WebGPU Render Pipeline:** Compute Shader에서 계산된 `V_{clip}` 데이터를 받아 화면에 렌더링합니다.
4.  **인터랙션:**
    *   **슬라이더:** World, View, Projection 행렬의 구성 요소(예: 월드 X,Y,Z 이동/회전/크기 조절, 카메라 X,Y,Z 위치/회전, FOV, Aspect Ratio, Near/Far Plane)를 조절할 수 있는 UI 슬라이더를 제공합니다.
    *   **실시간 반영:** 슬라이더를 조작하면 해당 행렬값이 변경되고, Compute Shader가 다시 실행되어 정점들이 즉시 새로운 위치로 변환되어 화면에 업데이트됩니다.
    *   **시각화:** 그리드의 각 정점이 어떤 변환을 겪었는지 화살표나 보조 선분으로 시각화하거나, 변환 전/후의 정점 위치를 동시에 보여줄 수 있습니다.

이 데모를 통해 학습자는 MVP 변환이 3D 오브젝트를 2D 화면에 어떻게 투영하고 위치시키는지를 "직접 조작하며" 깊이 있게 이해할 수 있을 것입니다. 특히 Compute Shader의 병렬 처리 능력을 활용하여 복잡한 행렬 연산이 어떻게 실시간으로 처리되는지도 체감할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/학습자-커밋-분석-add-source-code/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
