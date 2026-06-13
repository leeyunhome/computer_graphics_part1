# [코드 리뷰] Separable 5-Tap Box Blur 가로 패스 구현 및 이미지 전처리

축하합니다! DirectX 11 및 C++ 기반의 그래픽스 스터디에서 훌륭한 단계에 도달하셨습니다. 이번 커밋은 블룸(Bloom) 효과의 핵심 빌딩 블록이 되는 **분리 가능한 컨볼루션(Separable Convolution)**의 첫 단추인 '가로 방향 1차원 박스 블러(Horizontal Box Blur)'와 '이미지 밝기 전처리'를 성공적으로 구현한 코드입니다.

학습자님께서 코드를 직접 작성하며 깊이 있게 이해한 그래픽스 이론과 핵심 개념들을 정리해 드립니다.

---

## 1. 직접 구현하며 학습한 핵심 그래픽스 개념

### ① 분리 가능한 컨볼루션 (Separable Convolution)
일반적인 $5 \times 5$ 크기의 2차원 필터를 이미지에 적용하려면 픽셀당 총 $5 \times 5 = 25$번의 텍셀 페치(Texel Fetch) 및 연산이 필요합니다. 이미지의 해상도가 커질수록 이 연산량은 엄청난 성능 병목을 야기합니다.

이를 해결하기 위해 수학적으로 2차원 필터 커널을 두 개의 1차원 필터(가로, 세로)로 분리하여 연속으로 적용하는 기법이 바로 **Separable Convolution**입니다.

$$ 2D\text{ Kernel} = 1D\text{ Vertical Kernel} \times 1D\text{ Horizontal Kernel} $$

이 기법을 적용하면 연산량이 픽셀당 $O(N^2)$에서 $O(2N)$으로 획기적으로 줄어듭니다. 
이번에 구현하신 5-tap 블러의 경우:
* **기존 2차원 방식**: 픽셀당 **25회** 연산
* **Separable 방식**: 가로 5회 + 세로 5회 = 픽셀당 **10회** 연산 (약 2.5배 성능 향상)

현재 커밋에서는 이 중 첫 번째 단계인 **가로 방향(Horizontal) 1차원 패스**를 완벽하게 구현하셨습니다.

### ② 5-Tap Box Blur의 수학적 모델
박스 블러는 주변 영역의 픽셀 값들을 동일한 가중치로 평균 내는 필터입니다. 5-tap 가로 블러는 현재 픽셀 $i$를 기준으로 좌우 2개씩의 이웃 픽셀($i-2, i-1, i, i+1, i+2$)을 샘플링하여 평균을 구합니다.

가중치는 모든 탭이 동일하게 $0.2 \left(\frac{1}{5}\right)$씩 나누어 가집니다. 이를 수학식으로 표현하면 다음과 같습니다.

$$ I_{\text{horizontal}}(i, j) = \sum_{s = -2}^{2} I_{\text{original}}(i + s, j) \times 0.2 $$

### ③ 이중 버퍼링(Double Buffering)을 통한 데이터 무결성 유지
블러 연산을 할 때, 원래 이미지(`this->pixels`)에 연산 결과를 실시간으로 덮어쓰게 되면 다음 픽셀 연산 시 이미 블러 처리가 완료된(오염된) 데이터를 읽게 됩니다. 

학습자님께서는 연산 결과를 임시 버퍼인 `pixelsBuffer`에 쓰고, 루프가 끝난 뒤 `std::swap`을 통해 한 번에 교체하는 **이중 버퍼링 기법**을 정확히 적용하여 필터의 왜곡 현상을 방지하셨습니다.

---

## 2. 핵심 알고리즘 구조 (추상화 및 의사코드)

강의 원본 코드의 디테일을 유지하되, 알고리즘의 본질을 명확히 이해할 수 있도록 추상화한 의사코드(Pseudo-code)입니다.

```cpp
// 1단계: 이미지 밝기 조절 (Pre-processing)
for each pixel in Image:
    pixel.rgb = pixel.rgb * 1.2f // 모든 RGB 채널의 에너지를 균일하게 증폭

// 2단계: 가로 방향 5-Tap Box Blur 실행
for y from 0 to Image.Height:
    for x from 0 to Image.Width:
        color_accumulator = (0, 0, 0)
        
        // [-2, -1, 0, 1, 2] 범위의 가로 이웃 샘플링
        for offset from -2 to 2:
            neighbor_color = GetPixel(x + offset, y) // 경계선 예외 처리가 포함된 픽셀 획득
            color_accumulator.rgb += neighbor_color.rgb
            
        // 균일한 가중치(0.2)를 곱하여 결과 버퍼에 기록
        TemporaryBuffer[x, y].rgb = color_accumulator.rgb * 0.2f

// 3단계: 임시 버퍼와 원본 버퍼 교체 (Swap)
Swap(Image.Pixels, TemporaryBuffer)
```

---

## 3. 코드 개선 및 최적화 제안 (전문가 피드백)

1. **경계선 처리(Boundary Handling)**: `GetPixel(i + si - 2, j)` 함수 내부에서 이미지 경계 밖의 인덱스에 접근할 때 Clamp(가장자리 픽셀 복사) 처리가 잘 되어 있는지 확인하는 것이 중요합니다.
2. **SIMD / 병렬화 활용**: 현재 가로 패스 루프에는 `#pragma omp parallel for`가 빠져 있습니다. 세로 패스에 적용된 것처럼 가로 패스에도 OpenMP를 활성화하면 멀티코어 CPU 환경에서 비약적인 속도 향상을 얻을 수 있습니다.

---

## 4. WebGPU 인터랙티브 데모 (WebGPU Interactive Demo)

이 C++ CPU 기반의 알고리즘을 최신 웹 그래픽스 표준인 **WebGPU Compute Shader**로 옮겨 브라우저에서 실시간으로 시각화한다면 다음과 같은 아키텍처와 화면으로 구성할 수 있습니다.

```
+-------------------------------------------------------------+
|                     [ WebGPU 실시간 데모 ]                  |
|  [원본 이미지 (Colosseum)]  --->  [ 슬라이더: 밝기 (1.2x) ]   |
|                                                             |
|                         [ 연산 단계 ]                        |
|   Compute Shader Pass 1: 가로 블러 (현재 구현 단계)           |
|   Compute Shader Pass 2: 세로 블러 (대기 중)                 |
|                                                             |
|  [결과 화면]                                                |
|  +---------------------------+---------------------------+  |
|  | 원본 (Brightened)         | 가로 블러 적용 (Horizontal) |  |
|  |                           | (가로로 은은하게 번진 효과) |  |
|  +---------------------------+---------------------------+  |
+-------------------------------------------------------------+
```

### WebGPU 구현 방식 요약
1. **Compute Shader (WGSL) 작성**: 
   * CPU의 이중 루프를 GPU의 수천 개 스레드로 병렬 처리합니다.
   * `workgroup` 스레드 레이아웃을 정의하고, 픽셀 데이터를 GPU 내부의 초고속 메모리 영역인 **공유 메모리(Shared Memory)**에 적재하여 텍스처 샘플링 오버헤드를 줄입니다.
2. **인터랙티브 컨트롤러**:
   * 사용자가 웹브라우저 화면에서 슬라이더를 조절하여 이미지의 밝기 배수(예: `1.0` ~ `2.0`)를 실시간으로 변경하면, GPU Constant Buffer를 통해 값이 즉시 업데이트되어 화면에 60fps로 블러 효과가 반영됩니다.
3. **가로 블러의 시각적 특징**:
   * 세로 블러 패스를 거치기 전이므로, 이미지 내 콜로세움의 기둥이나 아치 같은 격자 무늬가 가로 방향으로만 부드럽게 번져 있는 독특한 시각적 효과(마치 아나모픽 렌즈 플레어의 초기 단계 같은 느낌)를 브라우저에서 직접 관찰할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/코드-리뷰-separable-5-tap-box-blur-가로-패스-구현-/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
