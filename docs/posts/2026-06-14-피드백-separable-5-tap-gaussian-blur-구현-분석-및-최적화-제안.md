# [피드백] Separable 5-tap Gaussian Blur 구현 분석 및 최적화 제안

안녕하세요! DirectX 11 / C++ 그래픽스 스터디에 제출하신 커밋을 검토했습니다. 

기존의 단순한 박스 블러(Box Blur)에서 그래픽스 및 이미지 처리에서 매우 중요한 기법인 **가우시안 블러(Gaussian Blur)**, 그중에서도 연산 속도를 획기적으로 줄여주는 **분해 가능(Separable) 구조**로 전환하신 점은 매우 훌륭한 선택입니다.

작성하신 코드와 개념을 바탕으로, 직접 구현하며 이해하신 핵심 그래픽스 이론을 정리하고, 코드 상에서 발생할 수 있는 잠재적인 구조적 문제를 짚어 드리겠습니다.

---

## 1. 학습자가 이해한 핵심 개념: Separable Convolution

학습자님은 2차원 공간에서의 필터링 연산을 1차원 연산 두 번으로 나누어 처리하는 **Separable Convolution**의 강력한 이점을 파악하고 이를 코드로 옮기셨습니다.

### 가우시안 필터의 분리 가능성 (Separability)
2차원 가우시안 분포 공식은 다음과 같이 $x$와 $y$에 대한 두 개의 독립적인 1차원 가우시안 분포의 곱으로 분리될 수 있습니다.

$$G_{2D}(x, y) = \frac{1}{2\pi\sigma^2} e^{-\frac{x^2 + y^2}{2\sigma^2}} = \left( \frac{1}{\sqrt{2\pi}\sigma} e^{-\frac{x^2}{2\sigma^2}} \right) \cdot \left( \frac{1}{\sqrt{2\pi}\sigma} e^{-\frac{y^2}{2\sigma^2}} \right) = G_{1D}(x) \cdot G_{1D}(y)$$

이 수학적 성질 덕분에, $N \times N$ 크기의 2차원 커널을 직접 적용하는 대신, 가로 방향 1차원 커널($1 \times N$)을 먼저 적용한 후 세로 방향 1차원 커널($N \times 1$)을 적용하여 동일한 효과를 낼 수 있습니다.

*   **기존 2D 가우시안 방식의 시간 복잡도:** 픽셀당 $$O(N^2)$$ 번의 샘플링 필요.
*   **Separable 가우시안 방식의 시간 복잡도:** 픽셀당 $$O(N + N) = O(2N)$$ 번의 샘플링 필요.
*   학습자님이 구현하신 5-tap 커널($N=5$)의 경우, 픽셀당 연산 수가 $25$번에서 $10$번으로 대폭 감소합니다. 이터레이션을 100번 반복하는 현재 코드 특성상, 이 최적화는 프레임 레이트 유지에 결정적인 역할을 합니다.

---

## 2. 알고리즘 구조 추상화 (의사코드)

학습자님이 구현하고자 한 Separable Gaussian Blur 알고리즘의 전체 흐름은 다음과 같습니다. 가로 방향(Horizontal Pass)으로 가중합을 계산해 중간 버퍼에 저장하고, 이 결과를 다시 세로 방향(Vertical Pass) 가중합으로 처리하여 최종 이미지를 얻습니다.

```text
function SeparableGaussianBlur(Image input, Image intermediate, Image output, weights)
    // Pass 1: Horizontal Blur
    for each pixel (i, j) in input:
        colorSum = (0, 0, 0, 0)
        for k from -2 to 2:
            neighborColor = input.GetPixel(i + k, j)
            colorSum += neighborColor * weights[k + 2]
        intermediate.SetPixel(i, j, colorSum)

    // Pass 2: Vertical Blur
    for each pixel (i, j) in intermediate:
        colorSum = (0, 0, 0, 0)
        for k from -2 to 2:
            neighborColor = intermediate.GetPixel(i, j + k) // 가로 블러가 적용된 중간 버퍼에서 읽음
            colorSum += neighborColor * weights[k + 2]
        output.SetPixel(i, j, colorSum)
```

---

## 3. 코드 코드 리뷰 및 수정 제안 (중요 디버깅 포인트)

구현하신 코드에서 Separable Blur의 개념은 아주 잘 녹아있지만, **데이터 흐름(Data Flow)** 상에서 매우 치명적인 논리적 오류가 발견되었습니다.

### 문제점 분석
현재 작성하신 `GaussianBlur5()` 함수의 구조를 보면 다음과 같이 동작하고 있습니다.

1.  **가로 Pass:** `this->pixels`에서 원본 픽셀들을 읽어와 가로 가중합을 계산하고, 결과를 `pixelsBuffer`에 저장합니다.
2.  **세로 Pass:** 다시 `this->pixels`에서 원본 픽셀들을 읽어와 세로 가중합을 계산하고, 결과를 `pixelsBuffer`에 덮어씁니다.

즉, **세로 Pass가 작동할 때 가로 Pass의 결과가 반영된 `pixelsBuffer`를 읽지 않고, 블러 처리가 전혀 되지 않은 원본 상태인 `this->pixels`를 다시 읽고 있습니다.** 이로 인해 가로 Pass의 연산 결과는 완전히 무시되고, 최종적으로는 **세로 방향으로만 블러 처리된 결과**가 `pixelsBuffer`에 남게 됩니다.

### 해결 방안 (Ping-Pong Buffer)
가로 블러가 적용된 중간 결과를 세로 블러 연산의 입력으로 사용해야 합니다. 첫 번째 Pass가 끝난 시점에 임시 버퍼의 내용을 원본 데이터 구조로 동기화(복사 혹은 포인터 스왑)해 주어야 합니다.

```cpp
// [수정 예시]
void Image::GaussianBlur5()
{
    // 1. Horizontal Pass (this->pixels -> pixelsBuffer)
    for (int j = 0; j < this->height; j++) {
        for (int i = 0; i < this->width; i++) {
            // ... 가로 가중합 계산 ...
            pixelsBuffer[i + this->width * j] = neighborColorSum;
        }
    }

    // ★ 중요: 첫 번째 Pass 결과를 원본 픽셀로 복사하여 세로 Pass의 입력으로 준비합니다.
    // (또는 포인터를 교환하는 방식을 사용할 수도 있습니다)
    std::copy(pixelsBuffer.begin(), pixelsBuffer.end(), this->pixels.begin());

    // 2. Vertical Pass (this->pixels(가로 블러 적용됨) -> pixelsBuffer)
    for (int j = 0; j < this->height; j++) {
        for (int i = 0; i < this->width; i++) {
            // ... 세로 가중합 계산 ...
            pixelsBuffer[i + this->width * j] = neighborColorSum;
        }
    }
    
    // 최종 결과를 다시 원본에 동기화
    std::copy(pixelsBuffer.begin(), pixelsBuffer.end(), this->pixels.begin());
}
```

이 "핑퐁(Ping-Pong)" 버퍼 메커니즘을 적용하셔야 기획하신 온전한 2차원 가우시안 블러 효과가 나타납니다.

---

## 4. WebGPU 인터랙티브 데모로 확장하기

이 Separable 5-tap Gaussian Blur 알고리즘을 최신 웹 그래픽스 표준인 **WebGPU**의 **Compute Shader(컴퓨트 셰이더)**로 구현하면 극적인 성능 향상을 체감할 수 있는 훌륭한 인터랙티브 데모를 만들 수 있습니다.

### WebGPU 시각화 데모 설계 구조

1.  **동작 방식 및 아키텍처:**
    *   CPU의 이중 루프 대신, 수만 개의 GPU 스레드가 동시에 실행됩니다.
    *   **Workgroup Shared Memory(공유 메모리)**를 사용하여 텍스처 메모리 대역폭을 극적으로 절약합니다. 스레드 그룹이 픽셀 데이터를 공유 메모리에 한 번만 로드(`var<workgroup>`)한 후 가중치 연산을 수행하므로 캐시 효율이 극대화됩니다.
    *   두 개의 Compute Pipeline(가로 패스, 세로 패스)을 구성하여, GPU 내부에서 첫 번째 컴퓌팅 패스의 출력 텍스처를 두 번째 컴퓌팅 패스의 입력 텍스처로 직접 전달(Ping-Pong 렌더 타깃 바인딩)합니다.

2.  **화면 구성 및 인터랙티브 요소:**
    *   **좌측 화면 (Original Image):** 블러 처리가 되지 않은 'colosseum.jpg'를 렌더링합니다.
    *   **우측 화면 (Processed Image):** 실시간으로 Compute Shader가 적용된 블러 이미지를 보여줍니다.
    *   **UI 컨트롤러:**
        *   **Sigma ($$\sigma$$) 슬라이더:** 가우시안 분포의 표준편차를 실시간으로 조절하여 흐려짐의 강도를 제어합니다. (실시간으로 커널의 가중치 배열 `weights`가 GPU Uniform Buffer로 전송되어 업데이트됩니다)
        *   **Iteration 수치 조절:** CPU에서 100번 돌릴 때 버벅였던 연산이, WebGPU GPU 가속을 통해 100번 이상 반복해도 부드럽게 60FPS를 유지하는 모습을 시각적 성능 그래프와 함께 비교하여 보여줍니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/피드백-separable-5-tap-gaussian-blur-구현-분석-/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
