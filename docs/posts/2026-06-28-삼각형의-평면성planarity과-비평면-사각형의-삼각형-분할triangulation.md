# 삼각형의 평면성(Planarity)과 비평면 사각형의 삼각형 분할(Triangulation)

우리가 3차원 공간을 정의하고 이를 화면에 렌더링할 때, 가장 기본이 되는 기하학적 단위는 단연 **삼각형(Triangle)**입니다. 이번 커밋은 그래픽스 파이프라인과 레이트레이싱에서 삼각형이 왜 만능의 기본 단위(Primitive)로 사용되는지, 그리고 4개 이상의 정점을 가진 다각형이 가질 수 있는 치명적인 한계인 **비평면성(Non-planarity)**을 어떻게 해결하는지에 대한 수학적·기하학적 고찰을 담고 있습니다.

---

## 1. 핵심 개념: 왜 삼각형인가? (Triangle Planarity)

3차원 공간에서 세 점은 언제나 단 하나의 평면을 정의합니다. 이를 **삼각형의 평면성(Triangle Planarity)**이라고 합니다. 

### 수학적 정의
공간 상의 서로 다른 세 정점 $\mathbf{v}_0, \mathbf{v}_1, \mathbf{v}_2$가 일직선상에 있지 않다면, 이 세 점을 지나는 평면의 법선 벡터(Normal Vector) $\mathbf{n}$은 외적(Cross Product)을 통해 다음과 같이 유일하게 결정됩니다.

$$\mathbf{e}_1 = \mathbf{v}_1 - \mathbf{v}_0$$
$$\mathbf{e}_2 = \mathbf{v}_2 - \mathbf{v}_0$$
$$\mathbf{n} = \mathbf{e}_1 \times \mathbf{e}_2$$

이렇게 구해진 법선 벡터 $\mathbf{n}$과 평면 위의 한 점 $\mathbf{v}_0$를 이용하면, 평면 위의 임의의 점 $\mathbf{p}$가 만족해야 하는 평면의 방정식을 정의할 수 있습니다.

$$(\mathbf{p} - \mathbf{v}_0) \cdot \mathbf{n} = 0$$

삼각형의 세 점은 항상 이 식을 완벽하게 만족하므로, 어떠한 방식으로 3차원 공간에서 회전하거나 변형되어도 평평한(Planar) 상태를 유지합니다.

---

## 2. 사각형의 한계: 비평면성과 뒤틀림 (Non-planar Quadrilaterals & Folding)

반면, 4개의 정점 $\mathbf{v}_0, \mathbf{v}_1, \mathbf{v}_2, \mathbf{v}_3$으로 구성된 사각형(Quad)은 항상 평평하다는 보장이 없습니다. 

예를 들어, 평평한 종이의 한쪽 모서리를 접는 상황(Folding)을 생각해 봅시다. 한 정점 $\mathbf{v}_3$가 다른 세 점이 이루는 평면의 방정식 $(\mathbf{p} - \mathbf{v}_0) \cdot \mathbf{n} = 0$을 만족하지 못하고 붕 뜨게 된다면, 이 사각형은 더 이상 하나의 평면으로 표현할 수 없는 **비평면 사각형(Non-planar Quadrilateral)**이 됩니다.

### 레이트레이싱에서의 문제점
레이트레이싱(Raytracing)에서 광선과 도형의 교차 판정(Ray-Object Intersection)을 수행할 때, 도형이 평평하지 않으면 수학적 정의가 모호해집니다. 단일 법선 벡터를 정의할 수 없기 때문에 광선이 사각형과 만나는 정확한 교차점과 그 지점에서의 반사광을 계산하기가 매우 까다로워집니다. 이는 결국 **퐁 반사 모델(Phong Reflection Model)**을 적용할 때 입사각과 반사각 계산의 왜곡을 야기하여, 화면에 어색한 그림자나 아티팩트(Artifact)를 발생시키는 원인이 됩니다.

---

## 3. 해결책: 삼각형 분할 (Triangulation)

이 문제를 해결하는 가장 확실하고 단순한 방법은 모든 다각형을 삼각형 단위로 쪼개는 **삼각형 분할(Triangulation)**입니다. 비평면 사각형은 대각선을 기준으로 두 개의 삼각형으로 분할하면, 각각의 삼각형은 언제나 완벽한 평평함을 유지하게 됩니다.

### 추상화된 분할 알고리즘 (Pseudo-code)

비평면 사각형 $Q(\mathbf{v}_0, \mathbf{v}_1, \mathbf{v}_2, \mathbf{v}_3)$가 주어졌을 때, 이를 두 개의 삼각형 $T_1, T_2$로 안전하게 분할하여 레이트레이싱 파이프라인에 전달하는 과정은 다음과 같이 추상화할 수 있습니다.

```cpp
struct Quad {
    Vector3 v0, v1, v2, v3;
};

struct Triangle {
    Vector3 p0, p1, p2;
};

// 사각형을 2개의 평면 삼각형으로 분할하는 함수
std::pair<Triangle, Triangle> TriangulateQuad(const Quad& quad) {
    Triangle t1;
    t1.p0 = quad.v0;
    t1.p1 = quad.v1;
    t1.p2 = quad.v2; // 첫 번째 삼각형 (v0, v1, v2)

    Triangle t2;
    t2.p0 = quad.v0;
    t2.p1 = quad.v2;
    t2.p2 = quad.v3; // 두 번째 삼각형 (v0, v2, v3)

    return {t1, t2};
}

// 레이트레이싱 루프에서의 적용
bool IntersectQuad(const Ray& ray, const Quad& quad, HitRecord& record) {
    auto [t1, t2] = TriangulateQuad(quad);
    
    // 두 삼각형 각각에 대해 평면 교차 판정을 수행
    bool hit = IntersectTriangle(ray, t1, record);
    hit |= IntersectTriangle(ray, t2, record); 
    
    return hit;
}
```

이 분할을 통해 복잡한 비평면 기하구조도 고유의 법선 벡터를 가진 단순한 평면 삼각형들의 집합으로 환원되므로, 일관성 있는 **퐁 반사 모델(Phong Reflection Model)** 기반의 광원 연산이 가능해집니다.

---

## 4. WebGPU 인터랙티브 데모 제안: 비평면 사각형의 시각화

이 기하학적 개념을 웹 브라우저에서 실시간으로 시각화하기 위해, **WebGPU Compute Shader**와 렌더링 파이프라인을 활용한 인터랙티브 데모를 다음과 같이 구성할 수 있습니다.

```
[ WebGPU Interactive Canvas ]
+----------------------------------------+
|   (v3) *-----> 조절용 기즈모(Drag)      |  <- 마우스로 v3를 위아래로 움직임
|       / \                              |
|      /   \  Triangulated Edge (v0-v2)  |  <- 접히는 경계선 시각화
|     /     \                            |
| (v0)*------* (v2)                      |
|     \      /                           |
|      \    /                            |
|       \  /                             |
|        * (v1)                          |
+----------------------------------------+
* 실시간 퐁 반사 모델(Phong Reflection Model) 적용:
  접힌 양쪽 삼각형의 밝기가 서로 다르게 표현되어 평면의 깨짐을 시각적으로 인지 가능.
```

### 데모 구현 핵심 요약
1. **정점 버퍼 제어 (Vertex Buffer Manipulation)**: 
   - 화면에 4개의 정점(Quad)을 배치하고, 사용자가 UI 슬라이더나 마우스 드래그를 통해 하나의 정점(예: $\mathbf{v}_3$)의 Z축 값을 실시간으로 변화시킬 수 있도록 합니다.
2. **Compute/Render Shader 내 동적 분할**:
   - WebGPU의 셰이더(WGSL) 단계에서 해당 Quad를 실시간으로 2개의 삼각형(`Triangle 1: v0-v1-v2`, `Triangle 2: v0-v2-v3`)으로 분할합니다.
3. **법선 벡터 변화 및 조명 시각화**:
   - 두 삼각형의 개별 법선 벡터 $\mathbf{n}_1, \mathbf{n}_2$를 실시간으로 계산하여 화면에 가느다란 화살표(Vector)로 시각화합니다.
   - 평평할 때는 두 법선 벡터가 완벽히 일치하지만, 정점을 움직여 '접히는(Folding)' 순간 법선 벡터가 서로 다른 방향으로 갈라지는 모습을 보여줍니다.
   - 여기에 **퐁 반사 모델(Phong Reflection Model)**을 적용하여 광원의 위치에 따라 접힌 경계선(Diagonal Edge)을 경계로 명암이 급격하게 갈라지는 현상을 실시간으로 렌더링합니다.

이 데모는 학습자가 구현한 삼각형 분할 공식이 실제 3D 그래픽스 렌더러에서 빛의 반사와 섀이딩에 얼마나 즉각적이고 결정적인 영향을 미치는지 직관적으로 이해할 수 있도록 돕는 훌륭한 도구가 될 것입니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/삼각형의-평면성planarity과-비평면-사각형의-삼각형-분할triang/demo.html" width="100%" height="700" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
