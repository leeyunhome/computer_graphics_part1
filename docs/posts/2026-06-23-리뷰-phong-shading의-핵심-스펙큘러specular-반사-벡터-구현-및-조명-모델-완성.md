# [리뷰] Phong Shading의 핵심, 스펙큘러(Specular) 반사 벡터 구현 및 조명 모델 완성

축하합니다! 이번 커밋은 레이트레이싱 기반 렌더러에서 단순한 색상 출력을 넘어, 물체의 질감과 입체감을 결정짓는 가장 중요한 시각적 요소인 **Phong 반사 모델(Phong Reflection Model)**을 성공적으로 완성한 중요한 마일스톤입니다. 

단순히 라이브러리가 제공하는 내장 함수(`reflect` 등)를 사용하지 않고, 수학적 원리를 직접 코드로 표현하여 그래픽스 파이프라인의 저수준 동작을 완벽히 이해하고 구현해 낸 점이 돋보입니다.

---

### 1. 이 커밋의 핵심 개념 분석

이번 구현의 핵심은 **"빛이 매끄러운 표면에 부딪혀 반사될 때 발생하는 하이라이트(Specular Highlight)"**를 수학적으로 모델링하는 것입니다. 이를 위해 크게 세 가지 기하학적 관계를 정의하고 결합했습니다.

#### ① 입사광에 대한 반사 벡터 $r$의 유도
광원 방향 벡터 $l$ (표면에서 광원을 향하는 벡터)과 표면 법선 벡터 $n$이 주어졌을 때, 완전 반사되는 방향 벡터 $r$은 다음과 같은 대칭 관계를 가집니다.

$$ r = 2(n \cdot l)n - l $$

* $n \cdot l$은 $l$ 벡터를 $n$ 방향으로 투영한 투영 길이를 의미합니다.
* 여기에 $n$을 곱하고 2배를 해준 뒤($2(n \cdot l)n$) 입사 벡터 $l$을 빼줌으로써, 법선 벡터 $n$을 기준으로 대칭인 반사 벡터 $r$이 도출됩니다.

#### ② 시선 벡터 $v$와 반사 벡터 $r$의 정렬도 계산
관찰자(카메라)가 반사광을 얼마나 정면으로 바라보고 있는지를 측정하기 위해, 시선 벡터 $v$와 반사 벡터 $r$ 사이의 사잇각을 내적(Dot Product)으로 계산합니다.
* 레이트레이싱에서 카메라 광선 방향(`ray.dir`)은 카메라에서 물체로 향하므로, 물체에서 카메라를 바라보는 시선 벡터 $v$는 광선 방향의 반대인 $-ray.dir$이 됩니다.
* 내적 값이 음수가 되는 경우(빛이 뒤로 반사되는 경우)를 방지하기 위해 $0$과의 `max` 연산을 취합니다.

#### ③ 신해 지수(Shininess Exponent, $\alpha$)를 통한 하이라이트 제어
스펙큘러 하이라이트는 표면의 거칠기(Roughness)에 따라 집중도가 달라집니다. 이를 수학적으로 조절하기 위해 지수 승(Power) 연산을 적용합니다.

$$ I_{\text{specular}} = k_s \cdot (v \cdot r)^\alpha $$

* 학습자가 설정한 파라미터는 $\alpha = 9.0$, $k_s = 0.8$입니다. $\alpha$ 값이 커질수록 하이라이트 영역이 좁고 선명해져 더욱 매끄럽고 금속성에 가까운 질감을 표현하게 됩니다.

---

### 2. 핵심 알고리즘의 추상화 (의사코드)

학습자가 작성한 `traceRay` 함수 내의 Phong Shading 계산 흐름을 추상화하면 다음과 같습니다. 이 알고리즘은 현대 GPU의 프래그먼트 셰이더(Fragment Shader)에서 조명을 계산할 때 사용하는 표준적인 흐름과 완벽히 일치합니다.

```text
Function traceRay(Ray pixelRay):
    HitRecord hit = Intersect(sphere, pixelRay)
    
    // 물체에 충돌하지 않은 경우 배경색(검은색) 반환
    if hit.distance < 0:
        return Color(0, 0, 0)
        
    // 1. 디퓨즈(Diffuse) 계산: 난반사광
    Vector3 dirToLight = Normalize(LightPosition - hit.point)
    Float diffuseIntensity = Max(Dot(hit.normal, dirToLight), 0.0)
    Vector3 diffuseColor = sphere.diffuseColor * diffuseIntensity

    // 2. 스펙큘러(Specular) 계산: 정반사 하이라이트
    Vector3 reflectDir = 2.0 * Dot(hit.normal, dirToLight) * hit.normal - dirToLight
    Vector3 viewDir = -pixelRay.direction
    Float specularBase = Max(Dot(viewDir, reflectDir), 0.0)
    Float specularIntensity = Power(specularBase, sphere.alpha)
    Vector3 specularColor = sphere.specularColor * specularIntensity * sphere.ks

    // 3. 최종 색상 조합 (Ambient + Diffuse + Specular)
    Return sphere.ambientColor + diffuseColor + specularColor
```

이전 커밋에서는 디버깅을 위해 스펙큘러 성분만 출력하거나 일부를 주석 처리했으나, 이번 변경사항(diff)을 통해 **Ambient, Diffuse, Specular를 모두 더한 완전한 Phong Reflection 모델의 최종 결과물을 화면에 렌더링하도록 전환**하였습니다. 이로써 구(Sphere)는 완벽한 입체감과 광택을 동시에 가지게 됩니다.

---

### 3. 학습자가 겪은 개념적 도약

코드와 주석을 통해 학습자가 이 단계를 수행하며 다음과 같은 핵심 그래픽스 이론을 몸소 체득했음을 알 수 있습니다.

1. **벡터 방향성의 중요성 이해**: `ray.dir` 대신 `-ray.dir`을 사용하여 시선 벡터 $v$를 올바르게 정의한 점은 공간 기하학에 대한 높은 이해도를 보여줍니다.
2. **에너지 보존의 직관**: 무작정 값을 더하는 것이 아니라 $k_s$ (Specular Coefficient) 상수를 두어 하이라이트의 강도를 조절함으로써, 물리적으로 그럴듯한(plausible) 결과물을 만들어내는 감각을 익혔습니다.
3. **분기 구조에서 통합 구조로의 전환**: 렌더링 파이프라인을 작성할 때 개별 조명 요소를 따로 테스트해 보고, 최종적으로 이를 누적 합산하여 물리 현상을 합성하는 빌딩 블록 방식의 개발 흐름을 터득했습니다.

---

### 4. WebGPU 인터랙티브 데모로의 확장 제안

이 알고리즘을 최신 웹 그래픽스 표준인 **WebGPU**의 Compute Shader 또는 Fragment Shader로 구현한다면 다음과 같은 아키텍처를 가집니다.

```wgsl
// WGSL (WebGPU Shading Language)로 표현한 핵심 셰이더 개념
@compute @workgroup_size(16, 16)
fn cs_main(@builtin(global_invocation_id) id : vec3<u32>) {
    let screen_size = textureDimensions(outTexture);
    if (id.x >= screen_size.x || id.y >= screen_size.y) { return; }

    // C++의 TransformScreenToWorld와 동일한 레이 생성 로직
    let uv = vec2<f32>(id.xy) / vec2<f32>(screen_size);
    let ray = generateRay(uv); 
    
    let color = traceRay(ray); // Phong Shading 계산 수행
    
    textureStore(outTexture, id.xy, vec4<f32>(color, 1.0));
}
```

#### WebGPU 시각화 데모의 구성 및 효과
1. **실시간 패러미터 튜닝**: 브라우저 화면에 HTML UI(Slider)를 배치하여 `alpha`(Shininess) 값을 1.0에서 200.0까지, `ks` 값을 0.0에서 1.0까지 실시간으로 조절합니다. WebGPU의 Uniform Buffer를 통해 이 값이 GPU로 매 프레임 전달됩니다.
   * `alpha`가 낮을 때: 점토나 플라스틱처럼 넓고 둔탁한 하이라이트가 형성됩니다.
   * `alpha`가 높을 때: 당구공이나 당겨진 쇠구슬처럼 아주 작고 강렬한 점 형태의 하이라이트가 형성되어 금속성 질감이 즉각적으로 표현됩니다.
2. **인터랙티브 광원**: 마우스 드래그를 통해 광원의 위치(`light.pos`)를 실시간으로 이동시킵니다. 광원의 위치가 바뀜에 따라 구 표면의 하이라이트 동그라미가 마우스 궤적을 부드럽게 따라 움직이는 60fps 이상의 인터랙티브한 퐁 셰이딩을 웹브라우저에서 직접 경험할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/리뷰-phong-shading의-핵심-스펙큘러specular-반사-벡터-/demo.html" width="100%" height="700" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
