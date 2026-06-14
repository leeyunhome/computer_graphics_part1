# [코드 리뷰] Separable 5-Tap Gaussian Blur 구현 분석 및 최적화

축하합니다! 이번 커밋은 2D 이미지 처리에서 성능 최적화의 핵심 분기점이 되는 **분할 가능한 컨볼루션(Separable Convolution)** 기법을 성공적으로 구현한 중요한 단계입니다. 

기존의 단순한 박스 블러(Box Blur)에서 벗어나, 가우시안 분포(Gaussian Distribution)를 따르는 가중치를 적용하여 훨씬 자연스럽고 부드러운 블러 효과를 구현하셨습니다. 작성하신 코드를 바탕으로 컴퓨터 그래픽스 관점에서의 핵심 개념과 구현 디테일, 그리고 향후 GPU 이전을 위한 조언을 정리해 드립니다.

---

## 1. 학습자가 직접 구현하며 이해한 핵심 그래픽스 개념

### 1.1 분할 가능한 컨볼루션 (Separable Convolution)
일반적으로 $K \times K$ 크기의 2D 필터 커널을 이미지에 직접 적용하려면 픽셀당 $K^2$ 번의 텍스처 샘플링(연산)이 필요합니다. 5-tap 커널의 경우 픽셀당 25번의 연산이 필요합니다.

하지만 가우시안 필터처럼 수학적으로 가로와 세로 축으로 분리 가능한(Separable) 커널은 다음과 같이 두 번의 1차원 패스(Pass)로 나누어 처리할 수 있습니다.
* **Pass 1 (가로 블러):** 가로 방향 1D 가우시안 필터 적용 ($K$ 번 연산)
* **Pass 2 (세로 블러):** 세로 방향 1D 가우시안 필터 적용 ($K$ 번 연산)

결과적으로 연산량이 $K^2$에서 $2K$로 감소합니다. 이번 구현에서 선택한 5-tap의 경우, **25번의 연산이 단 10번의 연산으로 감소**하여 성능이 약 2.5배 향상되는 효과를 얻었습니다. 100회의 반복 연산(Iterations)이 지정되어 있으므로, 이 최적화가 전체 프레임 레이트에 미치는 영향은 지대합니다.

### 1.2 가우시안 가중치와 에너지 보존
수학적으로 1차원 가우시안 분포는 다음과 같이 정의됩니다.

$$G(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{x^2}{2\sigma^2}}$$

커밋에 사용된 가중치 벡터 $W = [0.0545, 0.2442, 0.4026, 0.2442, 0.0545]$는 $\sigma \approx 1.0$인 가우시안 함수를 이산화(Discretize)한 결과물입니다. 이 가중치들의 합을 구해보면 다음과 같습니다.

$$\sum_{i=0}^{4} W_i = 0.0545 + 0.2442 + 0.4026 + 0.2442 + 0.0545 = 1.0$$

가중치의 합이 정확히 $1.0$이 되는 것은 그래픽스에서 매우 중요합니다. 이 합이 1보다 크면 블러를 반복할수록 이미지가 점점 밝아지며(Saturation), 1보다 작으면 이미지가 어두워지게 됩니다. 가중치 합을 1로 유지함으로써 **에너지 보존(Energy Conservation)** 법칙을 만족하여 이미지 고유의 밝기를 유지할 수 있습니다.

---

## 2. 알고리즘 파이프라인 분석 및 추상화

구현하신 가우시안 블러 알고리즘은 아래와 같은 2단계 파이프라인 구조를 가집니다. 원본 이미지 버퍼와 임시 버퍼 사이의 관계에 유의해야 합니다.

### [가우시안 블러 실행 흐름도]
```
[원본 이미지 (this->pixels)]
       │
       ▼ (Pass 1: 가로 방향 가중치 누적)
[가로 블러 완료 임시 버퍼 (pixelsBuffer)]
       │
       ▼ (버퍼 스왑 및 동기화: pixelsBuffer -> pixels)
[중간 결과 이미지 (this->pixels)]
       │
       ▼ (Pass 2: 세로 방향 가중치 누적)
[최종 가우시안 블러 완료 (pixelsBuffer)]
```

### [핵심 알고리즘 의사코드]
```cpp
// 1D 가우시안 커널 가중치 정의
const float weights[5] = { 0.0545f, 0.2442f, 0.4026f, 0.2442f, 0.0545f };

// Pass 1: Horizontal Blur
for (int y = 0; y < height; y++) {
    for (int x = 0; x < width; x++) {
        float4 accumulatedColor = float4(0.0f);
        for (int step = 0; step < 5; step++) {
            // 가로 방향 이웃 픽셀 샘플링 (x + step - 2)
            float4 neighbor = SamplePixel(x + step - 2, y);
            accumulatedColor += neighbor * weights[step];
        }
        tempBuffer[x, y] = accumulatedColor;
    }
}

// 중요: Pass 1의 결과가 Pass 2의 입력이 되도록 버퍼를 갱신해야 합니다.
SyncBuffers(sourceBuffer, tempBuffer);

// Pass 2: Vertical Blur
for (int y = 0; y < height; y++) {
    for (int x = 0; x < width; x++) {
        float4 accumulatedColor = float4(0.0f);
        for (int step = 0; step < 5; step++) {
            // 세로 방향 이웃 픽셀 샘플링 (y + step - 2)
            float4 neighbor = SamplePixel(x, y + step - 2);
            accumulatedColor += neighbor * weights[step];
        }
        tempBuffer[x, y] = accumulatedColor;
    }
}
```

> **전문가 가이드:** 코드 변경사항의 생략된 부분(`...`)에서 첫 번째 패스(Horizontal)가 끝난 후 `pixelsBuffer`의 내용을 반드시 `this->pixels`로 복사하거나 포인터를 교체(Swap)해주어야 합니다. 그렇지 않으면 두 번째 패스(Vertical)가 가로 블러가 적용되지 않은 원본 이미지를 다시 참조하게 되어 올바른 2D 가우시안 블러가 완성되지 않습니다.

---

## 3. 코드의 그래픽스적 한계와 개선 방향 (DX11 관점)

현재 구현은 CPU 루프를 통해 픽셀을 하나씩 제어하고 있습니다. 가로 세로 100회 반복 처리는 CPU에게 매우 가혹한 연산이며, 실시간 렌더링(60fps 이상) 환경에서는 메인 스레드 병목의 주원인이 됩니다. 이 코드를 DirectX 11 하드웨어 가속으로 이전할 때 고려해야 할 두 가지 팁을 드립니다.

1. **컴퓨트 셰이더(Compute Shader) 활용:**
   DX11의 `ID3D11ComputeShader`를 사용하여 이 가로/세로 패스를 GPGPU 연산으로 전환할 수 있습니다. 스레드 그룹 공유 메모리(Group Shared Memory, `groupshared`)를 활용하면 텍스처 샘플링 횟수를 획기적으로 줄일 수 있습니다.
2. **선형 필터링 하드웨어 활용 (Bilinear Filtering Trick):**
   GPU의 텍스처 샘플러는 하드웨어 수준에서 선형 보간(Bilinear Interpolation)을 지원합니다. 정수 좌표가 아닌 픽셀 사이의 소수점 좌표를 샘플링하면, 단 한 번의 샘플링으로 두 픽셀의 가중치 평균값을 얻을 수 있습니다. 이를 이용하면 **5-tap 가우시안 블러를 단 3번의 텍스처 샘플링(3-tap)으로 완벽하게 최적화**할 수 있습니다.

---

## 4. WebGPU 인터랙티브 데모 미리보기

이 최적화된 Separable 가우시안 블러 알고리즘을 모던 웹 그래픽스 API인 **WebGPU의 Compute Shader**로 구현한다면 다음과 같이 매우 빠르고 대화식인 시각화 데모를 구성할 수 있습니다.

* **동작 원리:** 
  웹 브라우저 상에서 GPU 메모리에 이미지를 텍스처로 업로드한 뒤, WGSL(WebGPU Shading Language)로 작성된 두 개의 Compute Pass(`horizontal_blur`, `vertical_blur`)를 실행합니다. 
* **워크그룹(Workgroup) 구성:**
  각 픽셀을 1:1로 매핑하는 가로 $16 \times 1$, 세로 $1 \times 16$ 형태의 1차원 워크그룹 스레드를 구성하여 GPU 병렬 처리를 극대화합니다.
* **실시간 인터랙티브 UI:**
  * **Sigma ($\sigma$) 슬라이더:** 실시간으로 가우시안 가중치 공식을 계산하여 커널 값을 업데이트하고 블러의 반경을 조절합니다.
  * **Iteration 카운터:** CPU에서는 100회 반복 시 수 초 동안 멈추던 연산이, WebGPU 환경에서는 매 프레임(60fps)마다 100회 이상의 패스를 누적 연산해도 전혀 끊김 없이 실시간으로 부드럽게 흐려지는 모습을 관찰할 수 있습니다.
  * **텍스처 디버그 뷰:** 원본 이미지, 가로 패스만 적용된 중간 단계(Motion blur 느낌), 그리고 최종 가우시안 블러가 완성된 결과를 마우스 드래그를 통해 실시간 Split View로 비교할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/코드-리뷰-separable-5-tap-gaussian-blur-구현-분/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
