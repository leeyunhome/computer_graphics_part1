# 실시간 픽셀 감쇄(Pixel Decay)를 통한 점진적 암전 효과 구현

학습자는 이번 커밋을 통해 정적인 이미지 필터링 단계를 넘어, **매 프레임 호출되는 업데이트 루프(Update Loop)를 활용한 동적 비주얼 효과(Dynamic Visual Effect)**의 기초를 성공적으로 구현하였습니다. 

---

## 1. 학습자가 직접 구현하며 이해한 핵심 개념

### 1) 정적 처리(Static)와 동적 처리(Dynamic)의 차이
이전 단계에서는 생성자(Constructor)에서 이미지를 단 한 번만 밝게 만들거나 어둡게 만드는 정적 처리를 수행했습니다. 하지만 이번 변경을 통해 CPU의 `Update` 루프 내에서 매 프레임 이미지 데이터를 수정하도록 구조를 변경했습니다. 이는 시간의 흐름에 따라 변화하는 애니메이션 효과나 비주얼 피드백을 구현하는 그래픽스 프로그래밍의 핵심 패러다임입니다.

### 2) 지수적 감쇄(Exponential Decay)를 통한 잔상 및 암전 효과
매 프레임마다 이전 프레임의 픽셀 값에 $1.0$보다 작은 상수(여기서는 $0.99$)를 곱해줌으로써, 시간에 따라 밝기가 서서히 줄어드는 **지수적 감쇄(Exponential Decay)** 효과를 물리적으로 모사했습니다. 이는 모션 블러, 블루밍의 잔상 효과(Decay), 혹은 연기나 불꽃 같은 파티클의 수명(Lifetime)에 따른 페이드아웃을 구현할 때 표준적으로 사용되는 기법입니다.

---

## 2. 핵심 수학 공식

프레임 $t$에서의 특정 픽셀의 RGB 색상 벡터를 $\mathbf{C}_t$, 감쇄 인자(Decay factor)를 $d = 0.99$라고 할 때, 매 프레임 적용되는 수식은 다음과 같습니다.

$$ \mathbf{C}_t = \text{clamp}(\mathbf{C}_{t-1} \times d, 0.0, 1.0) $$

이를 최초 이미지 상태 $\mathbf{C}_0$와 프레임 수 $n$에 대해 일반화하면 다음과 같은 지수 함수 식으로 표현됩니다.

$$ \mathbf{C}_n = \mathbf{C}_0 \times (0.99)^n $$

*   $0.99$라는 값은 $1.0$에 매우 가깝기 때문에 급격히 어두워지지 않고, 부드럽고 자연스럽게 페이드아웃(Fade-out)되는 시각적 효과를 낳습니다.
*   `clamp` 함수는 수치적 오버플로우나 언더플로우를 방지하여 최종 RGB 값이 항상 유효한 색상 영역인 $[0.0, 1.0]$ 내에 머물도록 보장합니다.

---

## 3. 알고리즘 추상화 및 의사코드

현재 구현은 CPU가 이미지 전체 버퍼를 순회하며 픽셀 값을 직접 수정하는 방식입니다. 이 흐름을 추상화하면 다음과 같습니다.

```text
Function Update(deltaTime):
    decayFactor = 0.99
    minBound = 0.0
    maxBound = 1.0

    // 이미지의 모든 픽셀을 순회 (CPU 렌더링 루프)
    For each pixel in Image.Pixels:
        pixel.R = Clamp(pixel.R * decayFactor, minBound, maxBound)
        pixel.G = Clamp(pixel.G * decayFactor, minBound, maxBound)
        pixel.B = Clamp(pixel.B * decayFactor, minBound, maxBound)
        
    // 변경된 픽셀 데이터를 GPU의 텍스처 버퍼로 업로드 및 화면 출력 준비
    UploadToGPUTexture(Image)
```

> **전문가의 조언**: 현재 CPU 상에서 가로 $\times$ 세로 크기만큼 루프를 돌며 픽셀을 연산하는 방식은 학습 단계에서 개념을 이해하기에는 아주 좋습니다. 그러나 해상도가 높아질수록 CPU 병목(Bottleneck)이 발생하므로, 실무 및 릴리즈 단계에서는 이 연산을 GPU의 픽셀 쉐이더(Pixel Shader)나 컴퓨트 쉐이더(Compute Shader)로 이관하여 병렬 처리해야 합니다.

---

## 4. WebGPU 인터랙티브 데모

이 개념을 현대 웹 그래픽스 표준인 **WebGPU** 환경으로 이식하여, 브라우저에서 실시간 Compute Shader로 구동하면 어떻게 시각화될 수 있을지 설명합니다.

### 1) 작동 메커니즘
*   **컴퓨트 쉐이더(Compute Shader)**: CPU 대신 GPU의 수천 개 코어가 이미지의 모든 픽셀을 동시에 병렬로 계산합니다. 2D 스레드 그룹 워크그룹(Workgroup)을 픽셀 좌표와 1:1 매핑하여 연산 속도를 극대화합니다.
*   **텍스처 바인딩(Texture Binding)**: 읽기/쓰기가 모두 가능한 저장용 텍스처(Storage Texture) 바인딩을 사용하여, 이전 프레임의 결과가 저장된 텍스처를 직접 수정(In-place modification)합니다.

### 2) WebGPU WGSL 컴퓨트 쉐이더 예시 코드 (추상화)
```wgsl
@group(0) @binding(0) var textureData : texture_storage_2d<rgba8unorm, read_write>;

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) global_id : vec3<u32>) {
    let coords = vec2<i32>(global_id.xy);
    let size = textureDimensions(textureData);

    // 이미지 경계 검사
    if (coords.x >= size.x || coords.y >= size.y) {
        return;
    }

    // 1. 현재 프레임의 픽셀 컬러 읽기
    var color = textureLoad(textureData, coords);

    // 2. 점진적 감쇄 적용 (0.99 곱하기) 및 Clamp
    color.r = clamp(color.r * 0.99, 0.0, 1.0);
    color.g = clamp(color.g * 0.99, 0.0, 1.0);
    color.b = clamp(color.b * 0.99, 0.0, 1.0);

    // 3. 다시 텍스처에 쓰기
    textureStore(textureData, coords, color);
}
```

### 3) 데모 시각화 모습
*   **사용자 인터랙션**: 웹 브라우저 화면에서 마우스를 클릭하거나 드래그하는 영역에 흰색(1.0, 1.0, 1.0) 빛이 칠해집니다.
*   **실시간 감쇄**: 마우스를 떼는 순간, 컴퓨트 쉐이더가 매 프레임 위 쉐이더를 실행하여 궤적이 서서히 어두워지며 사라집니다. 마치 밤하늘의 불꽃놀이나 야광 페인팅처럼 실시간으로 반응하는 인터랙티브한 잔상 디스플레이를 감상할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/실시간-픽셀-감쇄pixel-decay를-통한-점진적-암전-효과-구현/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
