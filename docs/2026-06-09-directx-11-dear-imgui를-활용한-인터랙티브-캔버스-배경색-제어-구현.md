# [DirectX 11] Dear ImGui를 활용한 인터랙티브 캔버스 배경색 제어 구현

안녕하세요. 컴퓨터 그래픽스를 학습하며 구현한 내용과 고민의 과정을 기록하는 포트폴리오입니다. 

이번 프로젝트에서는 DirectX 11 환경에 **Dear ImGui**를 연동하여, 사용자가 UI 슬라이더를 통해 실시간으로 캔버스의 배경색을 제어할 수 있는 기능을 구현했습니다. 기존의 정적이거나 하드코딩된 애니메이션을 제거하고, 진정한 의미의 **인터랙티브 렌더링 루프(Interactive Rendering Loop)**를 구축하는 과정을 정리해 보았습니다.

---

## 1. Immediate Mode GUI (IMGUI) 패러다임의 이해

이번 구현의 핵심은 `Dear ImGui` 라이브러리의 도입입니다. 전통적인 GUI 시스템(Retained Mode)과 달리, IMGUI는 **매 프레임마다 UI의 상태를 새로 정의하고 그리는 방식**을 취합니다. 

이러한 방식은 그래픽스 렌더링 파이프라인의 '메인 루프(Main Loop)' 구조와 완벽하게 맞아떨어집니다. 프로그램의 상태(State)와 UI가 즉각적으로 동기화되므로, 복잡한 콜백(Callback) 이벤트 없이도 직관적인 데이터 바인딩이 가능합니다.

### 렌더링 루프 내의 ImGui 생명주기 (개념도)

실제 코드 대신 렌더링 루프 안에서 ImGui가 어떻게 동작하는지 추상화한 흐름은 다음과 같습니다.

```cpp
while (MessageLoop()) 
{
    // 1. ImGui 및 플랫폼/그래픽스 API의 새 프레임 시작
    ImGui_StartNewFrame();
    
    // 2. UI 위젯 정의 (데이터 바인딩)
    ImGui::Begin("Background Color");
    ImGui::SliderFloat3("RGB", &appState.backgroundColor, 0.0f, 1.0f);
    ImGui::End();
    
    // 3. UI 렌더링 데이터 생성
    ImGui::Render();
    
    // 4. 애플리케이션 상태 업데이트 및 메인 그래픽스 렌더링
    App_Update(); 
    App_Render();
    
    // 5. 생성된 ImGui 데이터를 실제 그래픽스 API(DX11)를 통해 화면에 그리기
    RenderDrawData_DX11();
    
    // 6. 백버퍼와 프론트버퍼 교체 (Swap)
    Present();
}
```

---

## 2. 색상 데이터의 수학적 표현과 메모리 업데이트

GUI를 통해 입력받은 색상 데이터는 화면의 픽셀(Pixel) 데이터로 변환되어야 합니다. 컴퓨터 그래픽스에서 색상은 일반적으로 **RGBA(Red, Green, Blue, Alpha)** 모델을 사용하며, 이번 구현에서는 각 채널을 $0.0$ 부터 $1.0$ 사이의 정규화된 부동소수점(Normalized Floating-point)으로 표현합니다.

수학적으로 캔버스의 특정 픽셀 색상 $C$ 는 다음과 같은 벡터로 표현됩니다.

$$ C_{rgba} = \begin{bmatrix} R \\ G \\ B \\ A \end{bmatrix}, \quad R, G, B, A \in [0.0, 1.0] $$

### 캔버스 버퍼 업데이트 알고리즘

사용자가 ImGui 슬라이더를 조작하면, 전역 상태(또는 클래스 멤버)로 관리되는 배경색 배열의 값이 즉각적으로 변경됩니다. `Update` 함수에서는 이 값을 읽어와 캔버스 해상도(Width $\times$ Height)만큼의 1차원 배열을 단일 색상으로 가득 채웁니다.

```cpp
// 개념적 코드: 캔버스 전체 픽셀을 새로운 배경색으로 업데이트
Color currentBgColor = GetColorFromImGui();

// 캔버스의 총 픽셀 수만큼 배열을 할당하고, 현재 색상으로 초기화
std::vector<Color> pixelBuffer(TotalPixels, currentBgColor);

// 이후 이 pixelBuffer 데이터를 GPU 텍스처 메모리로 전송 (Map / Unmap)
UpdateTextureBuffer(pixelBuffer);
```

이 과정에서 CPU의 시스템 메모리(RAM)에 존재하는 `std::vector` 데이터가 Direct3D의 리소스 매핑 기법을 통해 GPU의 비디오 메모리(VRAM)로 전송되어 화면에 그려지게 됩니다.

---

## 3. 실시간 인터랙션을 위한 코드 리팩토링

이번 커밋에서는 새로운 기능 추가뿐만 아니라 기존 코드의 문제점을 개선하는 리팩토링도 함께 진행되었습니다.

* **Blocking 함수(`Sleep`) 제거:** 
  초기 테스트용 코드에 포함되어 있던 `Sleep(300)` 함수는 메인 스레드를 멈추게 하여 UI의 응답성을 심각하게 저해합니다. 실시간 렌더링과 상호작용을 위해서는 메인 루프가 지연 없이 최대한 빠르게 회전해야 하므로 이를 제거했습니다.
* **하드코딩된 애니메이션 제거:** 
  모듈로 연산(`%`)을 통해 픽셀의 색상을 순차적으로 바꾸던 정해진 애니메이션 코드를 제거하고, 전적으로 사용자의 입력(ImGui)에 의해 캔버스 전체의 상태가 결정되도록 로직을 간결하게 변경했습니다.

---

## 4. 배운 점 및 향후 과제

이번 작업을 통해 **응용 프로그램의 상태(State) $\rightarrow$ GUI 상호작용 $\rightarrow$ CPU 버퍼 업데이트 $\rightarrow$ GPU 리소스 매핑 및 렌더링**으로 이어지는 전체 파이프라인의 데이터 흐름을 명확하게 이해할 수 있었습니다. 

특히 렌더링 파이프라인 위에 별도의 UI 레이어를 올리는 과정에서, 상태 값이 프레임마다 어떻게 동기화되는지 체감할 수 있었습니다. 

**다음 학습 목표:**
현재는 캔버스 전체를 단일 색상으로 채우고 있지만, 앞으로는 이 픽셀 버퍼 배열을 조작하여 선 그리기(Bresenham's line algorithm), 삼각형 래스터화(Rasterization), 그리고 점진적으로는 3D 공간의 물체를 2D 화면에 투영(Projection)하는 렌더러의 핵심 기초를 구현해 나갈 계획입니다.