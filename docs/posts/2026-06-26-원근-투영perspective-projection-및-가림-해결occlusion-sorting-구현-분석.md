# 원근 투영(Perspective Projection) 및 가림 해결(Occlusion Sorting) 구현 분석

본 커밋은 레이트레이싱 기법의 기초에서 매우 중요한 두 가지 물리적/시각적 사실성 단계를 구현하고 있습니다. 첫째는 평행 광선 대신 카메라(눈)의 위치로부터 퍼져나가는 광선을 생성하는 **원근 투영(Perspective Projection)**이며, 둘째는 광선의 진행 경로 상에 놓인 여러 물체 중 가장 가까운 물체를 선택하는 **최단 거리 충돌 판정(Occlusion Sorting)**입니다.

---

## 1. 핵심 개념 및 수학적 원리

### (1) 원근 투영 (Perspective Projection)

기존 단계의 정투영(Orthographic Projection)에서는 화면의 모든 픽셀에서 동일한 방향(예: $z$축 방향인 $\vec{d} = (0, 0, 1)$)으로 평행한 광선을 투사했습니다. 이는 멀고 가까움에 따른 크기 변화가 없는 비현실적인 이미지를 만듭니다.

이를 카메라의 렌즈와 인간의 눈과 유사한 원근 투영으로 전환하기 위해, 3차원 공간상의 카메라(눈)의 위치 $\mathbf{E}$ (`eyePos`)를 도입합니다. 스크린 상의 한 점을 $\mathbf{P}_{\text{world}}$ (`pixelPosWorld`)라고 할 때, 카메라에서 시작하여 스크린의 픽셀을 통과하는 광선의 방향 벡터 $\mathbf{D}$는 다음과 같이 정의됩니다.

$$ \mathbf{D} = \frac{\mathbf{P}_{\text{world}} - \mathbf{E}}{\|\mathbf{P}_{\text{world}} - \mathbf{E}\|} $$

학습자는 코드에서 광선의 시작점(Origin)을 $\mathbf{P}_{\text{world}}$로 설정하고 방향 벡터를 $\mathbf{D}$로 설정하였습니다. 이는 카메라 위치 $\mathbf{E}$에서 시작하는 것과 수학적으로 동일선상에 있지만, 스크린 평면($z=0$) 이전의 영역을 불필요하게 계산하지 않도록 만드는 실용적인 최적화 기법입니다.

### (2) 최단 거리 충돌 판정 (Closest Collision)

하나의 광선 경로 상에 여러 개의 구(Sphere)가 겹쳐서 존재할 때, 관찰자에게 보이는 것은 **가장 앞에 있는(즉, 충돌 거리 $t$가 가장 작은) 물체**뿐입니다. 이를 컴퓨터 그래픽스에서는 가림 효과(Occlusion)라고 부르며, 레이트레이싱에서는 광선-물체 충돌 지점의 거리 파라미터 $t \ge 0$ (코드의 `hit.d`) 중 최솟값을 탐색하여 해결합니다.

광선의 수학적 정의는 다음과 같습니다.

$$ \mathbf{R}(t) = \mathbf{O} + t\mathbf{D} \quad (t \ge 0) $$

여기서 가장 작은 양수 $t$를 갖는 충돌면의 정보를 유지하고 갱신하는 것이 알고리즘의 핵심입니다.

---

## 2. 알고리즘 설계 및 가상코드 (Pseudo-code)

학습자가 구현하려 한 최단 거리 충돌 판정 알고리즘을 추상화하면 다음과 같습니다.

```text
function FindClosestCollision(Ray ray):
    closestDistance = INF
    closestHit = InvalidHit
    
    for each object in scene:
        hit = object.CheckCollision(ray)
        
        // 광선 앞쪽에 충돌이 존재하고, 기존 최단 거리보다 더 가까운 경우에만 갱신
        if hit.isValid and hit.distance >= 0 and hit.distance < closestDistance:
            closestDistance = hit.distance
            closestHit = hit
            closestHit.object = object
            
    return closestHit
```

---

## 3. 코드 분석 및 주요 피드백 (버그 탐지)

학습자의 코드 변화를 면밀히 분석한 결과, **구현상 치명적인 버그가 존재합니다.** 

### 버그 분석
학습자는 `FindClosestCollision` 함수를 다음과 같이 수정하였습니다.

```cpp
float closestD = 1000.0; // INF 역할
Hit closestHit = Hit{ -1.0, dvec3(0.0), dvec3(0.0) };

for (int l = 0; l < objects.size(); l++)
{
    auto hit = objects[l]->CheckRayCollision(ray);

    if (hit.d >= 0.0f) // <--- 버그 발생 지점!
    {
        closestD = hit.d;
        closestHit = hit;
        closestHit.obj = objects[l];
    }
}
```

* **문제점:** 최단 거리를 추적하기 위해 `closestD` 변수를 정의하고 초기값을 `1000.0`으로 설정했으나, `if` 조건문 내에서 **현재 충돌 거리 `hit.d`가 이전 최단 거리 `closestD`보다 작은지 비교하는 연산(`hit.d < closestD`)이 누락**되었습니다.
* **결과:** 이로 인해 실제 물리적으로 가장 가까운 물체가 선택되는 것이 아니라, 단순히 루프의 마지막 순서에 있는 물체 중 충돌이 일어난 물체가 이전 결과를 덮어쓰게 됩니다. 물체가 생성된 역순(`sphere1` -> `sphere2` -> `sphere3` 순으로 갱신)에 따라 렌더링 결과가 가로막혀 엉뚱하게 보일 수 있습니다.

### 수정 권고안
진정한 최단 거리 충돌 판정(Occlusion)을 달성하려면 해당 조건문을 다음과 같이 수정해야 합니다.

```cpp
// 수정 후 안전한 조건문
if (hit.d >= 0.0f && hit.d < closestD)
{
    closestD = hit.d;
    closestHit = hit;
    closestHit.obj = objects[l];
}
```

---

## 4. 퐁 반사 모델 (Phong Reflection Model)의 적용

학습자는 렌더링 방정식의 기초가 되는 **퐁 반사 모델(Phong Reflection Model)**을 적용하여 광원과 물체 표면의 상호작용을 계산하고 있습니다.

* **Ambient (환경광):** 장면 전체에 균일하게 가해지는 기초 빛입니다. `hit.obj->amb`
* **Diffuse (난반사광):** 표면의 법선 벡터 $\mathbf{N}$(`hit.normal`)과 광원으로 향하는 벡터 $\mathbf{L}$(`dirToLight`)의 내적을 통해 각도에 따른 빛의 감쇄를 표현합니다.
  $$ I_{\text{diffuse}} = \max(\mathbf{N} \cdot \mathbf{L}, 0) $$
* **Specular (경면반사광):** 빛의 반사 방향 $\mathbf{R}$(`reflectDir`)과 카메라를 향하는 시선 방향 $\mathbf{V}$(`-ray.dir`)의 정렬 상태에 따라 하이라이트를 생성합니다.
  $$ I_{\text{specular}} = \max(\mathbf{R} \cdot \mathbf{V}, 0)^{\alpha} $$

이 세 가지 요소를 더해 최종 픽셀 색상을 완성합니다.

---

## 5. WebGPU 인터랙티브 데모

이 C++ 기반 CPU 레이트레이싱 코드를 최신 웹 그래픽스 API인 **WebGPU**로 이전하면 어떻게 확장할 수 있을까요?

### WebGPU Compute Shader 기반 시각화 개념
WebGPU에서는 CPU의 다중 스레드(OpenMP) 처리 한계를 뛰어넘어, 수백만 개의 픽셀을 GPU의 수천 개 코어에서 완벽하게 병렬로 처리할 수 있습니다. 

* **WGSL (WebGPU Shading Language) 구현**: `Render` 함수의 이중 `for` 루프는 GPU 상에서 `@compute @workgroup_size(16, 16)` 형식의 컴퓨트 셰이더로 매핑됩니다. 각 스레드는 고유의 픽셀 좌표 `global_id`를 할당받아 독립적으로 광선을 생성합니다.
* **인터랙티브 카메라 조작**: 마우스 드래그 이벤트를 받아 자바스크립트가 `eyePos` 변수를 업데이트하고 이를 **Uniform Buffer**를 통해 GPU로 전달하면, 사용자가 실시간으로 시점을 회전하고 확대/축소하며 원근감이 변하는 3차원 구체들을 끊김 없이(60fps 이상) 관찰할 수 있습니다.
* **실시간 레이트레이싱 캔버스**: 셰이더 연산 결과는 `textureStore`를 통해 GPU 텍스처에 쓰이고, 이는 곧바로 HTML5 `<canvas>`에 드로우되어 웹 환경에서 뛰어난 시각적 상호작용을 선사하게 됩니다.