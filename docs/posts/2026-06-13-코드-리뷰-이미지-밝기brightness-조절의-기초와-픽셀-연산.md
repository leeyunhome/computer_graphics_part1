# [코드 리뷰] 이미지 밝기(Brightness) 조절의 기초와 픽셀 연산

DirectX 11과 C++을 활용한 그래픽스 프레임워크에서 이미지 처리의 가장 기초적이면서도 중요한 단계인 **화소 점 처리(Point Processing)**를 성공적으로 구현하셨습니다. 

이번 커밋은 블룸(Bloom) 효과의 프리필터(Prefilter) 단계나 이미지의 전반적인 노출(Exposure)을 조절하기 위한 첫걸음입니다. 작성하신 코드를 바탕으로 직접 구현하며 이해하신 핵심 개념들을 정리하고, 한 단계 더 나아갈 수 있는 그래픽스 이론을 제시해 드립니다.

---

## 1. 학습자가 직접 구현하며 이해한 핵심 개념

### 1) 1차원 배열을 통한 2D 이미지 순회 (Image Flattening)
컴퓨터 메모리 상에서 2차원 이미지는 행(Row) 단위로 연속되게 배치된 1차원 배열로 표현됩니다. 학습자는 가로($W$)와 세로($H$) 크기를 곱한 총 픽셀 수만큼 반복문을 실행하여 이미지 전체를 효율적으로 순회하는 방법을 올바르게 적용했습니다.

$$Total\_Pixels = Width \times Height$$

### 2) 화소 점 처리(Point Processing)와 스케일링
특정 픽셀의 출력값이 오직 해당 위치의 입력 픽셀값에 의해서만 결정되는 연산을 **점 처리(Point Processing)**라고 합니다. 학습자는 각 픽셀의 채널 값에 일정한 상수(스케일 팩터)를 곱하여 밝기를 조절하는 선형 매핑을 구현했습니다.

수식으로 표현하면 다음과 같습니다. 여기서 $I_{in}$은 입력 픽셀 값, $s$는 스케일 팩터($1.2$), $I_{out}$은 보정된 출력 픽셀 값입니다.

$$I_{out}(x, y) = I_{in}(x, y) \times s$$

---

## 2. 핵심 알고리즘 구조 (추상화)

학습자가 구현한 이미지 밝기 조절 알고리즘은 다음과 같은 흐름으로 추상화할 수 있습니다. 

```text
function brightenImage(image, scaleFactor):
    for each pixel in image.pixels:
        // 특정 채널(또는 단일 채널)의 밝기를 선형적으로 증가시킵니다.
        pixel.primary_channel = pixel.primary_channel * scaleFactor
        
        // (권장 사항) 오버플로우 방지를 위한 클램핑 처리
        pixel.primary_channel = clamp(pixel.primary_channel, 0.0, 1.0)
```

### 💡 전문가의 팁: 색상 왜곡 방지 및 클램핑(Clamping)
현재 코드에서는 `v[0]`(일반적으로 RGB 중 Red 채널 혹은 단일 채널의 값)만 $1.2$를 곱하고 있습니다. 
1. **RGB 컬러 이미지일 경우**: Red 채널만 밝아지므로 이미지 전체에 붉은 톤이 도는 색상 왜곡(Color Tint)이 발생할 수 있습니다. 전체적인 밝기를 올바르게 올리기 위해서는 RGB 모든 채널(`v[0]`, `v[1]`, `v[2]`)에 동일한 스케일 팩터를 곱해주어야 합니다.
2. **LDR(Low Dynamic Range) 환경**: 결과값이 최대 밝기 값($1.0$ 또는 $255$)을 초과할 수 있으므로, 상한선을 제한하는 `clamp` 연산이 안전장치로서 필요합니다.

---

## 3. WebGPU 인터랙티브 데모: Compute Shader로 시각화하기

이 픽셀 연산 로직을 웹 브라우저 상에서 GPU의 강력한 병렬 연산 성능을 활용하는 **WebGPU Compute Shader**로 구현한다면 어떻게 시각화할 수 있을까요?

### 시각화 및 동작 방식 설명
* **사용자 인터페이스 (UI)**: 웹 페이지에 밝기 조절 슬라이더(스케일 값: $0.0 \sim 2.0$)를 배치합니다.
* **병렬 처리 (Parallel Compute)**: CPU에서 루프를 돌며 순차적으로 처리하는 대신, WebGPU의 Compute Shader가 이미지의 모든 픽셀을 동시에 병렬로 연산합니다.
* **실시간 렌더링**: 슬라이더를 움직일 때마다 uniform 버퍼를 통해 GPU로 새로운 스케일 값이 전달되며, 연산 결과가 즉각적으로 브라우저 화면의 `<canvas>`에 텍스처로 그려집니다.

### 핵심 WGSL (WebGPU Shading Language) 구조
Compute Shader에서는 다음과 같이 각 픽셀의 글로벌 ID를 기반으로 텍스처를 읽고, 밝기를 곱한 뒤 다시 쓰게 됩니다.

```rust
@group(0) @binding(0) var inputTex: texture_2d<f32>;
@group(0) @binding(1) var outputTex: texture_storage_2d<rgba8unorm, write>;
@group(0) @binding(2) var<uniform> scaleFactor: f32;

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let coords = vec2<i32>(global_id.xy);
    
    // 1. 입력 텍스처로부터 원래 픽셀 색상(RGB) 읽기
    let originalColor = textureLoad(inputTex, coords, 0);
    
    // 2. 모든 RGB 채널에 스케일 팩터 곱하기 (밝기 증가) 및 클램핑
    let brightenedRGB = clamp(originalColor.rgb * scaleFactor, vec3<f32>(0.0), vec3<f32>(1.0));
    
    // 3. 결과물 저장 (알파 채널은 유지)
    textureStore(outputTex, coords, vec4<f32>(brightenedRGB, originalColor.a));
}
```

이러한 GPU 병렬 연산 방식은 이미지 크기가 $4K, 8K$로 커지더라도 프레임 드랍 없이 실시간으로 밝기를 제어할 수 있게 해줍니다. 이번 실습을 통해 다진 픽셀 제어 기초는 추후 작성하실 Gaussian Blur나 Bloom Filter와 같은 고성능 이미지 필터링 구현의 단단한 밑거름이 될 것입니다!

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/코드-리뷰-이미지-밝기brightness-조절의-기초와-픽셀-연산/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
