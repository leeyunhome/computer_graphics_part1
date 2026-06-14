# [DirectX 11] C++ 그래픽스 환경에서의 GLM 실험적 확장 활성화 및 디버깅 기초

이번 커밋은 DirectX 11 / C++ 그래픽스 학습 과정에서 수학 라이브러리인 **GLM(OpenGL Mathematics)**의 디버깅 유틸리티를 안전하게 통합하기 위한 프로젝트 설정 변경을 담고 있습니다. 

단순히 빌드 에러를 해결한 것을 넘어, 그래픽스 프로그래밍에서 필수적인 **수학적 데이터 시각화(디버깅)의 기틀**을 마련했다는 점에서 의미가 큽니다.

---

## 1. 커밋의 핵심 개념: 그래픽스 디버깅과 GLM 매크로 설정

### 3D 변환 Matrix와 디버깅의 한계
그래픽스 파이프라인을 구축할 때, 우리는 수많은 벡터와 행렬 연산을 수행합니다. 로컬 좌표계의 정점을 스크린 공간으로 변환하는 대표적인 공식은 다음과 같습니다.

$$ \mathbf{v}_{clip} = P \times V \times M \times \mathbf{v}_{local} $$

여기서 $M$(Model), $V$(View), $P$(Projection)는 모두 $4 \times 4$ 행렬입니다. 셰이더나 C++ 애플리케이션 단계에서 변환이 잘못되었을 때, 이를 콘솔에 출력하여 값을 확인하는 것은 디버깅의 출발점입니다. 

하지만 C++ 표준 라이브러리(`std::cout`)는 `glm::vec3`나 `glm::mat4` 같은 고차원 수학 타입을 기본적으로 출력할 수 없습니다.

### `glm/gtx/string_cast.hpp`와 실험적 확장 기능
GLM 라이브러리는 이를 해결하기 위해 행렬과 벡터를 문자열로 쉽게 변환해 주는 `glm::to_string()` 함수를 제공합니다. 이 함수는 `glm/gtx/string_cast.hpp` 헤더에 정의되어 있습니다.

* **GTX(Extension)의 의미**: GLM에서 `gtx` 경로에 있는 헤더들은 '실험적(Experimental)' 기능을 의미합니다. 향후 API가 변경될 가능성이 있으므로, 개발자가 이 위험을 인지하고 사용하겠다는 명시적인 동의를 요구합니다.
* **해결책**: 프리프로세서(전처리기) 단계에서 `GLM_ENABLE_EXPERIMENTAL` 매크로를 정의해야만 해당 헤더의 기능을 컴파일러가 허용합니다. 학습자는 이를 프로젝트 전반(`.vcxproj` 설정)에 반영하여 해결했습니다.

---

## 2. 학습자가 직접 구현하며 이해한 핵심 구조

학습자는 단순 소스 코드 레벨(`#define`)에서 매크로를 선언하는 대신, Visual Studio 프로젝트 구성 요소(`.vcxproj`)에 직접 정의를 추가했습니다. 이는 규모가 큰 그래픽스 엔진 아키텍처에서 매우 권장되는 방식입니다.

### 전처리 정의 통합의 아키텍처적 의미
모든 빌드 환경(Debug, Release, Win32, x64)에 매크로를 주입함으로써 다음과 같은 이점을 얻습니다.
1. **일관성**: 특정 소스 파일에서 `#define`을 누락하여 발생하는 산발적인 빌드 에러를 방지합니다.
2. **사전 컴파일된 헤더(PCH)와의 호환성**: 그래픽스 프로젝트에서 흔히 쓰이는 `pch.h` 등과 엉키지 않고 안전하게 GLM 설정을 전역에 전파합니다.

### 추상화된 디버깅 워크플로우

학습자가 구축한 디버깅 환경의 논리적 흐름은 다음과 같이 요약할 수 있습니다.

```cpp
// 1. 그래픽스 렌더링 루프 중 카메라 또는 오브젝트의 행렬 계산
Matrix4x4 modelMatrix = CalculateModelTransform(translation, rotation, scale);
Matrix4x4 viewMatrix  = CalculateViewMatrix(cameraPosition, lookAt);
Matrix4x4 projectionMatrix = CalculateProjectionMatrix(fov, aspectRatio, nearZ, farZ);

// 2. MVP 결합 행렬 도출
Matrix4x4 mvpMatrix = projectionMatrix * viewMatrix * modelMatrix;

// 3. 빌드 에러 없이 작동하는 GLM 문자열 변환 디버깅 (학습자가 해결한 핵심 영역)
#ifdef _DEBUG
    // 콘솔 창에 4x4 행렬의 원소들을 포맷팅하여 실시간 출력
    String formattedMatrix = Math::ToString(mvpMatrix);
    Debug::Log("Current MVP Matrix:\n" + formattedMatrix);
#endif
```

---

## 3. WebGPU 인터랙티브 데모로의 확장 관점

웹 환경의 차세대 그래픽스 API인 **WebGPU**에서도 이와 유사한 수학적 디버깅 및 연산 문제가 발생합니다. WebGPU의 셰이더 언어인 **WGSL(WebGPU Shading Language)** 역시 복잡한 행렬 연산을 수행하지만, 셰이더 내부의 값을 CPU(JavaScript) 측에서 직접 확인하는 것은 매우 까다롭습니다.

이 커밋에서 다룬 **"수학적 연산 결과를 CPU로 가져와 확인하는 시각화 기법"**을 WebGPU Compute Shader 데모로 재구성한다면 다음과 같은 방식으로 시각화할 수 있습니다.

### WebGPU Compute Shader 기반 행렬 변환 시각화 시나리오

1. **상황 설정**: 수만 개의 정점(Vertices)에 임의의 3D 회전 행렬 $R(\theta)$를 적용하는 Compute Shader를 가동합니다.
2. **디버깅 버퍼(Storage Buffer) 생성**:
   * CPU와 GPU가 공유하는 `readback` 버퍼를 만듭니다.
   * GPU 연산 결과로 도출된 변환 행렬 및 정점 위치 정보를 이 버퍼에 기록합니다.
3. **JS를 통한 시각화(WebGPU의 `string_cast` 구현)**:
   * GPU 연산이 끝나면 `GPUBuffer.mapAsync()`를 호출하여 데이터를 메모리에 매핑합니다.
   * JavaScript 콘솔 또는 HTML 브라우저 화면에 3D 변환 행렬 상태와 정점들의 변화를 실시간 텍스트 및 3D 기하구조로 렌더링합니다.

```rust
// WGSL (Compute Shader 예시)
struct DebugData {
    transformMatrix : mat4x4<f32>,
    calculatedPos   : vec4<f32>,
}
@group(0) @binding(0) var<storage, read_write> debugBuffer : DebugData;

@compute @workgroup_size(1)
fn main() {
    // GPU 내부에서 복잡한 행렬 연산 수행
    let M = mat4x4<f32>(...);
    debugBuffer.transformMatrix = M; 
    debugBuffer.calculatedPos = M * vec4<f32>(1.0, 2.0, 3.0, 1.0);
}
```

* **데모 화면 구성**: 사용자가 웹페이지의 슬라이더를 조절하면, WebGPU가 실시간으로 행렬 변환을 계산합니다. 화면 한편에는 학습자가 DirectX 11 환경에서 `glm::to_string()`으로 확인하고자 했던 포맷 그대로, **변환 행렬 데이터가 실시간 텍스트로 갱신**되며 3D 오브젝트가 회전하는 모습을 직관적으로 관찰할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/directx-11-c-그래픽스-환경에서의-glm-실험적-확장-활성화-및/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
