# DirectX 11 그래픽스 파이프라인의 첫 걸음: Window 및 디바이스 초기화

첫 번째 커밋을 축하합니다! graphics API 학습에서 가장 거대하고 험난한 장벽 중 하나는 화면에 '아무것도 없는 빈 창'을 띄우고, 이를 원하는 단색(Clear Color)으로 채우는 초기 설정 단계입니다. 

이번 첫 커밋을 통해 학습자님은 Windows API(Win32)와 DirectX 11 간의 연결 고리를 성공적으로 구축하고, GPU 하드웨어를 제어하기 위한 최소한의 그래픽스 파이프라인 인프라를 이해하고 구현하셨습니다. 본 리뷰에서는 이번 작업에서 학습자님이 직접 구현하며 습득한 핵심 그래픽스 개념과 구조를 정리해 드립니다.

---

## 1. 학습자가 직접 구현하며 이해한 핵심 개념

### 1) Win32 API와 그래픽스 루프 (Game Loop)의 동기화
전통적인 Windows 애플리케이션은 이벤트가 발생할 때만 반응하는 '이벤트 구동식(Event-driven)' 구조를 가집니다. 하지만 실시간 그래픽스 애플리케이션은 매 프레임 끊임없이 화면을 갱신해야 하므로, 학습자님은 메시지 큐에 대기 중인 메시지가 없을 때 GPU 렌더링 함수를 지속적으로 호출하는 **실시간 게임 루프(Real-time Loop)** 구조를 직접 구축하셨습니다.

### 2) ID3D11Device와 ID3D11DeviceContext의 역할 분담
DirectX 11은 리소스 생성과 렌더링 명령 실행을 엄격히 분리합니다.
* **Device (ID3D11Device):** 버퍼, 텍스처, 셰이더 등 GPU 메모리에 올라갈 리소스를 할당하고 생성하는 '공장' 역할을 수행합니다.
* **Device Context (ID3D11DeviceContext):** 생성된 리소스를 파이프라인에 바인딩하고, 그리기 명령(Draw Call)을 내리는 '실행자' 역할을 수행합니다.
이 구분을 통해 리소스 관리와 파이프라인 제어의 흐름을 파악하셨을 것입니다.

### 3) 스왑 체인(Swap Chain)과 더블 버퍼링(Double Buffering)
화면이 그려지는 과정이 사용자에게 그대로 노출되면 깜빡임(Flickering)이나 찢어짐(Tearing) 현상이 발생합니다. 학습자님은 전면 버퍼(Front Buffer)와 후면 버퍼(Back Buffer)를 두고, GPU가 후면 버퍼에 그리는 동안 전면 버퍼는 디스플레이에 출력하며, 그리기가 완료되면 두 버퍼를 교체(Present)하는 **스왑 체인** 메커니즘을 적용하셨습니다.

### 4) 렌더 타겟 뷰(Render Target View, RTV)와 뷰포트(Viewport)
GPU 내부의 2D 텍스처(후면 버퍼)에 직접 그림을 그리기 위해서는 이를 파이프라인의 출력 병합기(Output Merger) 단계에 연결해 주는 통로가 필요합니다. 학습자님은 후면 버퍼를 가리키는 **RTV**를 생성하고, 그려질 화면의 픽셀 좌표 범위를 정의하는 **Viewport**를 설정하여 3D NDC 공간이 실제 모니터 해상도 픽셀 공간으로 매핑되는 기반을 마련하셨습니다.

---

## 2. 핵심 수학적 개념: 스크린 좌표계에서 NDC로의 변환

우리가 모니터 화면에서 보는 픽셀 좌표계(Screen Space)는 좌측 상단이 $(0, 0)$이고 우측 하단이 $(Width, Height)$인 양수 기반의 좌표계입니다. 반면, DirectX 11의 내부 투영 공간(Normalized Device Coordinates, NDC)은 화면 중심이 $(0, 0)$이고, 좌측 하단이 $(-1, -1)$, 우측 상단이 $(1, 1)$인 왼손 좌표계를 사용합니다.

이 두 좌표계 사이의 변환 식은 뷰포트 매핑의 근간이 되며, 하드웨어 내부적으로 다음과 같이 계산됩니다.

$$ x_{ndc} = \frac{2 \cdot x_{pixel}}{Width} - 1 $$

$$ y_{ndc} = 1 - \frac{2 \cdot y_{pixel}}{Height} $$

이 변환 식을 통해 GPU는 우리가 입력한 정점(Vertex)들이 화면의 정확한 픽셀 위치에 래스터화(Rasterization)되도록 정렬합니다. 학습자님이 설정한 `D3D11_VIEWPORT` 구조체는 이 수학적 변환을 하드웨어단에서 자동으로 수행하도록 돕는 가이드라인 역할을 합니다.

---

## 3. 핵심 알고리즘 흐름 (추상화된 의사코드)

전체적인 어플리케이션의 초기화 및 루프 흐름은 다음과 같은 구조로 추상화할 수 있습니다.

```python
# [Initialization Phase]
def InitializeApplication():
    # 1. Win32 윈도우 창 생성
    window_handle = CreateWin32Window(width, height, title="DX11 Study")
    
    # 2. DX11 핵심 객체 생성 (Device, Context, SwapChain)
    device, context, swap_chain = D3D11CreateDeviceAndSwapChain(
        adapter=None, 
        driver_type=HARDWARE, 
        swap_chain_desc=ConfigSwapChain(window_handle, width, height)
    )
    
    # 3. 스왑 체인의 Back Buffer 텍스처 획득
    back_buffer_texture = swap_chain.GetBuffer(0)
    
    # 4. Back Buffer를 타겟으로 하는 Render Target View 생성
    render_target_view = device.CreateRenderTargetView(back_buffer_texture)
    
    # 5. 파이프라인에 렌더 타겟 바인딩 및 뷰포트 설정
    context.OMSetRenderTargets(render_target_view)
    context.RSSetViewports(Viewport(0, 0, width, height))
    
    return window_handle, context, swap_chain, render_target_view

# [Main Loop Phase]
def RunEngine(window_handle, context, swap_chain, render_target_view):
    while engine_is_running:
        if HasWindowsMessage():
            ProcessWindowsMessage() # 창 크기 조절, 종료 이벤트 등 처리
        else:
            # 1. 렌더 타겟을 특정 색상(예: Cornflower Blue)으로 초기화
            clear_color = [0.1, 0.2, 0.4, 1.0]
            context.ClearRenderTargetView(render_target_view, clear_color)
            
            # 2. [추후 구현] 그리기를 원하는 기하 구조물 렌더링 호출 (Draw Call)
            # context.DrawIndexed(...)
            
            # 3. 프레임 버퍼 스왑 (Present)을 통해 모니터에 출력
            swap_chain.Present(sync_interval=1) # V-Sync 활성화
```

---

## 4. WebGPU 인터랙티브 데모

학습자님이 DirectX 11에서 C++로 작성하신 이 기초 초기화 및 화면 클리어(Clear) 로직을 웹 생태계의 차세대 그래픽스 API인 **WebGPU**로 전환하여 브라우저 환경에서 시각화하면 다음과 같은 구조로 인터랙티브 데모를 구성할 수 있습니다.

### 시각화 방식 및 인터랙션 시나리오
1. **Clear Color 실시간 조절 패널:** 브라우저 UI 상에 존재하는 RGB 슬라이더를 통해 배경 색상 값을 조절합니다.
2. **WebGPU 렌더 패스:** 사용자가 UI 슬라이더를 움직일 때마다, WebGPU의 `GPURenderPassEncoder` 내 `clearValue` 속성이 실시간으로 변경되어 Canvas의 Back Buffer 색상이 부드럽게 전환됩니다.
3. **Compute Shader 연동 (확장):** 백그라운드에서 단순 단색 채우기가 아닌, Compute Shader를 구동하여 프레임 버퍼의 각 픽셀에 수학적 패턴(예: 만델브로트 집합 또는 프랙탈 패턴)을 실시간으로 계산하여 쓰는 연산 과정을 화면에 실시간으로 매핑해 보여줍니다.

### WebGPU에서의 파이프라인 대응성
DirectX 11에서 복잡하게 설정했던 `IDXGISwapChain`과 `ID3D11RenderTargetView`는 WebGPU에서 브라우저의 HTML5 Canvas 컨텍스트(`GPUCanvasContext`)에 의해 고도로 추상화됩니다. 학습자님이 DX11에서 겪으셨던 하드웨어와 윈도우 핸들 간의 복잡한 초기화 과정을 WebGPU에서는 단 몇 줄의 자바스크립트/타입스크립트 코드로 경험할 수 있어, DX11의 원리를 이해한 상태에서 WebGPU를 보면 그래픽스 API의 현대적 발전 방향성을 아주 직관적으로 체감할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/directx-11-그래픽스-파이프라인의-첫-걸음-window-및-디바이/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
