# 스크린 공간에서의 원 판정(Point-in-Circle) 알고리즘 구현 및 최적화

이번 커밋은 2D 스크린 공간(Screen Space)에서 CPU 라스터라이제이션(Rasterization)을 통해 원을 그리기 위한 핵심 판정 함수인 `IsInside`를 구현하고, 이를 위해 GLM(OpenGL Mathematics)의 확장 기능을 프로젝트에 통합한 작업입니다. 

학습자는 단순한 수학적 공식을 코드로 옮기는 것에 그치지 않고, 컴퓨터 그래픽스 연산에서 매우 중요한 **제곱근(Square Root) 연산 피하기** 최적화 기법을 직접 고민하고 적용하였습니다.

---

## 1. 커밋의 핵심 개념 및 수학적 배경

이 커밋의 핵심은 **"특정 스크린 좌표 $\mathbf{x}(x, y)$가 중심이 $\mathbf{c}(c_x, c_y)$ 이고 반지름이 $r$인 원의 내부에 정합하는가?"**를 판정하는 것입니다.

### 수학적 정형화 (Point-in-Circle Equation)
전형적인 2차원 유클리드 공간에서 두 점 사이의 거리를 구하는 공식은 다음과 같습니다.

$$ d = \sqrt{(x - c_x)^2 + (y - c_y)^2} $$

이 거리 $d$가 반지름 $r$보다 작거나 같으면 점 $\mathbf{x}$는 원의 내부에 존재합니다 ($d \le r$). 따라서 판정식은 다음과 같이 정의됩니다.

$$ \sqrt{(x - c_x)^2 + (y - c_y)^2} \le r $$

### 그래픽스 관점에서의 최적화: Squared Distance
컴퓨터 그래픽스에서 CPU나 GPU 모두에게 제곱근($\sqrt{\cdot}$) 연산은 매우 무거운(비싼) 연산 중 하나입니다. 수만에서 수백만 개의 픽셀을 매 프레임마다 검사해야 하는 라스터라이제이션 환경에서 픽셀당 한 번씩 제곱근을 호출하는 것은 심각한 병목을 유발합니다.

따라서 양변을 제곱하여 제곱근 연산을 제거한 식을 사용합니다.

$$ (x - c_x)^2 + (y - c_y)^2 \le r^2 $$

벡터 표현식으로는 다음과 같이 표현할 수 있습니다.

$$ \|\mathbf{x} - \mathbf{c}\|^2 \le r^2 $$

학습자는 주석을 통해 이 두 가지 방법(제곱근을 쓰는 방법과 내적을 통해 제곱된 거리를 비교하는 방법)을 모두 고민했음을 보여주고 있으며, 최종적으로 GLM 라이브러리의 최적화 함수인 `glm::distance2`를 사용하여 이를 간결하게 해결했습니다.

---

## 2. 코드 구조 분석 및 개선 제안

### GLM 확장 헤더 및 전처리기 설정
`glm/gtx/norm.hpp`에 정의된 `glm::distance2` 함수는 두 벡터 사이의 거리의 제곱(L2 Norm의 제곱)을 반환합니다. `gtx` 네임스페이스 아래에 있는 함수들은 GLM의 실험적(Experimental) 확장 기능이므로, 이를 C++에서 컴파일하기 위해 프로젝트의 전처리기 정의에 `GLM_ENABLE_EXPERIMENTAL`을 추가한 것은 올바른 조치입니다.

### 마이크로 최적화 (Micro-Optimization) 기회
학습자는 코드 작성 시 매우 훌륭한 시도를 해두었습니다. `Circle` 클래스의 생성자에서 미리 반지름의 제곱 값을 계산하여 멤버 변수 `radiusSquared`에 저장하도록 설계했습니다.

```cpp
Circle(const glm::vec2 &center, const float radius, const glm::vec4 &color)
    : center(center), color(color), radius(radius), radiusSquared(radius*radius)
{
}
```

하지만 정작 `IsInside` 함수의 반환문에서는 매번 곱셈 연산을 다시 수행하고 있습니다.

```cpp
return glm::distance2(x, center) <= radius * radius;
```

이를 이미 준비해 둔 `radiusSquared` 멤버 변수를 사용하도록 변경하면, 불필요한 부동소수점 곱셈 연산($radius \times radius$)을 매 픽셀 판정마다 생략할 수 있습니다.

**개선 제안 코드:**
```cpp
bool IsInside(const glm::vec2 &x)
{
    return glm::distance2(x, center) <= radiusSquared;
}
```

---

## 3. 라스터라이제이션 파이프라인에서의 흐름 (추상화)

이 `IsInside` 함수가 전체 스크린 space 상에서 원을 그리기 위해 어떻게 활용되는지 추상화된 의사코드(Pseudo-code)로 나타내면 다음과 같습니다.

```text
function RenderScene(FrameBuffer, ScreenWidth, ScreenHeight, Circle):
    for y from 0 to ScreenHeight - 1:
        for x from 0 to ScreenWidth - 1:
            pixelPosition = Vector2(x, y)
            
            // 현재 픽셀이 원 내부에 있는지 검사
            if Circle.IsInside(pixelPosition) is True:
                FrameBuffer.SetPixel(x, y, Circle.color)
            else:
                FrameBuffer.SetPixel(x, y, BackgroundColor)
```

이 방식은 전형적인 **CPU 기반의 브루트포스 라스터라이제이션(Rasterization by Grid Search)** 방식입니다. 

---

## 4. WebGPU 인터랙티브 데모 시각화

이 개념을 현대적인 웹 그래픽스 API인 **WebGPU**의 **Compute Shader** 또는 **Fragment Shader**로 이식하면, CPU에서 순차적으로 처리하던 루프를 수만 개의 GPU 코어를 통해 극도로 병렬화할 수 있습니다.

### WebGPU 셰이더(WGSL)에서의 구현 방식
WebGPU에서는 화면의 각 픽셀(Fragment)에 대해 이 수식이 동시에 실행됩니다. 브라우저 스크린의 모든 픽셀에서 병렬로 거리 판정이 수행되어 60fps 이상의 부드러운 속도로 원이 렌더링됩니다.

```wgsl
// WGSL Fragment Shader 예시
struct CanvasUniform {
    screenSize: vec2<f32>,
    circleCenter: vec2<f32>,
    circleRadius: f32,
    circleColor: vec4<f32>,
};

@group(0) @binding(0) var<uniform> canvas : CanvasUniform;

@fragment
fn main(@builtin(position) FragCoord : vec4<f32>) -> @location(0) vec4<f32> {
    let pixelCoord = FragCoord.xy; // 스크린 공간 좌표 (x, y)
    
    // 점과 원 중심 사이의 벡터
    let toCenter = pixelCoord - canvas.circleCenter;
    
    // 벡터의 내적(dot product)을 이용해 제곱 거리를 구함
    let distanceSquared = dot(toCenter, toCenter);
    let radiusSquared = canvas.circleRadius * canvas.circleRadius;
    
    // 원 안쪽이면 원의 색상을, 바깥쪽이면 검은색을 반환
    if (distanceSquared <= radiusSquared) {
        return canvas.circleColor;
    } else {
        return vec4<f32>(0.0, 0.0, 0.0, 1.0); // 배경색
    }
}
```

### 데모 시각화 효과
WebGPU 데모를 브라우저에서 실행하면 다음과 같은 실시간 인터랙션을 구현할 수 있습니다.
1. **마우스 상호작용**: 사용자가 캔버스 위에서 마우스를 움직이면 `circleCenter` 유니폼 변수가 마우스 포인터 좌표로 실시간 업데이트되어 마우스를 부드럽게 따라다니는 원이 그려집니다.
2. **해상도 독립성**: 화면 크기가 달라져도 스크린 공간 좌표 `FragCoord`를 기준으로 연산하기 때문에 왜곡 없는 정밀한 원을 렌더링합니다.
3. **안티앨리어싱(Anti-aliasing) 확장**: 데모에서 판정 경계면($distanceSquared \approx radiusSquared$)에 `smoothstep` 함수를 적용하면 거친 계단 현상(Aliasing)이 해결된 부드러운 경계선의 원을 시각화할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/스크린-공간에서의-원-판정point-in-circle-알고리즘-구현-및-/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
