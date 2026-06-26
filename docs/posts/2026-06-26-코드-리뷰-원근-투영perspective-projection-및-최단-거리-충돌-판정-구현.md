# [코드 리뷰] 원근 투영(Perspective Projection) 및 최단 거리 충돌 판정 구현

이번 커밋은 3차원 컴퓨터 그래픽스의 핵심인 **원근 투영(Perspective Projection)**과 여러 물체가 레이(Ray)에 부딪혔을 때 가장 앞쪽에 있는 물체를 판별하는 **가려짐 처리(Occlusion Sorting / Depth Test)**를 레이트레이싱 파이프라인에 성공적으로 통합한 중요한 단계입니다. 

학습자가 직접 직관을 넓혀가며 수식과 알고리즘을 코드로 구현한 흐름을 분석하고, 한 단계 더 발전하기 위한 피드백을 제공합니다.

---

## 1. 핵심 개념 및 수학적 원리

### 1) 정투영(Orthographic) vs 원근 투영(Perspective)
기존 단계에서는 화면의 모든 픽셀에서 동일한 방향 $$(0, 0, 1)$$로 평행한 광선을 보냈습니다(정투영). 이 방식은 멀고 가까움에 따른 크기 변화가 없어 설계 도면 등에 유리하지만, 인간의 눈이나 카메라가 세상을 보는 방식과는 다릅니다.

원근 투영을 구현하기 위해, 카메라의 위치(눈의 위치) $$\mathbf{E}_{\text{eye}}$$를 가상의 3차원 공간 내 고정된 점 $$(0, 0, -1.5)$$에 배치합니다. 그리고 이미지 평면(스크린) 위의 한 점 $$\mathbf{P}_{\text{world}}$$를 향해 퍼져나가는 광선을 생성합니다.

광선의 수학적 정의는 다음과 같습니다.

$$ \mathbf{R}(t) = \mathbf{o} + t\mathbf{d} \quad (t \ge 0) $$

여기서 광선의 시작점 $$\mathbf{o}$$와 방향 벡터 $$\mathbf{d}$$는 다음과 같이 정의됩니다.

*   **광선의 시작점 (Origin, $$\mathbf{o}$$)**: $$\mathbf{P}_{\text{world}}$$ (픽셀의 월드 좌표)
*   **광선의 방향 (Direction, $$\mathbf{d}$$)**: 눈의 위치에서 픽셀을 향하는 벡터를 정규화(Normalize)한 것

$$ \mathbf{d} = \frac{\mathbf{P}_{\text{world}} - \mathbf{E}_{\text{eye}}}{\|\mathbf{P}_{\text{world}} - \mathbf{E}_{\text{eye}}\|} $$

이 식을 통해 스크린 중심에서 멀어질수록 광선이 바깥쪽으로 넓게 퍼지게 되어, 멀리 있는 물체일수록 작게 투영되는 원근 효과가 자연스럽게 발생합니다.

---

## 2. 알고리즘 추상화 (Pseudo-code)

원근 투영 광선 생성 및 최단 거리 충돌 판정 알고리즘의 전체적인 흐름은 다음과 같습니다.

```text
for each pixel (i, j) in screen:
    // 1. 픽셀 좌표를 3D 월드 좌표로 변환
    pixelPosWorld = TransformScreenToWorld(i, j)
    
    // 2. 원근 투영 광선(Ray) 생성
    rayDirection = Normalize(pixelPosWorld - eyePos)
    ray = Ray(origin = pixelPosWorld, direction = rayDirection)
    
    // 3. 씬의 모든 물체와 충돌 검사하여 가장 가까운 히트점 찾기
    closestHit = FindClosestCollision(ray)
    
    // 4. 충돌한 경우 퐁 반사 모델(Phong Reflection Model)을 적용해 픽셀 색상 결정
    if closestHit.d >= 0:
        pixelColor = CalculatePhongReflection(closestHit, ray)
    else:
        pixelColor = Black
        
    pixels[i, j] = pixelColor
```

---

## 3. 코드 변경 사항 분석 및 피드백 (중요한 버그 발견)

### 🔍 치명적인 논리 오류 분석 (`FindClosestCollision`)
학습자가 작성한 `FindClosestCollision` 함수를 보면, 가려짐 처리를 위해 최단 거리 `closestD`를 추적하고자 노력한 흔적이 보입니다.

```cpp
// 학습자의 코드 일부
Hit FindClosestCollision(Ray& ray)
{
    float closestD = 1000.0; // inf
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

    return closestHit;
}
```

#### 무엇이 문제인가요?
조건문 `if (hit.d >= 0.0f)` 내부에서 `closestD = hit.d;`로 값을 업데이트하고 있지만, **새로운 충돌 거리 `hit.d`가 기존의 최소 거리 `closestD`보다 작은지 비교하는 조건이 누락**되었습니다.

이로 인해 루프 내에서 충돌이 발생하는 모든 오브젝트 중 **가장 마지막으로 검사된 오브젝트의 충돌 정보**가 항상 최종 반환됩니다. 

현재 코드에서 구들이 역순으로 배치되어 있고(`sphere3` -> `sphere2` -> `sphere1`), 실제 시각적으로 가장 앞에 있는 `sphere1`이 가장 마지막 인덱스(`l = 2`)에 위치해 있어서 우연히 올바르게 렌더링된 것처럼 보였을 뿐입니다. 만약 오브젝트의 추가 순서가 바뀌거나 카메라의 구도가 바뀌면 뒤에 가려진 물체가 앞에 그려지는 렌더링 오류가 발생하게 됩니다.

#### 해결 방안 (Code Fix)
충돌 거리 `hit.d`가 현재 기록된 `closestD`보다 작을 때만 값을 갱신하도록 조건식을 수정해야 합니다.

```cpp
Hit FindClosestCollision(Ray& ray)
{
    float closestD = 1e6f; // 충돌 가능한 충분히 큰 값 (Infinity 역할)
    Hit closestHit = Hit{ -1.0, dvec3(0.0), dvec3(0.0) };

    for (int l = 0; l < objects.size(); l++)
    {
        auto hit = objects[l]->CheckRayCollision(ray);

        // 충돌 거리가 유효(0 이상)하고, 기존 최단 거리보다 작은 경우에만 업데이트
        if (hit.d >= 0.0f && hit.d < closestD)
        {
            closestD = hit.d;
            closestHit = hit;
            closestHit.obj = objects[l];
        }
    }

    return closestHit;
}
```

---

## 4. 조명 모델 적용: 퐁 반사 모델 (Phong Reflection Model)

물체의 입체감을 살리기 위해 `traceRay` 함수에서 구현된 조명 연산은 **퐁 반사 모델(Phong Reflection Model)**을 충실히 따르고 있습니다. (래스터화 단계의 'Phong Shading'과 혼동하지 않아야 하며, 여기서는 수학적 빛의 반사를 근사하는 조명 모델을 지칭합니다.)

$$ \text{Color} = I_{\text{ambient}} + I_{\text{diffuse}} + I_{\text{specular}} $$

*   **Ambient (환경광)**: 주변 공간에 기본적으로 퍼져 있는 빛에 의한 최소한의 밝기.
*   **Diffuse (난반사)**: 램버트 코사인 법칙(Lambert's Cosine Law)에 따라 표면의 법선 벡터 $$\mathbf{N}$$과 광원 방향 벡터 $$\mathbf{L}$$의 내적($$\mathbf{N} \cdot \mathbf{L}$$)으로 계산되는 빛의 밝기.
*   **Specular (경면반사)**: 빛이 매끄러운 표면에서 정반사되어 눈으로 직접 들어오는 강한 하이라이트 효과. 반사 벡터 $$\mathbf{R}$$과 시선 방향의 역벡터 $$-\mathbf{D}$$의 내적을 물체의 거칠기 상수 `alpha`만큼 거듭제곱하여 계산합니다.

---

## 5. WebGPU 인터랙티브 데모 확장 가이드

현재 CPU 환경에서 `omp parallel for`로 병렬 처리하고 있는 레이트레이싱 파이프라인은 GPU 기반의 **WebGPU Compute Shader**를 활용하면 실시간(Interactive) 프레임레이트로 매우 손쉽게 전환할 수 있습니다.

### WGSL Compute Shader 시각화 구조
WebGPU의 셰이딩 언어인 WGSL(WebGPU Shading Language)을 이용해 브라우저에서 이 씬을 실행한다면 다음과 같은 방식으로 설계됩니다.

1.  **Workgroup 및 스레드 매핑**: CPU의 이중 루프(`width`, `height`)가 GPU의 2D 스레드 그리드 `@workgroup_size(16, 16)`로 직접 매핑됩니다.
2.  **구조체 정의 및 스토리지 버퍼**:
    ```wgsl
    struct Sphere {
        center: vec3<f32>,
        radius: f32,
        ambient: vec3<f32>,
        diffuse: vec3<f32>,
        specular: vec3<f32>,
        alpha: f32,
    }
    @group(0) @binding(0) var<storage, read> objects: array<Sphere>;
    @group(0) @binding(1) var outputTex: texture_storage_2d<rgba8unorm, write>;
    ```
3.  **Compute Shader 메인 함수**:
    *   CPU 코드의 `Render` 함수 내부 동작이 그대로 이식됩니다.
    *   각 스레드의 글로벌 ID `global_id.xy`를 기반으로 `TransformScreenToWorld` 연산을 수행하여 레이를 쏘고, 결과를 `textureStore`를 통해 화면에 출력합니다.
4.  **인터랙티브 요소**: WebGPU 버퍼를 통해 마우스 드래그 좌표를 `eyePos` Uniform 변수로 실시간 전달하면, 웹 브라우저 상에서 마우스의 움직임에 따라 구체들의 원근이 역동적으로 변화하고 가려짐 처리가 완벽하게 동적 계산되는 고성능 그래픽스 데모를 경험할 수 있습니다.