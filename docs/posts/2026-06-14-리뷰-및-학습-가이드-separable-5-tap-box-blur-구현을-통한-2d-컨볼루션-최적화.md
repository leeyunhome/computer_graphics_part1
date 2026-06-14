# [리뷰 및 학습 가이드] Separable 5-Tap Box Blur 구현을 통한 2D 컨볼루션 최적화

이번 커밋은 이미지 처리와 실시간 그래픽스에서 가장 기본적이면서도 중요한 최적화 기법 중 하나인 **Separable Convolution(분리 가능한 컨볼루션)**을 성공적으로 구현한 결과물입니다. 

기존의 2D 컨볼루션 필터를 가로(Horizontal)와 세로(Vertical)의 두 단계 1D 필터로 나누어 적용함으로써 계산 복잡도를 획기적으로 낮추는 개념을 직접 코드로 구현하고 검증하셨습니다. 학습자가 직접 작성한 코드와 구현 개념을 바탕으로 핵심 원리를 분석하고, 향후 최적화를 위한 그래픽스 전문가 피드백을 전달합니다.

---

## 1. 학습자가 직접 구현하며 이해한 핵심 개념

### 2D 필터 분리 가능성 (Separability)
일반적으로 크기가 $5 \times 5$인 2D Box Blur 커널을 이미지에 직접 적용하려면 픽셀당 $5 \times 5 = 25$번의 텍스처 샘플링(혹은 메모리 참조)과 연산이 필요합니다. 

하지만 Box Blur나 Gaussian Blur와 같은 필터는 수학적으로 가로축 1D 커널과 세로축 1D 커널의 곱(외적)으로 분리할 수 있습니다. 즉, $5 \times 5$ 필터를 아래 공식과 같이 가로 $5 \times 1$, 세로 $1 \times 5$ 필터의 연속적인 컨볼루션으로 표현할 수 있습니다.

$$ G(x, y) = F(x, y) * (H_x * H_y) = (F(x, y) * H_x) * H_y $$

이 방식을 사용하면 픽셀당 연산 횟수가 $5 + 5 = 10$번으로 줄어듭니다. 커널의 크기가 $N \times N$으로 커질수록 효율성의 차이는 극적으로 벌어집니다.
* **일반 2D 컨볼루션 복잡도:** $$O(N^2)$$
* **Separable 컨볼루션 복잡도:** $$O(2N)$$

### 핑퐁 버퍼링 (Ping-Pong Buffering)을 통한 파이프라인 흐름
코드 변경사항에서 가로 방향(Horizontal Pass) 연산이 완료된 후, `std::swap(this->pixels, pixelsBuffer);`를 통해 원본 데이터와 임시 버퍼를 교체하는 부분이 구현되어 있습니다. 
이후 이어진 세로 방향(Vertical Pass) 루프에서는 이 교체된 결과를 원본 이미지(`this->pixels`)로 삼아 다시 읽어 들이고, 최종 결과를 다시 `pixelsBuffer`에 기록합니다. 이는 그래픽스 파이프라인에서 렌더 타겟을 번갈아 가며 사용하는 **핑퐁 버퍼링(Ping-Pong Buffering)**의 전형적인 구조를 CPU CPU 메모리 상에서 훌륭하게 모사한 것입니다.

---

## 2. 분리 가능한 5-Tap Box Blur 핵심 알고리즘 (의사코드)

학습자가 작성한 이중 패스(Two-pass) 기반의 Box Blur 알고리즘을 추상화하여 표현하면 다음과 같습니다.

```python
# 5-Tap Separable Box Blur의 전체 흐름

# 가로 방향 가중치 (1D 5-Tap)
kernel_width = 5
weight = 1.0 / kernel_width  # 0.2

function BoxBlur5(image_pixels, temp_buffer):
    # Pass 1: Horizontal Blur
    for each pixel (x, y) in image:
        color_sum = Vector4(0.0)
        for offset in [-2, -1, 0, 1, 2]:
            color_sum += image_pixels[clamp_x(x + offset), y]
        temp_buffer[x, y] = color_sum * weight

    # 가로 블러가 완료된 데이터를 읽기 원본으로 설정하기 위해 버퍼 스왑
    swap(image_pixels, temp_buffer)

    # Pass 2: Vertical Blur (가로 블러 결과를 입력으로 사용)
    for each pixel (x, y) in image:
        color_sum = Vector4(0.0)
        for offset in [-2, -1, 0, 1, 2]:
            color_sum += image_pixels[x, clamp_y(y + offset)]
        temp_buffer[x, y] = color_sum * weight

    # 최종 결과를 image_pixels로 가져오기 위해 다시 한 번 스왑
    swap(image_pixels, temp_buffer)
```

---

## 3. 전문가 피드백 및 다음 단계 가이드

### ① 캐시 지역성(Cache Locality)과 메모리 접근 패턴 분석
* **가로 패스(Horizontal Pass):** 메모리가 가로 방향(`i`)으로 연속적으로 정렬되어 있으므로, 인접한 픽셀을 읽을 때 하드웨어 캐시(L1/L2 캐시)의 이점을 크게 얻습니다.
* **세로 패스(Vertical Pass):** 세로 방향(`j`)으로 인접한 픽셀을 읽기 위해 `i + width * (j + offset)` 메모리 주소에 접근합니다. 이는 `width` 크기만큼 메모리 점프가 일어나기 때문에 **캐시 미스(Cache Miss)**가 빈번하게 발생하여 CPU 연산 속도가 저하될 수 있습니다.
* **개선 팁:** 실시간 그래픽스 API(DirectX 11)에서는 이를 극복하기 위해 이미지 데이터를 **가로/세로 타일(Tile) 단위**로 나누어 GPU 스레드 그룹에 바인딩하고, 고속 메모리 영역에 적재하여 연산하는 기법을 주로 사용합니다.

### ② 반복 횟수(100 Iterations)와 스케일의 한계
현재 구현에서는 더 큰 블러 효과를 얻기 위해 `BoxBlur5`를 100번 반복 실행(`image.BoxBlur5()`)하고 있습니다. CPU 루프 기반에서 대형 이미지에 100회 반복은 매우 큰 오버헤드를 유발합니다.
* **현업에서의 해결책:**
  1. **다운샘플링(Downsampling):** 이미지를 $1/2$ 혹은 $1/4$ 크기로 축소한 뒤 블러를 적용하고 다시 업샘플링하여 합성하는 방식을 사용합니다. (Bloom 효과의 핵심)
  2. **커널 크기 확장:** 컨볼루션 횟수 자체를 늘리는 대신, 9-Tap, 11-Tap 등으로 1D 커널의 크기를 늘리거나, 샘플링 간격을 넓히는 Bilinear Filtering 트릭을 활용합니다.

---

## 4. WebGPU 인터랙티브 데모 섹션

DirectX 11에서 학습한 이 개념을 모던 웹 표준 API인 **WebGPU**의 **Compute Shader**로 시각화한다면 다음과 같은 아키텍처로 구현되어 브라우저에서 실시간으로 구동될 수 있습니다.

### Compute Shader를 활용한 고속 Separable Blur 시각화 구상

```wgsl
// WebGPU WGSL Compute Shader 예시 개념 코드
@group(0) @binding(0) var inputTexture: texture_2d<f32>;
@group(0) @binding(1) var outputTexture: texture_storage_2d<rgba8unorm, write>;

// 로컬 작업 그룹 크기 정의 (가로 16, 세로 16)
@compute @workgroup_size(16, 16)
fn cs_main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let coords = vec2<i32>(global_id.xy);
    var color_sum = vec4<f32>(0.0);
    
    // 가로 패스 예시
    for (var i: i32 = -2; i <= 2; i = i + 1) {
        let sample_coords = coords + vec2<i32>(i, 0);
        color_sum = color_sum + textureLoad(inputTexture, sample_coords, 0);
    }
    
    textureStore(outputTexture, coords, color_sum * 0.2);
}
```

### 웹 브라우저 인터랙티브 시각화 시나리오
1. **듀얼 패스 컴퓨트 파이프라인 (Two-Pass Pipeline):**
   * 브라우저 상에서 첫 번째 Compute Shader가 실행되어 원본 이미지를 가로로 블러링한 후 임시 GPU 텍스처(Buffer A)에 씁니다.
   * 곧바로 두 번째 Compute Shader가 실행되어 Buffer A를 읽어 세로로 블러링한 후 화면에 출력할 텍스처(Buffer B)에 씁니다.
2. **실시간 인터랙션 컨트롤러 제공:**
   * **블러 반복 횟수(Iterations) 슬라이더:** 슬라이더를 통해 GPU에서 컨볼루션 패스를 반복 수행하는 횟수를 실시간으로 제어(0회 ~ 100회)하며, CPU와 달리 **60fps**로 부드럽게 유지되는 프레임 레이트를 확인할 수 있습니다.
   * **가로/세로 개별 시각화 토글:** 가로 패스만 적용된 결과(가로로 길게 늘어진 이펙트)와 두 개의 패스가 모두 적용된 완전한 2D 블러 결과를 실시간으로 비교 감상할 수 있습니다.
3. **효과 체감:**
   * 콜로세움 이미지(`colosseum.jpg`)의 석조 질감과 하늘 경계선이 단계적으로 뭉개지며 부드러운 빛무리(Bloom)의 기초가 되는 광원 확산 이미지를 실시간으로 갱신하는 시각적 피드백을 사용자에게 선사합니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/리뷰-및-학습-가이드-separable-5-tap-box-blur-구현을/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
