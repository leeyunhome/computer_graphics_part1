# [코드 리뷰] 실시간 템포럴 라이트 디케이(Temporal Light Decay)와 이미지 프로세싱 파이프라인 구현

학습자님의 커밋을 환영합니다! 이번 구현은 단순히 정적인 블룸(Bloom) 필터를 적용하는 것을 넘어, **시간의 흐름에 따른 동적 빛 감쇠(Temporal Decay)와 증폭(Accumulation) 효과를 CPU 루프에서 직접 제어**하려고 시도한 점이 매우 돋보입니다. 

특히 화면을 반으로 나누어 가로축 좌표에 따라 서로 다른 스케일링 인자를 적용함으로써, 감쇠와 증폭의 시각적 차이를 직관적으로 비교할 수 있도록 설계한 실험 정신을 높이 평가합니다.

---

### 1. 학습자가 직접 구현하며 이해한 핵심 개념

#### 시간적 빛 감쇠 및 누적 (Temporal Decay & Accumulation)
학습자는 매 프레임 호출되는 `Update` 루프 내에서 이전 프레임의 픽셀 값에 지속적으로 특정 계수(Factor)를 곱해나가는 방식을 취했습니다. 이는 시간에 따른 빛의 소멸 및 노출 누적 효과를 수학적으로 시뮬레이션한 것입니다.

시간 $t$에서의 픽셀 밝기 $I(t)$는 이전 프레임의 밝기 $I(t-1)$과 스케일링 계수 $s$의 곱으로 정의되며, 모니터가 표현할 수 있는 한계치로 제한(Clamping)됩니다.

$$ I(t) = \max\left(0.0, \min\left(1.0, I(t-1) \times s\right)\right) $$

* **화면 왼쪽 영역 ($s = 0.99$):** 매 프레임 빛이 $1\%$씩 감소합니다. 프레임이 거듭될수록 $0.99^t$의 지수 감쇠 곡선을 그리며 서서히 어두워집니다.
* **화면 오른쪽 영역 ($s = 1.01$):** 매 프레임 빛이 $1\%$씩 증가합니다. $1.01^t$의 지수 성장 곡선을 그리며, 결국 $1.0$으로 수렴하여 화면이 하얗게 타들어 가는 화이트아웃(Overexposure) 현상이 발생합니다.

---

### 2. 핵심 알고리즘 추상화 (의사코드)

학습자가 구현한 `Example.h` 내의 업데이트 루프 로직을 추상화하여 표현하면 다음과 같습니다. 강의의 세부 API에 의존하지 않고 이미지 버퍼를 직접 수정하는 픽셀 셰이더의 전처리 단계 구조를 띱니다.

```cpp
// 매 프레임 호출되는 업데이트 루프
void UpdateFrame(Image& image, float decayFactor, float boostFactor)
{
    const int width = image.width;
    const int height = image.height;
    const int halfWidth = width / 2;

    for (int y = 0; y < height; ++y)
    {
        for (int x = 0; x < width; ++x)
        {
            const int pixelIndex = x + (y * width);
            Pixel& pixel = image.pixels[pixelIndex];

            if (x < halfWidth)
            {
                // 왼쪽: 서서히 어두워지는 디케이 효과
                pixel.r = Clamp(pixel.r * decayFactor, 0.0f, 1.0f);
                pixel.g = Clamp(pixel.g * decayFactor, 0.0f, 1.0f);
                pixel.b = Clamp(pixel.b * decayFactor, 0.0f, 1.0f);
            }
            else
            {
                // 오른쪽: 서서히 밝아지는 익스포저 효과
                pixel.r = Clamp(pixel.r * boostFactor, 0.0f, 1.0f);
                pixel.g = Clamp(pixel.g * boostFactor, 0.0f, 1.0f);
                pixel.b = Clamp(pixel.b * boostFactor, 0.0f, 1.0f);
            }
        }
    }

    // 이어서 텍스처를 블러 처리하여 블룸 효과의 소스로 활용함
    // image.ApplyBlur(kernelSize);
}
```

---

### 3. 그래픽스 전문가로서의 기술 피드백

1. **CPU 연산 병목 (CPU Bottleneck):**
   현재 가로/세로 픽셀을 CPU의 이중 루프로 순회하며 연산하고 있습니다. 이 방식은 알고리즘 검증 단계에서는 유용하나, FHD($1920 \times 1080$) 해상도만 되어도 매 프레임 약 200만 번의 연산이 수행되므로 CPU 병목의 주원인이 됩니다. 이 연산은 픽셀 간 독립적이므로, DirectX 11의 **픽셀 셰이더(Pixel Shader)** 혹은 **컴퓨트 셰이더(Compute Shader)**로 이전하여 GPU의 병렬 프로세싱을 활용하는 것이 좋습니다.

2. **정밀도 손실 및 누적 오차:**
   매 프레임 소수점 연산을 반복하고 고정 소수점 형태(`rgba8unorm` 등)로 저장 및 클램핑하면 소수점 아래 정밀도가 빠르게 유실됩니다. 실시간 그래픽스 파이프라인에서는 원본 데이터를 HDR(High Dynamic Range, 예: `R16G16B16A16_FLOAT`) 버퍼에 유지하고, 감쇠 연산을 처리한 뒤, 최종 렌더링 직전에 톤맵핑(Tone Mapping)과 클램핑을 적용하는 것이 색상의 디테일을 유지하는 정석입니다.

---

### 4. WebGPU 인터랙티브 데모

이 개념을 웹 브라우저에서 플러그인 없이 초고속으로 시각화하기 위해 **WebGPU Compute Shader**를 활용하는 데모를 제안합니다. GPU의 강력한 병렬 능력을 체감할 수 있는 훌륭한 쇼케이스가 될 것입니다.

#### 구현 설계 및 시각화 모습
* **실시간 파라미터 제어:** 사용자는 웹 페이지의 UI 슬라이더를 통해 감쇠 계수($0.90 \sim 0.99$)와 증폭 계수($1.00 \sim 1.10$)를 실시간으로 조정합니다.
* **병렬 컴파일 및 실행:** 브라우저는 GPU 메모리에 텍스처를 업로드한 뒤, 컴퓨트 셰이더를 통해 화면 전체를 수만 개의 스레드로 나누어 동시에 연산합니다. CPU 루프 대비 수백 배 빠른 속도로 동작하여 프레임 드랍이 전혀 없는 부드러운 전이를 보여줍니다.

#### WebGPU 컴퓨트 셰이더 (WGSL) 예시 코드
```wgsl
struct PushConstants {
    decayFactor : f32,
    boostFactor : f32,
    screenWidth : u32,
}

@group(0) @binding(0) var<uniform> params : PushConstants;
@group(0) @binding(1) var inputTex : texture_2d<f32>;
@group(0) @binding(2) var outputTex : texture_storage_2d<rgba8unorm, write>;

@compute @workgroup_size(16, 16)
fn cs_main(@builtin(global_invocation_id) id : vec3<u32>) {
    let coords = id.xy;
    let texSize = textureDimensions(inputTex);
    
    if (coords.x >= texSize.x || coords.y >= texSize.y) {
        return;
    }

    var color = textureLoad(inputTex, coords, 0).rgb;

    // 화면의 가로 중앙을 기준으로 연산 분기 (학습자의 C++ 로직을 GPU로 이식)
    if (coords.x < params.screenWidth / 2u) {
        color = clamp(color * params.decayFactor, vec3<f32>(0.0), vec3<f32>(1.0));
    } else {
        color = clamp(color * params.boostFactor, vec3<f32>(0.0), vec3<f32>(1.0));
    }

    textureStore(outputTex, coords, vec4<f32>(color, 1.0));
}
```

이 데모를 구동하면, 사용자는 마우스 클릭으로 빛을 화면에 '그린' 후, 슬라이더 조절에 따라 왼쪽 화면에서는 그 빛이 유령처럼 서서히 잔상을 남기며 사라지고(Decay), 오른쪽 화면에서는 핵분열하듯 하얗게 폭발해 나가는 역동적인 비주얼을 실시간으로 관찰할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/코드-리뷰-실시간-템포럴-라이트-디케이temporal-light-deca/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
