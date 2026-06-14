# 분리형 가우시안 블러(Separable Gaussian Blur)를 이용한 Bloom 효과 구현 리뷰

이번 커밋은 3차원 컴퓨터 그래픽스 및 포스트 프로세싱(Post-processing)의 핵심 효과 중 하나인 **블룸(Bloom) 효과**를 구현하기 위해, 밝은 영역(Bright region)을 추출하고 이에 대해 **분리형 가우시안 블러(Separable Gaussian Blur)**를 반복 적용하는 핵심 단계를 완성한 단계입니다.

학습자가 작성한 소스 코드와 커밋 내용을 바탕으로, 이 구현에 담긴 그래픽스 이론과 수식적 배경, 그리고 최적화 기법을 분석하고 피드백을 전달합니다.

---

## 1. 핵심 그래픽스 개념 및 알고리즘 의도

블룸 효과는 강한 빛이 카메라 렌즈나 눈의 망막에 부딪힐 때 발생하는 빛 번짐 현상(Glow)을 시뮬레이션합니다. 이를 구현하기 위해 학습자는 다음과 같은 3단계 파이프라인 중 **핵심 필터링 단계**를 구현했습니다.

1. **Thresholding (밝기 추출)**: 입력 이미지에서 특정 임계값($th = 0.3$) 이상의 밝기를 가진 픽셀만 남기고 나머지는 검은색으로 마스킹합니다.
2. **Blurring (번짐 효과 - 이번 커밋의 핵심)**: 추출된 밝은 영역을 흐리게 만들어 부드럽게 퍼지는 빛을 생성합니다.
3. **Composition (합성)**: 원본 이미지에 블러 처리된 이미지를 가산(Additive blending)하여 최종 결과물을 만듭니다.

---

## 2. 분리형 컨볼루션(Separable Convolution)의 수학적 이해

학습자의 코드에서 가장 돋보이는 설계는 `BoxBlur5`와 `GaussianBlur5`에 적용된 **Separable Convolution** 기법입니다.

### 2D 가우시안 필터의 분리성
2차원 가우시안 분포 함수는 다음과 같이 $x$와 $y$ 변수로 완전히 분리(factorization)될 수 있습니다.

$$ G(x, y) = \frac{1}{2\pi\sigma^2} e^{-\frac{x^2 + y^2}{2\sigma^2}} = \left( \frac{1}{\sqrt{2\pi}\sigma} e^{-\frac{x^2}{2\sigma^2}} \right) \cdot \left( \frac{1}{\sqrt{2\pi}\sigma} e^{-\frac{y^2}{2\sigma^2}} \right) = G(x) \cdot G(y) $$

이 수학적 성질 덕분에, $5 \times 5$ 크기의 2차원 커널을 이미지에 직접 적용하는 대신, **가로 방향 1차원 필터($1 \times 5$)**를 적용한 뒤 그 결과에 **세로 방향 1차원 필터($5 \times 1$)**를 연속으로 적용해도 수학적으로 완전히 동일한 결과를 얻을 수 있습니다.

### 연산량 감소 효과
이미지의 가로 크기를 $W$, 세로 크기를 $H$, 커널의 크기를 $K$라고 할 때 픽셀당 연산량의 차이는 다음과 같습니다.

* **일반 2D 컨볼루션**: $\mathcal{O}(W \times H \times K^2)$ (픽셀당 $K^2$번의 샘플링 필요, $5 \times 5 = 25$회)
* **분리형 컨볼루션**: $\mathcal{O}(W \times H \times 2K)$ (픽셀당 $2K$번의 샘플링 필요, $5 + 5 = 10$회)

커널 크기가 커질수록 이 효율성의 차이는 기하급수적으로 벌어지며, 실시간 그래픽스 처리를 가능하게 하는 핵심 최적화 요소입니다.

---

## 3. 구현된 가우시안 커널 가중치 분석

학습자가 코드에 선언한 가우시안 1차원 가중치는 다음과 같습니다.
```cpp
const float weights[5] = { 0.0545f, 0.2442f, 0.4026f, 0.2442f, 0.0545f };
```
이 가중치들의 합을 계산해 보면 다음과 같습니다.

$$ \sum_{i=1}^{5} w_i = 0.0545 + 0.2442 + 0.4026 + 0.2442 + 0.0545 = 1.0000 $$

가중치의 합이 정확히 $1.0$이 되도록 정규화(Normalization)되어 있습니다. 이는 필터를 적용하는 과정에서 에너지가 보존되어, **이미지 전체의 밝기가 왜곡되거나 원치 않게 밝아지거나 어두워지는 현상(Gain/Loss)을 방지**하기 위한 올바른 설계입니다.

---

## 4. 핵심 알고리즘 의사코드 (Abstracted Workflow)

CPU 환경에서 병렬성(OpenMP)을 활용하여 다중 블러를 수행하는 구조를 추상화하면 다음과 같습니다.

```python
# Bloom 알고리즘 추상화

def ExtractBrightRegions(image, threshold):
    for pixel in image:
        luminance = DotProduct(pixel.rgb, [0.2126, 0.7152, 0.0722])
        if luminance < threshold:
            pixel.rgb = Black
    return image

def GaussianBlur1D(image, direction):
    buffer = CreateEmptyBufferLike(image)
    weights = [0.0545, 0.2442, 0.4026, 0.2442, 0.0545]
    
    # OpenMP를 통한 멀티스레드 가속화 영역
    ParallelFor y in range(height):
        for x in range(width):
            colorSum = ZeroVector
            for i in range(-2, 3):
                sampleCoord = x + i if direction == Horizontal else y + i
                colorSum += GetClampedPixel(sampleCoord) * weights[i + 2]
            buffer[x, y] = colorSum
            
    return buffer

def BloomPipeline(inputImage, threshold, numRepeat):
    # 1. 밝은 영역만 남기기
    brightImage = ExtractBrightRegions(inputImage, threshold)
    
    # 2. 지정된 횟수(numRepeat)만큼 가우시안 블러 반복 적용 (커밋된 수정 사항)
    for _ in range(numRepeat):
        # 가로 블러 적용 후 세로 블러 순차 적용
        brightImage = GaussianBlur1D(brightImage, Horizontal)
        brightImage = GaussianBlur1D(brightImage, Vertical)
        
    # 3. 최종 원본 이미지와 블러 이미지 합성
    return BlendAdditive(inputImage, brightImage)
```

---

## 5. 전문가적 시각에서의 피드백 및 최적화 제안

### 장점
1. **OpenMP 가속 적용**: `#pragma omp parallel for`를 적절히 활용하여 CPU 멀티코어 환경에서 픽셀 연산을 병렬 처리했습니다. 이는 수많은 반복 연산(`numRepeat = 1000`) 시 처리 시간을 획기적으로 낮춰줍니다.
2. **Boundary 처리**: `GetPixel` 내부에서 `std::clamp`를 활용하여 이미지 경계 영역 밖을 참조할 때 발생하는 인덱스 오버플로우 문제를 안정적으로 해결했습니다.

### 개선 제안
1. **CPU 연산의 한계와 numRepeat**: 현재 `numRepeat` 값이 `1000`으로 설정되어 있습니다. CPU 환경에서 5x5 블러를 1000번 왕복(실제 가로/세로 총 2000번의 패스)하는 것은 병렬 처리를 하더라도 매우 무겁습니다.
   * **대안**: 다운샘플링(Downsampling) 기법을 도입하는 것을 추천합니다. 이미지를 $1/2$ 또는 $1/4$ 크기로 해상도를 줄인 후 가우시안 블러를 적용하면, 적은 커널 크기로도 넓은 반경의 번짐 효과를 매우 빠르게 얻을 수 있습니다.
2. **Ping-Pong Buffer 최적화**: 매 프레임이나 루프마다 새로운 `vector`인 `pixelsBuffer`를 할당하고 해제하는 대신, 사전에 두 개의 큰 버퍼만 선언해 두고 포인터를 교환하는 **핑퐁(Ping-pong) 버퍼링 기법**을 사용하면 메모리 할당 오버헤드를 줄일 수 있습니다.

---

## 6. WebGPU 인터랙티브 데모 시각화 제안

이 알고리즘을 최신 웹 그래픽스 API인 **WebGPU**의 **Compute Shader**를 이용해 브라우저에서 실시간으로 구현한다면 훨씬 극적인 성능 향상을 체감할 수 있습니다.

```wgsl
// WebGPU Compute Shader 예시 (Horizontal Pass)
@group(0) @binding(0) var inputTex: texture_2d<f32>;
@group(0) @binding(1) var outputTex: texture_storage_2d<rgba8unorm, write>;

const weights = array<f32, 5>(0.0545, 0.2442, 0.4026, 0.2442, 0.0545);

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let size = textureDimensions(inputTex);
    if (id.x >= size.x || id.y >= size.y) { return; }

    var colorSum = vec4<f32>(0.0);
    for (var i: i32 = -2; i <= 2; i++) {
        let sampleCoord = vec2<i32>(
            clamp(i32(id.x) + i, 0, i32(size.x) - 1),
            i32(id.y)
        );
        colorSum += textureLoad(inputTex, sampleCoord, 0) * weights[i + 2];
    }
    
    textureStore(outputTex, id.xy, vec4<f32>(colorSum.rgb, 1.0));
}
```

### WebGPU에서 구현하는 인터랙티브 시각화 시나리오
1. **임계값(Threshold) 실시간 조절**: UI 슬라이더를 통해 `threshold`를 $0.0$에서 $1.0$까지 조정하며, 원본 이미지에서 블룸 효과가 시작되는 영역이 동적으로 변화하는 모습을 확인할 수 있습니다.
2. **블러 반복 횟수(numRepeat) vs 성능 그래프**: WebGPU Compute Shader의 강력한 병렬 처리 능력 덕분에 CPU에서 수 초가 걸리던 `numRepeat = 1000` 연산이 GPU에서는 실시간(60fps)으로 돌아가는 극적인 성능 차이를 웹 페이지상에서 실시간 그래프와 함께 시각화할 수 있습니다.
3. **가로/세로 분리 패스 시각화**: 가로 블러만 적용된 상태(Horizontal stretch)와 가로/세로가 모두 적용된 상태를 각각 화면에 출력하여, **Separable Convolution**의 동작 원리를 직관적으로 이해할 수 있는 비교 뷰(Split View)를 제공합니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/분리형-가우시안-블러separable-gaussian-blur를-이용한-/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
