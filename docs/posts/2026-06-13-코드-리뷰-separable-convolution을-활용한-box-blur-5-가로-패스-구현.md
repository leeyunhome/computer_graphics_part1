# [코드 리뷰] Separable Convolution을 활용한 Box Blur 5 가로 패스 구현

학습자가 작성한 커밋은 이미지 프로세싱 및 블룸(Bloom) 효과의 핵심 기초가 되는 **분리 가능한 합성곱(Separable Convolution)**을 활용하여 5x5 박스 블러(Box Blur 5)의 가로 패스(Horizontal Pass)를 활성화하고 테스트하는 단계를 담고 있습니다. 

단순히 전체 이미지의 밝기를 균일하게 올리던 기존 코드(`image.pixels[i].v[0] *= 1.2f`)를 주석 처리하고, 인접 픽셀들의 공간적 정보를 활용하는 필터 기반의 블러 알고리즘으로 전환한 점이 돋보입니다. 학습자가 이 작업을 통해 직접 구현하고 이해한 핵심 그래픽스 개념들을 정리해 드립니다.

---

## 1. 학습자가 직접 구현하며 이해한 핵심 개념

### ① 분리 가능한 합성곱 (Separable Convolution)
일반적으로 2차원 이미지에 $N \times N$ 크기의 커널로 합성곱 연산을 적용하려면 픽셀당 $N^2$ 번의 텍스처 샘플링(혹은 메모리 접근)이 필요합니다. 하지만 커널이 가로와 세로 성분으로 분리 가능하다면, 이를 $N \times 1$ 가로 패스와 $1 \times N$ 세로 패스의 두 단계로 나누어 처리할 수 있습니다.

수식으로 표현하면, 2차원 필터 커널 $K$가 두 1차원 벡터의 외적 $K = v \cdot h^T$로 표현될 때 다음과 같이 합성곱의 결합법칙이 성립합니다.

$$ I_{blur} = I * K = I * (v \cdot h^T) = (I * h^T) * v $$

이 경우 픽셀당 연산량은 다음과 같이 획기적으로 줄어듭니다.
*   **기본 2D Convolution**: $O(N^2)$ (5x5 블러의 경우 픽셀당 **25회** 연산)
*   **Separable Convolution**: $O(N + N) = O(2N)$ (5x5 블러의 경우 픽셀당 **10회** 연산)

학습자는 이 효율적인 방식을 구현하기 위해 첫 번째 단계인 **가로 방향 1D 합성곱(Horizontal Pass)**을 먼저 적용하였습니다.

### ② Box Blur 5 알고리즘
Box Blur는 필터 영역 내의 모든 픽셀에 동일한 가중치를 부여하여 평균을 내는 가장 단순하고 직관적인 블러 방식입니다. 5x5 Box Blur의 가로 패스에서 각 픽셀은 자신을 중심으로 좌우 2개씩, 총 5개 픽셀 값의 평균을 취합니다.

이때 1차원 가로 커널의 가중치는 모두 동일하게 $\frac{1}{5}$ (0.2)이 됩니다.

$$ P_{out}(x, y) = \frac{1}{5} \sum_{i=-2}^{2} P_{in}(x+i, y) $$

학습자는 가로 패스를 적용한 중간 결과 버퍼를 생성하고, 경계선 처리(Boundary Condition) 등을 고려하며 메모리에 안전하게 쓰는 과정을 이해하고 구현했을 것입니다.

### ③ 다중 패스 필터링 (Multi-pass Filtering)
커밋된 코드에서 `image.BoxBlur5()`를 100번 반복 실행하는 루프가 확인됩니다. 
```cpp
for(int i = 0; i < 100; i++)
    image.BoxBlur5();
```
블러 필터를 여러 번 반복해서 적용하면 블러의 반경(Radius)이 넓어지는 효과를 얻을 수 있으며, 통계학의 **중앙한계정리(Central Limit Theorem)**에 의해 단순한 Box Blur라 할지라도 반복 적용할수록 종형 곡선 형태인 Gaussian Blur에 가까운 부드러운 결과를 얻을 수 있음을 실험적으로 이해했을 것입니다.

---

## 2. 핵심 알고리즘 설명 (의사코드)

학습자가 구현한 `BoxBlur5` 내부의 가로 패스 알고리즘을 추상화된 의사코드로 표현하면 다음과 같습니다. 원래의 이미지 데이터를 직접 덮어쓰면(In-place) 이후 연산에 왜곡이 생기므로, 반드시 입력 이미지와 출력 이미지를 분리하여 처리해야 합니다.

```text
function ApplyHorizontalBoxBlur5(inputImage, outputImage):
    width = inputImage.width
    height = inputImage.height

    for y from 0 to height - 1:
        for x from 0 to width - 1:
            colorSum = Vector3(0, 0, 0)
            
            // 가로 방향으로 인접한 5개의 픽셀 샘플링
            for offset from -2 to 2:
                sampleX = Clamp(x + offset, 0, width - 1) // 경계 영역 처리
                colorSum += inputImage.GetPixel(sampleX, y)
            
            // 평균값을 출력 버퍼에 저장
            outputImage.SetPixel(x, y, colorSum / 5.0)
```

---

## 3. WebGPU 인터랙티브 데모로 시각화하기

만약 이 C++ CPU 기반의 알고리즘을 최신 웹 그래픽스 표준인 **WebGPU의 Compute Shader**로 옮겨 브라우저에서 실시간 인터랙티브 데모로 시각화한다면 다음과 같이 멋지게 구성할 수 있습니다.

### 💡 데모 구성 및 시각화 아이디어

1.  **실시간 파이프라인 시각화 (Split Screen)**
    *   화면을 반으로 나누어 한쪽에는 원본 이미지를, 다른 쪽에는 실시간으로 블러가 적용되는 이미지를 렌더링합니다.
    *   **Horizontal Pass Only** 모드를 제공하여 가로 방향으로만 픽셀이 길게 늘어지는(Stretched) 중간 단계의 이미지를 직접 눈으로 확인할 수 있게 합니다.

2.  **Compute Shader의 공유 메모리(Workgroup Memory) 활용**
    *   WebGPU의 `@compute` 셰이더 내에서 가로 패스를 수행할 때, 각 스레드 그룹이 텍스처를 개별적으로 샘플링하는 대신 `workgroup` 공유 메모리에 가로 1라인의 픽셀 데이터를 미리 로드(`LDS, Local Data Store` 활용)하도록 구현합니다.
    *   이를 통해 GPU 메모리 대역폭을 극적으로 절약하는 고급 최적화 기법을 데모 코드와 성능 그래프(FPS / GPU Time ms)로 시각화합니다.

3.  **인터랙티브 파라미터 조절**
    *   **Iteration Slider (1 ~ 100)**: CPU에서는 100번 반복하면 병목이 생기지만, WebGPU Compute Shader에서는 수십 번의 패스도 실시간(60fps)으로 돌아가는 모습을 슬라이더를 통해 직접 체험합니다.
    *   **Kernel Type Selector**: BoxBlur5와 GaussianBlur5를 실시간으로 스위칭하며, 박스 블러를 여러 번 반복했을 때 가우시안 블러와 시각적으로 얼마나 유사해지는지 비교 분석할 수 있도록 합니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/코드-리뷰-separable-convolution을-활용한-box-blu/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
