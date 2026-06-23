# 퐁 반사 모델(Phong Reflection Model)의 스펙큘러 하이라이트 및 반사 벡터 구현

본 커밋은 3차원 컴퓨터 그래픽스에서 물체의 입체감과 질감을 표현하는 데 핵심적인 **퐁 반사 모델(Phong Reflection Model)** 중, 광택 효과를 담당하는 **스펙큘러 하이라이트(Specular Highlight)**를 물리적 벡터 연산을 통해 구현한 단계입니다. 

학습자는 단순히 라이브러리 함수에 의존하지 않고, 빛의 입사각과 표면의 법선 벡터 사이의 기하학적 관계를 직접 정의하여 반사 벡터를 계산하고 이를 픽셀 셰이딩(여기서는 레이트레이싱 기법)에 적용하였습니다.

---

## 1. 핵심 수학적 개념 및 물리적 모델

퐁 반사 모델에서 스펙큘러 하이라이트는 관찰자의 시선이 빛의 정반사 경로와 얼마나 일치하는지에 따라 결정됩니다. 이 커밋의 핵심은 **반사 벡터(Reflection Vector)** $r$과 **시선 벡터(View Vector)** $v$ 사이의 관계를 수학적으로 정의하고 구현한 것입니다.

### 반사 벡터($r$)의 유도
광원 방향 벡터를 $l$ (물체 표면에서 광원을 향하는 벡터), 표면의 법선 벡터를 $n$이라고 할 때, 정반사 방향으로 나아가는 벡터 $r$은 다음과 같은 대칭 관계를 가집니다.

$$ r = 2(n \cdot l)n - l $$

* **$n \cdot l$ (내적):** 법선 벡터와 광원 벡터가 이루는 각도의 코사인 값으로, 표면이 광원을 얼마나 정면으로 마주보고 있는지를 나타냅니다.
* **$2(n \cdot l)n$:** 광원 벡터 $l$을 법선 벡터 $n$에 투영한 길이의 2배만큼 법선 방향으로 늘린 벡터입니다. 여기서 $l$을 빼줌으로써 정반사 벡터 $r$이 도출됩니다.

### 스펙큘러 하이라이트($I_{specular}$) 공식
반사 벡터 $r$이 구해지면, 카메라(시선) 방향 벡터 $v$와의 정렬 상태를 계산하여 스펙큘러 강도를 결정합니다.

$$ I_{specular} = k_s \cdot C_{specular} \cdot (\max(v \cdot r, 0))^{\alpha} $$

* **$v$ (시선 벡터):** 물체 표면에서 카메라를 향하는 벡터입니다. 코드에서는 광선의 역방향인 `-ray.dir`로 정의됩니다.
* **$\alpha$ (Shininess, 광택도):** 하이라이트의 집중도를 조절하는 지수(Exponent)입니다. 값이 커질수록 하이라이트 영역이 좁고 강렬해져 금속이나 유리 같은 매끄러운 질감을 표현하고, 작을수록 플라스틱처럼 넓게 퍼지는 질감을 표현합니다. (본 구현에서는 `alpha = 9.0f` 사용)
* **$k_s$ (스펙큘러 계수):** 반사광의 세기를 조절하는 인자입니다. (본 구현에서는 `ks = 0.8f` 사용)

---

## 2. 학습자가 직접 구현하며 이해한 개념

### ① 레이트레이싱 환경에서의 시선 벡터($v$) 정의
일반적으로 래스터라이저(Rasterizer) 기반 렌더링 파이프라인에서는 카메라 위치와 픽셀 위치의 차를 이용해 시선 벡터를 구합니다. 하지만 레이트레이싱에서는 픽셀로 쏘아 보낸 광선(Ray)의 방향 벡터 `ray.dir`이 존재하므로, 카메라를 향하는 벡터 $v$는 광선 방향의 반대 방향인 `-ray.dir`이 된다는 기하학적 사실을 명확히 이해하고 코드로 구현했습니다.

### ② 스펙큘러 하이라이트 개별 시각화 (Debugging technique)
학습자는 전체 조명(Ambient + Diffuse + Specular)을 한 번에 합쳐서 출력하지 않고, 최종 반환값으로 스펙큘러 성분만 단독 반환(`return sphere->spec * specular * sphere->ks;`)하도록 설정하였습니다. 이는 구현한 수학적 수식이 화면에 정확한 하이라이트 원형 범위를 만들어내는지 직관적으로 검증하기 위한 훌륭한 디버깅 접근법입니다.

---

## 3. 핵심 알고리즘 구조 (추상화 및 의사코드)

학습자가 작성한 `traceRay` 함수의 핵심 구조는 다음과 같이 추상화할 수 있습니다.

```cpp
Color traceRay(Ray ray)
{
    // 1. 광선과 구체의 충돌 검사
    HitRecord hit = intersect(ray, sphere);
    if (!hit.hasIntersected) {
        return Color(0, 0, 0); // 배경색 (검은색)
    }

    // 2. 표면 속성 및 기하 정보 정의
    Vector3 N = hit.normal;                      // 법선 벡터
    Vector3 L = normalize(Light.pos - hit.point); // 광원 벡터
    Vector3 V = normalize(-ray.dir);             // 시선 벡터 (카메라 방향)

    // 3. 반사 벡터 계산 (r = 2(n·l)n - l)
    Vector3 R = 2.0 * dot(N, L) * N - L;

    // 4. 스펙큘러 강도 계산 (pow(max(v·r, 0), alpha))
    float specFactor = pow(max(dot(V, R), 0.0), sphere.alpha);

    // 5. 최종 스펙큘러 색상 반환
    return sphere.specularColor * specFactor * sphere.specularIntensity;
}
```

---

## 4. WebGPU 인터랙티브 데모로의 확장 구상

이 알고리즘을 최신 웹 그래픽스 API인 **WebGPU**의 Compute Shader 또는 Fragment Shader로 이식한다면 훨씬 동적이고 뛰어난 성능의 시각화를 구현할 수 있습니다.

### 웹 브라우저에서의 시각화 효과
* **실시간 광원 제어:** 사용자가 마우스를 브라우저 화면 위에서 움직이면, 마우스의 $xy$ 좌표가 WebGPU Uniform Buffer를 통해 실시간으로 셰이더의 `light.pos`로 전달됩니다. 사용자는 마우스 이동에 따라 구체 표면의 반짝이는 하이라이트(Specular Highlight)가 실시간으로 부드럽게 궤적을 그리며 이동하는 모습을 관찰할 수 있습니다.
* **실시간 파라미터 조절 GUI:** 웹 페이지에 슬라이더 조절 바를 배치하여 `alpha`(광택도) 값을 1.0에서 100.0까지, `ks` 값을 0.0에서 1.0까지 실시간으로 조절할 수 있습니다. `alpha`가 커질수록 하이라이트 점이 극도로 작고 밝아지며 구체가 점차 크롬 공처럼 단단하고 매끄러운 질감으로 변하는 과정을 GPU 가속을 통해 초당 60프레임 이상으로 즉각 확인하게 됩니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/퐁-반사-모델phong-reflection-model의-스펙큘러-하이라이/demo.html" width="100%" height="700" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
