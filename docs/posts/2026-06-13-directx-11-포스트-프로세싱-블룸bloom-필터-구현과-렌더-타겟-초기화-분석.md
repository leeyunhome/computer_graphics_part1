# DirectX 11 포스트 프로세싱: 블룸(Bloom) 필터 구현과 렌더 타겟 초기화 분석

학습자의 커밋은 DirectX 11 기반 그래픽스 파이프라인에서 입력 이미지 소스를 변경하고, 화면을 비우는 배경색(Clear Color)을 기존 검은색에서 파란색(Blue)으로 변경한 작업을 담고 있습니다. 이 단순해 보이는 코드 변경 이면에는 그래픽스 포스트 프로세싱(Post-processing)과 파이프라인 상태 관리에 대한 중요한 개념들이 녹아있습니다.

이 피드백에서는 학습자가 이 단계를 통해 직접 구현하고 이해한 핵심 그래픽스 개념을 분석합니다.

---

## 1. 학습자가 이해한 핵심 그래픽스 개념

### 1) 이미지 로딩 및 텍스처 자원(Texture Resource) 관리
학습자는 `.HEIC` 고효율 이미지 포맷을 범용적인 `.jpg` 포맷(`image_4.jpg`)으로 변환하여 프로젝트에 적용했습니다. 
* **CPU-GPU 데이터 전송**: CPU에서 읽어들인 이미지 바이트 데이터는 DirectX 11의 `ID3D11Texture2D` 자원으로 생성되어 GPU 메모리(VRAM)로 업로드됩니다.
* **셰이더 리소스 뷰(SRV, Shader Resource View)**: GPU 파이프라인(특히 픽셀 셰이더)에서 이 이미지를 샘플링할 수 있도록 뷰를 바인딩하는 과정을 이해하고 적용했습니다.

### 2) 렌더 타겟 뷰(RenderTargetView) 초기화와 화면 클리어
`Render()` 함수 내에서 `clearColor`가 변경되었습니다.
* **기존**: `float clearColor[4] = { 0.0f, 0.0f, 0.0f, 1.0f };` (검은색 완전 불투명)
* **변경**: `float clearColor[4] = { 0.0f, 0.0f, 1.0f, 1.0f };` (파란색 완전 불투명)

이 변경은 `ID3D11DeviceContext::ClearRenderTargetView`를 통해 프레임 버퍼를 특정 단색으로 채우는 작업입니다. 디버깅 과정에서 백버퍼가 올바르게 초기화되고 있는지, 혹은 블룸 효과의 투명도(Alpha)와 혼합(Blending)이 파란색 배경 위에서 어떻게 상호작용하는지 확인하기 위한 훌륭한 시도입니다.

### 3) 블룸(Bloom) 효과의 수학적 원리
블룸 효과는 화면에서 기준치 이상의 밝은 영역을 추출하여 흐리게(Blur) 만든 뒤, 원본 이미지와 더하는(Additive Blending) 기법입니다. 학습자는 이 과정에서 다음 두 가지 핵심 수학적 처리를 이해하고 구현하고 있습니다.

#### 휘도(Luminance) 공식
이미지의 각 픽셀에서 밝기 정보를 추출하기 위해 인간의 눈이 초록색에 가장 민감하고 파란색에 가장 둔감하다는 생리학적 특성을 반영한 공식입니다.

$$ L = 0.2126R + 0.7152G + 0.0722B $$

#### 임계값 필터링 (Thresholding)
특정 밝기 임계값($$T$$)을 넘는 픽셀만 통과시켜 블룸이 일어날 영역을 결정합니다.

$$ C_{bright} = \begin{cases} C & \text{if } L > T \\ 0 & \text{otherwise} \end{cases} $$

#### 가산 혼합 (Additive Blending)
흐려진 밝은 이미지($$C_{blur}$$)를 원본 이미지($$C_{original}$$)에 더하여 최종 픽셀 색상($$C_{final}$$)을 결정합니다.

$$ C_{final} = C_{original} + k \cdot C_{blur} $$

*(여기서 $$k$$는 블룸의 강도를 조절하는 계수입니다.)*

---

## 2. 블룸 포스트 프로세싱 파이프라인 알고리즘

학습자가 다루고 있는 전체적인 블룸 알고리즘의 흐름을 추상화된 의사코드(Pseudocode)로 표현하면 다음과 같습니다.

```text
function RenderBloomEffect():
    // 1. 원본 씬을 렌더 타겟(RTT)에 렌더링
    SetRenderTarget(OriginalSceneTexture)
    ClearRenderTarget(clearColor) // { 0.0, 0.0, 1.0, 1.0 } 파란색으로 클리어
    DrawScene(image_4)

    // 2. 밝은 영역 추출 (Bright Pass)
    SetRenderTarget(BrightPassTexture)
    ClearRenderTarget(Black)
    for each pixel in OriginalSceneTexture:
        luminance = CalculateLuminance(pixel.rgb)
        if luminance > Threshold:
            BrightPassTexture.pixel = pixel.rgb
        else:
            BrightPassTexture.pixel = Black

    // 3. 가우시안 블러 수행 (Two-Pass Gaussian Blur로 최적화)
    // Horizontal Blur
    SetRenderTarget(BlurIntermediateTexture)
    ApplyHorizontalGaussianBlur(BrightPassTexture)
    
    // Vertical Blur
    SetRenderTarget(BlurFinalTexture)
    ApplyVerticalGaussianBlur(BlurIntermediateTexture)

    // 4. 최종 합성 (Composite Pass)
    SetRenderTarget(BackBuffer)
    for each pixel:
        original = OriginalSceneTexture.pixel
        blurred = BlurFinalTexture.pixel
        BackBuffer.pixel = original + (blurred * BloomIntensity)
```

---

## 3. 코드 개선 및 디버깅 가이드

1. **주석과 코드의 불일치**:
   `image.ReadFromFile("image_4.jpg");` 로 이미지를 변경했으나, 주석은 여전히 `// 컴퓨터 속도가 느리다면 "image_1_360.jpg" 사용`으로 유지되어 있습니다. 협업 및 유지보수를 위해 주석도 `image_4_360.jpg` 등으로 일치시키거나 범용적인 설명으로 수정하는 것이 좋습니다.
2. **배경색(Clear Color) 변경의 영향**:
   배경을 완전한 파란색(`0.0f, 0.0f, 1.0f`)으로 설정하면, 블룸 필터의 가산 혼합(Additive Blending) 단계에서 파란색 배경과 밝은 영역의 경계선이 어떻게 합성되는지 관찰할 수 있습니다. 만약 배경에 불필요한 번짐이 발생한다면 임계값($$T$$) 계산 시 배경의 파란색 채널이 필터링에 걸러지는지 검토해야 합니다.

---

## 4. WebGPU 인터랙티브 데모

만약 이 DirectX 11 블룸 프로젝트를 최신 웹 그래픽스 API인 **WebGPU**로 전환하여 브라우저에서 실행한다면 다음과 같은 방식으로 시각화 데모를 구성할 수 있습니다.

```
+-------------------------------------------------------------+
|                      [ WebGPU Bloom Demo ]                  |
+-------------------------------------------------------------+
|  [ Original Image: image_4.jpg ]                            |
|  +-------------------------+   +-------------------------+  |
|  |  (Blue Clear Canvas)    |   |  (Bright Pass Extract)  |  |
|  |   * Original Picture *  |   |   * Highlights Only *   |  |
|  +-------------------------+   +-------------------------+  |
|               |                             |               |
|               v                             v               |
|       [ Compute Shader ] ---------> [ Horizontal Blur ]     |
|                                             |               |
|                                             v               |
|                                     [ Vertical Blur ]       |
|                                             |               |
|  [ Final Composite Output ]                 v               |
|  +-------------------------------------------------------+  |
|  |                 * Final Bloomed Picture *             |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  < UI Controls >                                            |
|  Threshold: [=======|-------] 0.6                           |
|  Bloom Intensity: [====|----------] 1.5                     |
+-------------------------------------------------------------+
```

### WebGPU Compute Shader의 이점
* **고속 가우시안 블러**: WebGPU의 **컴퓨트 셰이더(Compute Shader)**를 활용하면, 픽셀 셰이더 방식보다 훨씬 빠른 속도로 이미지 블러를 수행할 수 있습니다.
* **공유 메모리(Workgroup Shared Memory)** 활용: 가우시안 필터링 시 주변 픽셀을 반복해서 샘플링할 필요 없이, 워크그룹 공유 메모리에 텍셀 블록을 한 번만 로드하고 재사용함으로써 대역폭을 극적으로 절약할 수 있습니다.
* **실시간 인터랙티브 조절**: 웹 페이지의 슬라이더(UI)를 통해 임계값(Threshold)과 블러 반경(Sigma)을 조절하면, WebGPU가 실시간으로 유니폼 버퍼(Uniform Buffer)를 업데이트하여 변환된 결과를 즉각 브라우저 화면에 렌더링합니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/directx-11-포스트-프로세싱-블룸bloom-필터-구현과-렌더-타겟/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
