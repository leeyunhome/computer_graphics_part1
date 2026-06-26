# [코드 리뷰] 원근 투영(Perspective Projection) 및 최단 거리 충돌 검사(Closest Hit) 구현

이번 커밋은 3차원 컴퓨터 그래픽스의 핵심 기초인 **원근 투영(Perspective Projection)**과 여러 물체가 겹쳐 있을 때 올바르게 가려짐을 처리하는 **최단 거리 충돌 검사(Occlusion Sorting)**를 구현한 중요한 단계입니다.

학습자가 직접 코드를 변경하며 Raytracing의 기초를 다지는 과정에서 아주 훌륭한 접근을 보여주었으나, 코드 내에 **치명적인 논리적 오류(버그)**가 포함되어 있습니다. 그래픽스 전문자의 시선에서 구현된 개념을 수학적으로 분석하고, 발견된 오류와 해결책을 제시하겠습니다.

---

## 1. 핵심 개념 및 변경 사항 개요

이전 단계의 정투영(Orthographic Projection)과 정렬되지 않은 충돌 처리에서 한 단계 나아가, 실제 카메라가 세상을 바라보는 방식과 시각적 차폐를 모사하기 위해 두 가지 큰 변화를 주었습니다.

1. **정투영에서 원근 투영으로의 전환 (Perspective View)**
   * **기존 (Orthographic)**: 화면의 모든 픽셀에서 평행한 방향($(0, 0, 1)$)으로 광선을 투사했습니다. 이 경우 물체의 깊이($z$)와 상관없이 크기가 일정하게 유지됩니다.
   * **변경 (Perspective)**: 고정된 가상의 눈 위치($E$)에서 픽셀의 세계 공간 좌표($P$)를 향하는 방향 벡터를 생성합니다. 멀리 있는 물체는 더 작게, 가까이 있는 물체는 더 크게 보이는 원근 효과를 얻습니다.

2. **최단 거리 충돌 검사 구현 시도 (Closest Hit / Occlusion)**
   * **기존**: 광선이 어떤 물체든 하나라도 부딪히면 즉시 그 물체의 색상을 반환하여, 오브젝트 벡터에 담긴 순서대로만 그려지는 한계가 있었습니다.
   * **변경**: 모든 물체와의 충돌 거리를 검사하여, **카메라와 가장 가까운 양수의 거리($d$)에서 충돌한 물체**를 찾아 렌더링하고자 했습니다.

---

## 2. 핵심 그래픽스 이론 및 수식

### 2.1 원근 광선 생성 (Perspective Ray Generation)

카메라(눈)의 위치를 $E(eyePos)$, 픽셀의 월드 공간 좌표를 $P(pixelPosWorld)$라고 할 때, 카메라에서 픽셀을 통과하여 뻗어나가는 광선의 방향 벡터 $D(rayDir)$는 다음과 같이 정의됩니다.

$$D = \frac{P - E}{\|P - E\|}$$

이 방향 벡터는 크기가 1인 단위 벡터(Unit Vector)로 정규화(Normalize)되어야 광선-구체 충돌 방정식 등에서 거리 파라미터 $t$(또는 $d$)를 정확한 물리적 거리 단위로 사용할 수 있습니다.

따라서 생성되는 광선 방정식은 다음과 같습니다.

$$R(t) = P + tD \quad (t \ge 0)$$

*(참고: 학습자는 광선의 시작점을 눈 $E$ 대신 스크린 공간의 픽셀 위치 $P$로 설정하여 스크린 뒤쪽의 물체가 그려지지 않도록 자연스럽게 Near Plane 클리핑 효과를 내었습니다.)*

### 2.2 최단 거리 충돌 (Closest Hit) 수식

장면에 존재하는 물체들의 집합을 $O = \{o_1, o_2, \dots, o_n\}$이라 하고, 광선 $R(t)$가 각 물체 $o_i$와 충돌하는 거리를 $t_i$라고 할 때, 눈에 보여야 하는 실제 충돌 지점 $t_{\text{closest}}$는 다음과 같이 정의됩니다.

$$t_{\text{closest}} = \min \{ t_i \mid t_i \ge 0, \quad i = 1, \dots, n \}$$

즉, 양의 거리(카메라 앞쪽)에 있는 충돌점 중 **최솟값**을 취해야 올바른 차폐(Occlusion)가 이루어집니다.

---

## 3. 구현 분석 및 버그 피드백 (중요)

### 🔴 발견된 논리적 오류 (Bug)

학습자가 작성한 `FindClosestCollision` 함수의 구현부를 살펴보면 치명적인 실수가 존재합니다.

```cpp
// 학습자의 코드 중에서
float closestD = 1000.0; // inf
Hit closestHit = Hit{ -1.0, dvec3(0.0), dvec3(0.0) };

for (int l = 0; l < objects.size(); l++)
{
    auto hit = objects[l]->CheckRayCollision(ray);

    if (hit.d >= 0.0f)
    {
        closestD = hit.d; // <--- 버그 발생 지점!
        closestHit = hit;
        closestHit.obj = objects[l];
    }
}
```

#### 문제점 분석:
* `closestD`라는 변수를 최댓값(1000.0)으로 초기화해 두고서, 루프 내부에서 새로 찾은 충돌 거리 `hit.d`가 **기존의 `closestD`보다 작은지 비교하는 조건문(`hit.d < closestD`)이 누락**되었습니다.
* 결과적으로, 이 코드는 가장 가까운 물체를 찾는 것이 아니라 **충돌이 일어난 물체 중 `objects` 벡터의 가장 마지막에 존재하는 물체**의 정보를 덮어쓰게 됩니다. 
* 현재 생성자에서 오브젝트를 추가한 순서가 역순(`sphere3`, `sphere2`, `sphere1`)이므로, 우연히 정렬된 것처럼 보일 수 있으나 배치 순서가 바뀌면 즉시 렌더링이 깨지게 됩니다.

---

## 4. 올바른 충돌 탐색 알고리즘 (의사코드)

수학적 정의에 부합하도록 최단 거리를 올바르게 필터링하는 알고리즘의 의사코드(Pseudo-code)입니다. 학습자는 이를 참고하여 C++ 코드를 수정해야 합니다.

```text
function FindClosestCollision(ray)
    closestDistance = INFINITY
    closestHit = InvalidHit

    for each object in scene.objects
        hit = object.CheckRayCollision(ray)
        
        // 1. 카메라 앞쪽에 충돌이 있고
        // 2. 그 충돌 거리가 지금까지 발견한 최소 거리보다 작은 경우에만 갱신
        if hit.distance >= 0.0 and hit.distance < closestDistance then
            closestDistance = hit.distance
            closestHit = hit
            closestHit.object = object
            
    return closestHit
```

### 올바른 C++ 수정 코드:
```cpp
if (hit.d >= 0.0f && hit.d < closestD) // 거리 비교 조건 추가
{
    closestD = hit.d;
    closestHit = hit;
    closestHit.obj = objects[l];
}
```

---

## 5. Phong Reflection Model (퐁 반사 모델)의 적용

광선 추적을 통해 가장 가까운 충돌점(`closestHit`)을 찾은 후, 학습자는 `traceRay` 함수에서 **Phong Reflection Model(퐁 반사 모델)**을 사용하여 픽셀의 최종 색상을 계산하고 있습니다.

$$\text{Color} = K_a I_a + K_d I_d (\vec{N} \cdot \vec{L}) + K_s I_s (\vec{V} \cdot \vec{R})^\alpha$$

* **Ambient(환경광)**: `hit.obj->amb` (간접광을 모사하는 상수 배경색)
* **Diffuse(난반사광)**: `hit.obj->dif * diff` (표면의 법선 $\vec{N}$과 광원 방향 $\vec{L}$의 내적에 비례)
* **Specular(경면광)**: `hit.obj->spec * specular` (카메라가 바라보는 방향 $\vec{V}$와 빛의 반사 방향 $\vec{R}$의 내적을 신 가수 $\alpha$로 거듭제곱)

이 수식들이 셰이더나 특정 API에 의존하지 않고, CPU 단에서 수학 라이브러리(GLM)를 통해 순수하게 코드로 계산되어 스크린에 투사되는 훌륭한 파이프라인 구조를 갖추고 있습니다.

---

## 6. WebGPU 인터랙티브 데모 제안

이 원근 투영 레이트레이싱 알고리즘을 최신 웹 그래픽스 API인 **WebGPU**의 **Compute Shader**로 마이그레이션한다면 다음과 같이 작동할 것입니다.

```wgsl
// WebGPU WGSL Compute Shader 예시 개념 코드
@group(0) @binding(0) var<storage, read_write> pixels: array<vec4f>;

struct Ray {
    origin: vec3f,
    direction: vec3f,
};

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) id: vec3u) {
    let width = 800u;
    let height = 600u;
    if (id.x >= width || id.y >= height) { return; }

    let eyePos = vec3f(0.0, 0.0, -1.5);
    let pixelPosWorld = transformScreenToWorld(id.xy, width, height);
    
    // WebGPU GPU 병렬 처리로 각 스레드가 광선을 생성
    let rayDir = normalize(pixelPosWorld - eyePos);
    var pixelRay = Ray(pixelPosWorld, rayDir);

    let color = traceRay(pixelRay);
    pixels[id.y * width + id.x] = vec4f(color, 1.0);
}
```

### 인터랙티브 데모의 시각화 효과:
1. **GPU 기반 실시간 렌더링**: CPU 멀티스레딩(OpenMP)으로 수십 FPS에 머물던 레이트레이싱을 WebGPU Compute Shader를 통해 60 FPS 이상의 부드러운 화면으로 웹 브라우저에서 직접 구동할 수 있습니다.
2. **실시간 카메라 조작**: 마우스 드래그를 통해 `eyePos` 좌표를 실시간으로 변경해 볼 수 있습니다. 원근 투영의 왜곡 현상(가장자리가 늘어나는 현상)과 구체들이 카메라 시점에 따라 서로를 가리는 가려짐(Occlusion) 현상이 실시간으로 웹상에 시각화됩니다.
3. **오브젝트 실시간 정렬 검증**: 세 개의 구체가 깊이($z$) 값에 상관없이 물리적으로 가까운 순서대로 가려지는 깊이 버퍼가 없는 실시간 Ray-Scene Collision 데모를 인터랙티브하게 조작할 수 있습니다.