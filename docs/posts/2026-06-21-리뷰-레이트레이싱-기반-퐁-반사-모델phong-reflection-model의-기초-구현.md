# [리뷰] 레이트레이싱 기반 퐁 반사 모델(Phong Reflection Model)의 기초 구현

이번 커밋은 광선 추적법(Raytracing) 환경에서 가장 기초적이면서도 강력한 로컬 조명 모델인 **퐁 반사 모델(Phong Reflection Model)**의 첫 단추를 꿰는 중요한 단계입니다. 

학습자는 단순히 물체의 유무에 따른 단색(Flat) 출력을 넘어, 빛과 표면의 기하학적 관계를 활용한 **확산광(Diffuse Reflection)**을 성공적으로 구현하였습니다.

---

## 1. 커밋의 핵심 개념: 람베르트 확산광(Lambertian Diffuse)의 수학적 구현

이 커밋의 핵심은 광원과 물체 표면의 법선 벡터(Normal Vector) 사이의 각도를 기반으로 빛의 세기를 결정하는 것입니다. 물리적으로 이상적인 거친 표면(Lambertian Surface)은 빛이 들어오는 각도에 따라 에너지를 흡수하고 사방으로 균일하게 반사합니다.

### 기하학적 원리와 수식

학습자가 구현한 코드의 핵심 수학 공식은 다음과 같습니다.

1. **광원 방향 벡터 계산 ($\vec{L}$)**  
   충돌 지점($\mathbf{P}$)에서 광원의 위치($\mathbf{P}_{\text{light}}$)를 향하는 단위 벡터를 구합니다.
   $$ \vec{L} = \frac{\mathbf{P}_{\text{light}} - \mathbf{P}}{\|\mathbf{P}_{\text{light}} - \mathbf{P}\|} $$

2. **내적(Dot Product)을 통한 투영과 클램핑(Clamping)**  
   표면의 법선 벡터 $\vec{N}$과 광원 방향 벡터 $\vec{L}$의 내적을 통해 두 벡터가 이루는 사이각 $\theta$의 코사인 값을 구합니다. 빛이 표면 뒤쪽에서 들어오는 경우(음수 값)를 방지하기 위해 $\max$ 함수를 사용하여 $0.0$으로 하한선을 제한합니다. 이를 **Half-Lambert** 또는 **Clamped Cosine**이라고 합니다.
   $$ I_{\text{diffuse}} = \max(\vec{N} \cdot \vec{L}, 0.0) $$

3. **최종 색상 결정**  
   물체의 고유 확산색(Diffuse Color, $\mathbf{C}_{\text{diff}}$)에 계산된 빛의 세기를 곱하여 최종 픽셀 색상을 결정합니다.
   $$ \mathbf{C}_{\text{final}} = \mathbf{C}_{\text{diff}} \times I_{\text{diffuse}} $$

---

## 2. 알고리즘 추상화 (의사코드)

학습자가 작성한 `traceRay` 함수 내의 조명 계산 로직을 추상화하면 다음과 같은 흐름을 가집니다.

```text
function traceRay(ray):
    // 1. 광선과 구체의 충돌 검사
    hitRecord = intersect(ray, sphere)
    
    if hitRecord.didCollide == false:
        return BACKGROUND_COLOR (Black)
        
    // 2. 조명 계산을 위한 기하학적 벡터 추출
    N = hitRecord.normal               // 충돌 지점의 법선 벡터 (정규화됨)
    P = hitRecord.point                // 충돌 지점의 3차원 좌표
    L = normalize(light.position - P)  // 충돌 지점에서 광원을 향하는 단위 벡터
    
    // 3. 람베르트 코사인 법칙 적용 (Diffuse)
    diffuseIntensity = max(dot(N, L), 0.0)
    
    // 4. 최종 색상 계산 (현재 단계에서는 Diffuse만 반영)
    finalColor = sphere.diffuseColor * diffuseIntensity
    
    return finalColor
```

---

## 3. 학습자 코드의 구조적 특징 및 발전 단계 분석

* **점진적 구현 방식(Step-by-step) 채택**:  
  퐁 반사 모델은 크게 세 가지 요소인 **Ambient(환경광), Diffuse(확산광), Specular(경면광)**로 나뉩니다. 학습자는 이 세 가지를 한 번에 구현하지 않고, 주석 처리를 통해 `Diffuse`를 먼저 정확히 시각화하여 검증하려는 좋은 접근법을 보여주고 있습니다.
  
* **스펙큘러(Specular) 구현을 위한 준비**:  
  코드 내에 `// const vec3 reflectDir = ... // r = 2 (n dot l) n - l`과 같은 주석이 존재합니다. 이는 빛의 반사 벡터($\vec{R}$)를 구하여 카메라(관찰자) 방향 벡터($\vec{V}$)와의 내적을 통해 하이라이트(Highlight)를 구현하기 위한 준비 단계임을 보여줍니다.
  $$ \vec{R} = 2(\vec{N} \cdot \vec{L})\vec{N} - \vec{L} $$

---

## 4. WebGPU 인터랙티브 데모 제안

이 커밋에서 구현된 퐁 셰이딩의 확산광 이론을 웹 브라우저에서 실시간으로 테스트할 수 있도록 **WebGPU Compute Shader** 데모를 구성한다면 다음과 같이 설계할 수 있습니다.

### 데모 구성 요소 및 시각화 효과

```
                     [ WebGPU Canvas (HTML5) ]
+-----------------------------------------------------------------+
|                                                                 |
|                           * (Light Source - Drag to Move)       |
|                                                                 |
|                        .-----.                                  |
|                      .-       -.                                |
|                     /  *       \  <-- Real-time Diffuse Shading |
|                    |  (Bright)  |                               |
|                     \          /                                |
|                      '-       -'                                |
|                        '-----'                                  |
|                                                                 |
+-----------------------------------------------------------------+
[ Light Position X: --|-- ] [ Sphere Color: [Blue] ] [ Specular: On/Off ]
```

1. **실시간 마우스 드래그를 통한 광원 제어**:
   * 브라우저 화면상에서 마우스를 움직이거나 슬라이더를 조절하면, GPU의 Uniform Buffer로 전달되는 `light.pos` 값이 실시간으로 업데이트됩니다.
   * 사용자는 광원의 위치가 바뀜에 따라 구체 표면의 밝은 부분(음영)이 실시간으로 부드럽게 변하는 람베르트 코사인 효과를 즉각적으로 관찰할 수 있습니다.

2. **WGSL Compute Shader 커널**:
   * CPU에서 픽셀 루프를 돌리는 대신, WebGPU의 `compute` 스테이지를 활용하여 각 픽셀 스레드가 병렬로 Ray-Sphere Intersection과 Diffuse 연산을 수행하도록 합니다.
   * `TextureStorage`에 결과를 직접 기록하여 60fps 이상의 극도로 부드러운 인터랙티브 퐁 셰이딩을 시연할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/리뷰-레이트레이싱-기반-퐁-반사-모델phong-reflection-mod/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
