# 스크린 공간에서의 원 판별 알고리즘 구현 (Point-in-Circle Test)

이번 커밋은 CPU 레벨에서 스크린 공간(Screen Space)의 각 픽셀을 순회하며, 특정 픽셀이 원의 내부에 포함되는지 여부를 판별하는 **Point-in-Circle Test**를 구현한 단계입니다. 

이는 향후 3차원 공간에서 레이트레이싱(Raytracing)의 핵심이 되는 **Ray-Sphere Intersection(광선-구체 교차 검사)** 알고리즘으로 나아가기 위한 직관적인 2차원적 첫 단계(Step 2)입니다.

---

## 1. 핵심 수학적 개념 및 알고리즘

이 구현의 핵심은 임의의 점 $\mathbf{x}(x, y)$가 중심이 $\mathbf{c}(c_x, c_y)$이고 반지름이 $r$인 원의 내부에 존재하는지 판별하는 것입니다.

### 원의 방정식과 부등식
점 $\mathbf{x}$가 원의 내부에 있을 조건은 수학적으로 다음과 같이 표현됩니다.

$$ \|\mathbf{x} - \mathbf{c}\| \le r $$

양변에 제곱을 취하면 루트 연산을 제거하여 연산 비용을 획기적으로 줄일 수 있습니다. 컴퓨터 그래픽스에서 제곱근($\sqrt{}$) 연산은 매우 무겁기 때문에, 항상 **거리의 제곱(Squared Distance)**을 비교하는 것이 정석입니다.

$$ \|\mathbf{x} - \mathbf{c}\|^2 \le r^2 $$

이를 벡터의 내적(Dot Product)으로 표현하면 다음과 같습니다.

$$ (\mathbf{x} - \mathbf{c}) \cdot (\mathbf{x} - \mathbf{c}) \le r^2 $$

학습자는 주석을 통해 이 흐름을 정확히 이해하고 있음을 보여줍니다. 
1. 직접 `sqrt`를 사용하는 방식
2. `glm::dot`을 이용해 내적으로 제곱 거리를 구하는 방식
3. 최종적으로 GLM의 실험적 확장 기능(Experimental)인 `glm::distance2`를 사용하는 방식

이 세 가지를 모두 고민하고 비교한 흔적이 코드에 잘 녹아있습니다.

---

## 2. 구조적 변경 및 코드 분석

### 멤버 변수 캐싱을 통한 최적화 의도
학습자는 생성자에서 `radiusSquared` 멤버 변수를 추가하여 $r^2$ 값을 미리 계산(Caching)하도록 코드를 개선했습니다.

```cpp
// 변경 전
: center(center), color(color), radius(radius)

// 변경 후
: center(center), color(color), radius(radius), radiusSquared(radius*radius)
```
이는 매 프레임, 매 픽셀마다 반복되는 곱셈 연산($r \times r$)을 단 한 번의 생성자 호출 시점으로 단축하려는 좋은 최적화 시도입니다.

### 아쉬운 점 및 피드백 (Optimization Point)
최종 반환문인 `IsInside` 메서드를 보면 다음과 같이 작성되어 있습니다.

```cpp
return glm::distance2(x, center) <= radius * radius;
```
여기서 우변에 `radius * radius`를 다시 계산하고 있습니다. 생성자에서 미리 구해둔 `radiusSquared` 멤버 변수가 존재하므로, 이를 다음과 같이 수정하면 매 픽셀마다 발생하는 곱셈 연산 하나를 더 줄일 수 있습니다.

```cpp
// 개선안
return glm::distance2(x, center) <= radiusSquared;
```
픽셀 수가 많아질수록(예: $1920 \times 1080$ 해상도에서는 약 200만 번) 이러한 미세한 최적화가 CPU 래스터라이저의 성능 향상에 기여합니다.

---

## 3. 추상화된 래스터라이제이션 파이프라인

이 2차원 원 그리기(Procedural Circle Generation)는 CPU 상에서 다음과 같은 구조적 흐름으로 픽셀을 채워나갑니다.

```text
Function RenderScene(Width, Height):
    Circle = InitializeCircle(Center=(Width/2, Height/2), Radius=Height/4)
    
    For each y from 0 to Height - 1:
        For each x from 0 to Width - 1:
            PixelPosition = Vector2(x, y)
            
            If Circle.IsInside(PixelPosition) is True:
                SetPixel(x, y, Circle.Color)
            Else:
                SetPixel(x, y, BackgroundColor)
```

이 방식은 기하학적 정보(원)를 직접 다각형(Polygon) 렌더링 파이프라인을 거치지 않고, 화면의 각 픽셀 위치에서 수식을 평가하여 직접 그려내는 **절차적 렌더링(Procedural Rendering)**의 기초입니다.

---

## 4. WebGPU 인터랙티브 데모 제안

이 알고리즘을 최신 웹 그래픽스 API인 **WebGPU**의 **Compute Shader** 또는 **Fragment Shader**로 이식한다면 극적인 성능 향상과 실시간 인터랙션을 구현할 수 있습니다.

### 시각화 및 구성 방식
* **병렬 처리 (Parallelism):** CPU가 순차적으로 `for` 루프를 돌며 픽셀을 검사했던 것과 달리, GPU의 수천 개 스레드가 화면의 각 픽셀 위치에서 `IsInside` 연산을 동시에(In Parallel) 실행합니다.
* **인터랙티브 요소:** 
  * 마우스 커서의 위치 정보를 Uniform Buffer를 통해 GPU로 매 프레임 전달합니다.
  * 원의 중심 $\mathbf{c}$를 마우스 포인터 좌표로 실시간 업데이트합니다.
  * 사용자가 마우스를 움직일 때마다 마우스 주변으로 부드럽게 그려지는 원을 실시간(60fps 이상)으로 관찰할 수 있습니다.

### WGSL (WebGPU Shading Language) 핵심 코드 표현
GPU 내부에서 실행될 fragment shader의 형태는 아래와 같이 직관적으로 구현됩니다.

```wgsl
struct Circle {
    center: vec2<f32>,
    radius_squared: f32,
    color: vec4<f32>,
};

@group(0) @binding(0) var<uniform> circle: Circle;

@fragment
fn main(@builtin(position) frag_coord: vec4<f32>) -> @location(0) vec4<f32> {
    // frag_coord.xy는 현재 스크린의 픽셀 좌표를 나타냄
    let to_center = frag_coord.xy - circle.center;
    let distance_squared = dot(to_center, to_center);
    
    if (distance_squared <= circle.radius_squared) {
        return circle.color;
    } else {
        return vec4<f32>(0.1, 0.1, 0.1, 1.0); // 어두운 배경색
    }
}
```

이 데모는 CPU와 GPU의 연산 방식 차이(순차 처리 vs 극도의 병렬 처리)를 이해하고, 공간의 기하학적 형태를 수식으로 정의하는 임프리시트 서피스(Implicit Surface) 렌더링의 매력을 시각적으로 체험할 수 있는 훌륭한 도구가 될 것입니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/스크린-공간에서의-원-판별-알고리즘-구현-point-in-circle-t/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
