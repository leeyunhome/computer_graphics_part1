# 원근 투영(Perspective Projection)과 최단 거리 충돌 판정(Closest Collision)의 구현

이번 커밋은 3차원 컴퓨터 그래픽스의 핵심인 **원근감(Perspective)**을 구현하고, 광선과 여러 오브젝트가 교차할 때 발생하는 **오클루전(Occlusion, 가려짐) 현상**을 올바르게 처리하기 위한 레이트레이싱 기초 단계입니다. 

기존의 정투영(Orthographic Projection) 방식에서 벗어나, 가상의 카메라(Eye) 위치를 설정하고 원근 투영을 적용하는 수학적 기법과 함께, 레이트레이서에서 객체들의 전후 관계를 판별하는 알고리즘을 분석합니다.

---

## 1. 핵심 개념 및 수학적 원리

### 1) 원근 투영 (Perspective Projection)

정투영에서는 스크린의 픽셀 위치와 무관하게 모든 광선이 평행한 방향($\mathbf{d} = (0, 0, 1)$)으로 나아갔습니다. 이로 인해 물체의 깊이($z$)에 따른 크기 변화가 표현되지 않았습니다.

원근 투영에서는 가상의 관찰자 시점인 카메라 위치 $\mathbf{e}$ (코드에서의 `eyePos`)가 존재하며, 모든 광선은 이 투영 중심점을 기준으로 스크린의 픽셀 위치 $\mathbf{p}_{\text{world}}$를 통과하여 방사형으로 뻗어나갑니다.

광선의 수학적 정의는 다음과 같습니다.

$$\mathbf{r}(t) = \mathbf{o} + t\mathbf{d} \quad (t \ge 0)$$

여기서 광선의 시작점 $\mathbf{o}$와 방향 벡터 $\mathbf{d}$는 다음과 같이 설정됩니다.
*   **시작점 ($\mathbf{o}$)**: 스크린 공간 상의 3차원 좌표 $\mathbf{p}_{\text{world}}$ (`pixelPosWorld`)
*   **방향 벡터 ($\mathbf{d}$)**: 카메라 위치 $\mathbf{e}$에서 픽셀 위치 $\mathbf{p}_{\text{world}}$로 향하는 단위 벡터

$$\mathbf{d} = \frac{\mathbf{p}_{\text{world}} - \mathbf{e}}{\|\mathbf{p}_{\text{world}} - \mathbf{e}\|}$$

카메라가 스크린 뒤쪽($z = -1.5$)에 있고 스크린이 $z = 0.0$에 위치하므로, 광선은 카메라에서 시작하여 앞쪽($+z$ 방향)으로 퍼져나가는 원추형 시야각(Frustum)을 형성합니다. 이를 통해 멀리 있는 물체는 작게, 가까이 있는 물체는 크게 보이는 원근 효과가 자연스럽게 발생합니다.

---

### 2) 최단 거리 충돌 판정 (Closest Collision)과 오클루전

화면에 그려지는 픽셀은 광선 상에서 **가장 먼저 부딪히는(가장 가까운)** 물체의 표면이어야 합니다. 이를 오클루전 소팅(Occlusion Sorting) 또는 깊이 판정(Depth Testing)이라고 합니다.

광선과 구의 충돌 방정식에 의해 구해지는 충돌 거리 파라미터 $t$ (코드에서의 `hit.d`)는 광선의 시작점으로부터 충돌 지점까지의 거리를 나타냅니다. 
여러 물체가 광선의 경로 상에 놓여 있을 때, 올바른 충돌 지점을 결정하는 규칙은 다음과 같습니다.

1.  **유효성 검사**: 충돌 거리 $t$는 카메라 앞방향이어야 하므로 반드시 $t \ge 0$이어야 합니다.
2.  **최솟값 갱신**: 유효한 충돌 중 가장 작은 $t$ 값을 가지는 오브젝트를 선택합니다.

$$\text{Selected Hit} = \arg\min_{i} \{ t_i \mid t_i \ge 0 \}$$

---

## 2. 코드 리팩토링 및 잠재적 버그 분석

학습자가 작성한 변경 사항 중 `FindClosestCollision` 함수에는 레이트레이싱의 결과를 왜곡할 수 있는 **치명적인 논리적 오류(Bug)**가 존재합니다.

### 학습자의 기존 구현 분석 (오류 탐지)

```cpp
Hit FindClosestCollision(Ray& ray)
{
    float closestD = 1000.0; // inf
    Hit closestHit = Hit{ -1.0, dvec3(0.0), dvec3(0.0) };

    for (int l = 0; l < objects.size(); l++)
    {
        auto hit = objects[l]->CheckRayCollision(ray);

        if (hit.d >= 0.0f) // <- 버그 발생 지점!
        {
            closestD = hit.d;
            closestHit = hit;
            closestHit.obj = objects[l];
        }
    }

    return closestHit;
}
```

#### 문제점:
`hit.d >= 0.0f` 조건문만 존재하고, **현재 찾은 충돌 거리(`hit.d`)가 기존의 최소 충돌 거리(`closestD`)보다 작은지 비교하는 조건(`hit.d < closestD`)이 누락**되었습니다.

이로 인해 루프를 돌면서 단순히 "광선과 충돌하는 마지막 오브젝트"의 정보가 덮어씌워지게 됩니다. 현재 `objects` 배열에는 일부러 역순(`sphere3` -> `sphere2` -> `sphere1`)으로 객체가 담겨 있어 결과가 운 좋게 맞아떨어질 수 있으나, 오브젝트 정렬 순서가 바뀌거나 뒤쪽에 가려진 거대한 물체가 있을 경우 렌더링 순서가 뒤엉키게 됩니다.

#### 올바른 수정 방향:
```cpp
if (hit.d >= 0.0f && hit.d < closestD)
{
    closestD = hit.d;
    closestHit = hit;
    closestHit.obj = objects[l];
}
```

---

## 3. 핵심 알고리즘 추상화 (Pseudo-code)

원근 투영 레이트레이서의 전체 렌더링 파이프라인과 퐁 반사 모델(Phong Reflection Model)을 적용한 셰이딩 과정을 추상화한 의사코드입니다.

```python
# 퐁 반사 모델을 이용한 색상 계산
def compute_phong_reflection(hit, ray, light):
    # 1. 주변광 (Ambient)
    color = hit.obj.ambient
    
    # 2. 확산광 (Diffuse)
    dir_to_light = normalize(light.pos - hit.point)
    diffuse_intensity = max(dot(hit.normal, dir_to_light), 0.0)
    color += hit.obj.diffuse * diffuse_intensity
    
    # 3. 반사광 (Specular)
    reflect_dir = reflect(-dir_to_light, hit.normal)
    view_dir = -ray.direction
    specular_intensity = pow(max(dot(view_dir, reflect_dir), 0.0), hit.obj.shininess)
    color += hit.obj.specular * specular_intensity
    
    return color

# 픽셀 루프 및 광선 투사
def render_scene(width, height, eye_pos, objects, light):
    for y in range(height):
        for x in range(width):
            # 스크린 좌표를 월드 공간 좌표로 변환 (-1.0 ~ 1.0 범위)
            pixel_pos_world = transform_screen_to_world(x, y)
            
            # 원근 투영 광선 생성
            ray_dir = normalize(pixel_pos_world - eye_pos)
            ray = Ray(origin=pixel_pos_world, direction=ray_dir)
            
            # 가장 가까운 충돌 객체 탐색
            closest_hit = find_closest_collision(ray, objects)
            
            if closest_hit.is_valid():
                pixel_color = compute_phong_reflection(closest_hit, ray, light)
                write_pixel(x, y, clamp(pixel_color, 0.0, 1.0))
            else:
                write_pixel(x, y, Color.BLACK)
```

---

## 4. WebGPU 인터랙티브 데모 제안

이 원근 투영 레이트레이서 알고리즘을 최신 웹 표준 그래픽스 API인 **WebGPU**의 **Compute Shader(WGSL)**로 이전하면, CPU 싱글 스레드 또는 OpenMP 환경보다 수백 배 빠른 실시간 병렬 렌더링이 가능해집니다.

```rust
// WGSL (WebGPU Shading Language) Compute Shader 개념 예시
@group(0) @binding(0) var<uniform> camera : CameraUniform;
@group(0) @binding(1) var<storage, read> objects : array<Sphere>;
@group(0) var output_texture : texture_storage_2d<rgba8unorm, write>;

@compute @workgroup_size(16, 16)
fn cs_main(@builtin(global_invocation_id) id : vec3<u32>) {
    let screen_size = textureDimensions(output_texture);
    if (id.x >= screen_size.x || id.y >= screen_size.y) { return; }

    let pixel_pos = transform_screen_to_world(id.xy, screen_size);
    let ray_dir = normalize(pixel_pos - camera.eyePos);
    
    var ray = Ray(pixel_pos, ray_dir);
    let hit = find_closest_collision(ray); // Storage Buffer 내 구체들과 루프 연산
    
    var color = vec4<f32>(0.0, 0.0, 0.0, 1.0);
    if (hit.d >= 0.0) {
        color = vec4<f32>(calculate_phong(hit, ray), 1.0);
    }
    
    textureStore(output_texture, id.xy, color);
}
```

### 구현 시 시각화 요소:
1.  **실시간 카메라 제어 (Interactive Camera)**: 마우스 드래그를 통해 `eyePos` 좌표를 변경하면, 실시간으로 소실점이 왜곡되거나 3차원 공간의 깊이감이 동적으로 변하는 원근 효과를 경험할 수 있습니다.
2.  **구체 동적 배치**: 구체들의 $z$축 깊이를 조정함에 따라 슬라이더를 통해 실시간으로 오클루전이 바뀌며 앞쪽 구체가 뒤쪽 구체를 가리는 모습이 GPU를 통해 즉각적으로 렌더링됩니다.
3.  **실시간 디버깅 뷰**: 각 픽셀에서의 광선 방향 벡터 $\mathbf{d}$의 값 자체를 RGB 색상으로 매핑하여(예: `(dir.xyz + 1.0) * 0.5`), 원근 투영 시 광선이 퍼져나가는 형태의 그라데이션을 시각적으로 확인할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/원근-투영perspective-projection과-최단-거리-충돌-판정/demo.html" width="100%" height="700" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
