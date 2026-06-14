# [리뷰] 블룸(Bloom) 효과의 첫 단계: 휘도(Luminance) 기반 임계값 추출 구현

학습자가 작성한 커밋은 이미지 프로세싱 및 실시간 그래픽스에서 널리 쓰이는 **블룸(Bloom) 효과**의 파이프라인 중 가장 첫 번째 단계인 **밝은 영역 추출(Bright Pass/Thresholding)**을 성공적으로 구현하고 있습니다.

이 단계는 화면에서 빛이 번지는 듯한 시각적 효과를 만들기 위해, 전체 이미지에서 "빛을 방출할 만큼 충분히 밝은" 영역만 남기고 나머지는 검은색(무효화)으로 걸러내는 핵심 전처리 과정입니다.

---

## 1. 핵심 수학적 개념 및 알고리즘

### 인간의 시각 특성을 반영한 상대 휘도 (Relative Luminance)
단순히 RGB 채널의 산술 평균 $\frac{R+G+B}{3}$을 사용하여 밝기를 구하면 인간의 실제 눈이 느끼는 밝기와 괴리가 생깁니다. 인간의 안구는 망막의 원추세포 분포 특성상 **초록색(Green)에 가장 민감하고, 파란색(Blue)에 가장 둔감**합니다. 

이러한 인간의 시각 인지 특성을 표준화한 것이 **ITU-R BT.709** 규격이며, 디지털 표준 RGB(sRGB) 색 공간에서 휘도 $Y$를 계산하는 공식은 다음과 같습니다.

$$Y = 0.2126 \cdot R + 0.7152 \cdot G + 0.0722 \cdot B$$

학습자는 이 수식을 각 픽셀의 RGB 채널에 정확히 적용하여 물리적/인지적으로 올바른 밝기 값을 도출해 냈습니다.

### 임계값 처리 (Thresholding)
추출된 상대 휘도 $Y$가 사전에 정의된 임계값(Threshold, 본 코드에서는 `0.3`)보다 작다면, 해당 픽셀은 빛을 발하지 않는 어두운 영역으로 판단하여 완전히 검은색으로 소거합니다.

$$Color_{out} = \begin{cases} Color_{in} & \text{if } Y \ge Threshold \\ (0, 0, 0) & \text{if } Y < Threshold \end{cases}$$

---

## 2. 알고리즘의 의사코드 (Pseudo-code)

학습자가 구현한 `Image::Bloom` 함수의 핵심 흐름은 다음과 같이 추상화할 수 있습니다. 

```python
function ExtractBrightPass(image, threshold):
    for each pixel in image:
        # 1. 픽셀의 RGB 색상 참조
        color = pixel.rgb
        
        # 2. ITU-R BT.709 공식을 이용한 휘도 계산
        luminance = 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b
        
        # 3. 임계값과 비교하여 어두운 영역 제거 (제외된 영역은 검은색 처리)
        if luminance < threshold:
            pixel.rgb = (0.0, 0.0, 0.0)
```

이 단계가 완료되면 어두운 배경(예: 콜로세움의 그늘진 벽면 등)은 모두 검은색으로 변하고, 하늘이나 강한 조명과 같이 밝은 영역만 원래 색상 그대로 남게 됩니다. 이후 이 결과물에 가우시안 블러(Gaussian Blur)를 적용하고 원본 이미지와 합성(Additive Blend)하면 비로소 블룸 효과가 완성됩니다.

---

## 3. 전체 그래픽스 파이프라인 관점에서의 분석

* **성능 및 병렬화**: 학습자는 CPU 환경에서 이를 처리하기 위해 `#pragma omp parallel for`를 사용하는 OpenMP 병렬화를 염두에 두고 설계했습니다. 픽셀 간의 연산 의존성이 없는 대표적인 **상호 독립적 연산(Embarrassingly Parallel)**이므로, CPU 멀티스레딩 및 GPU 파이프라인에 매우 적합합니다.
* **인플레이스(In-place) 연산의 한계**: 현재 구현은 원본 `pixels` 배열을 직접 수정하는 구조입니다. 실제 실시간 렌더링 엔진(DirectX 11)에서는 원본 씬을 보존해야 하므로, 별도의 텍스처(Render Target)에 이 밝은 영역만 따로 그려내는 **포스트 프로세싱 패스(Post-processing Pass)** 형태로 구현하는 것이 일반적입니다.

---

## 4. WebGPU 인터랙티브 데모로 확장하기

이 알고리즘을 최신 웹 그래픽스 표준인 **WebGPU**의 **Compute Shader**로 시각화하면, 웹 브라우저에서 GPU 하드웨어 가속을 통해 수백만 픽셀의 이미지를 실시간(60fps 이상)으로 처리하는 인터랙티브 데모를 구성할 수 있습니다.

### WebGPU Compute Shader (WGSL) 구현 컨셉
웹 상에서 캔버스에 이미지를 업로드하고, 슬라이더를 통해 임계값(Threshold)을 실시간으로 조절하는 데모를 위한 WGSL 셰이더 핵심 부분입니다.

```wgsl
@group(0) @binding(0) var inputTex: texture_2d<f32>;
@group(0) @binding(1) var outputTex: texture_storage_2d<rgba8unorm, write>;

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let dims = textureDimensions(inputTex);
    if (id.x >= dims.x || id.y >= dims.y) { return; }

    let coords = vec2<i32>(id.xy);
    let color = textureLoad(inputTex, coords, 0);

    // ITU-R BT.709 휘도 계산
    let luminance = dot(color.rgb, vec3<f32>(0.2126, 0.7152, 0.0722));
    
    // 유저가 슬라이더로 조절하는 임계값 매개변수 (Uniform Buffer에서 바인딩했다고 가정)
    let threshold = params.threshold; 

    var finalColor = vec3<f32>(0.0);
    if (luminance >= threshold) {
        finalColor = color.rgb;
    }

    textureStore(outputTex, coords, vec4<f32>(finalColor, 1.0));
}
```

### 인터랙티브 UI 구성 및 기대 시각 효과
1. **입력 이미지 로드**: 로컬 파일이나 제공된 콜로세움 이미지를 WebGPU 텍스처로 로드합니다.
2. **실시간 임계값 제어**: 사용자가 웹 UI의 슬라이더를 조작하여 `threshold` 값을 `0.0`에서 `1.0`까지 변화시킵니다.
3. **인터랙티브 반응**: 슬라이더를 움직일 때마다 Compute Shader가 매 프레임 실행되어, 실시간으로 어두운 부분이 칼같이 지워지며 밝은 영역(태양광이 닿는 석조물, 하늘 등)만 선명하게 추출되는 시각적 변화를 브라우저에서 지연 없이 관찰할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/리뷰-블룸bloom-효과의-첫-단계-휘도luminance-기반-임계값-추/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
