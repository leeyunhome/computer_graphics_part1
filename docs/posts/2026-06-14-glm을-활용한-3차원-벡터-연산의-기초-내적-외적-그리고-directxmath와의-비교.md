# GLM을 활용한 3차원 벡터 연산의 기초: 내적, 외적, 그리고 DirectXMath와의 비교

컴퓨터 그래픽스와 레이트레이싱(Ray Tracing)의 근간은 **벡터 수학(Vector Mathematics)**입니다. 화면에 광선을 쏘고, 물체와 충돌하고, 빛의 반사 및 굴절을 계산하는 모든 과정이 벡터 연산으로 표현됩니다. 

이번 커밋에서 학습자는 C++ 환경의 대표적인 그래픽스 수학 라이브러리인 **GLM(OpenGL Mathematics)**을 사용하여 벡터의 기본 연산인 내적(Dot Product)과 외적(Cross Product), 크기 계산 및 정규화(Normalization)를 구현하고 이를 검증했습니다. 또한 고성능 SIMD 연산을 지원하는 **DirectXMath**와의 사용성 비교를 통해 각 라이브러리의 설계 철학을 깊이 있게 이해하고 있습니다.

---

## 1. 핵심 수학적 개념 및 알고리즘

학습자가 코드 내 주석과 출력을 통해 직접 구현하고 검증한 핵심 수학적 개념은 다음과 같습니다.

### (1) 벡터의 크기(Length)와 정규화(Normalization)의 안전성
벡터의 정규화는 방향은 유지한 채 크기를 $1$로 만드는 연산이며, 레이트레이싱에서 광선의 방향(Ray Direction)이나 표면의 법선 벡터(Normal)를 다룰 때 필수적입니다.

$$\|\mathbf{v}\| = \sqrt{v_x^2 + v_y^2 + v_z^2}$$

$$\mathbf{u} = \frac{\mathbf{v}}{\|\mathbf{v}\|}$$

이때, 크기가 $0$에 가까운 벡터(Zero Vector)를 정규화하려고 하면 **Divide-by-Zero** 오류가 발생합니다. 학습자는 이를 방지하기 위한 안전 장치(Safety Guard)의 조건식을 주석으로 제안했습니다.

특히, 제곱근($\sqrt{}$) 연산은 CPU 비용이 크기 때문에, 크기를 직접 비교하는 대신 자기 자신을 내적하여 제곱 크기를 비교하는 최적화 기법을 명시했습니다.
$$\|\mathbf{v}\|^2 = \mathbf{v} \cdot \mathbf{v} < \epsilon$$

---

### (2) 내적(Dot Product)의 기하학적 의미
내적은 두 벡터 사이의 사잇각($\theta$)과 투영(Projection) 관계를 밝히는 데 사용됩니다.

$$\mathbf{a} \cdot \mathbf{b} = a_x b_x + a_y b_y + a_z b_z = \|\mathbf{a}\| \|\mathbf{b}\| \cos\theta$$

*   **직교(Orthogonal) 판별**: 두 벡터가 직교하면 $\cos(90^\circ) = 0$이므로 내적값은 $0$이 됩니다. 학습자는 `dot(vec3(1,0,0), vec3(0,1,0))`의 결과가 $0$임을 확인했습니다.
*   **투영 및 방향성**: 두 단위 벡터의 내적은 한 벡터가 다른 벡터 방향으로 투영된 길이이며, 레이트레이싱에서 빛의 입사각과 표면 법선 벡터 사이의 확산광(Diffuse Light) 세기를 계산(Lambertian Cosine Law)할 때 핵심으로 쓰입니다.

---

### (3) 외적(Cross Product)과 평행사변형 및 삼각형의 넓이
외적은 3차원 공간에서 두 벡터에 동시에 수직인 새로운 벡터(법선 벡터)를 구하는 연산입니다.

$$\mathbf{a} \times \mathbf{b} = \begin{vmatrix} \mathbf{i} & \mathbf{j} & \mathbf{k} \\ a_x & a_y & a_z \\ b_x & b_y & b_z \end{vmatrix}$$

*   **법선 벡터 생성**: 외적의 결과물인 $\mathbf{a} \times \mathbf{b}$는 $\mathbf{a}$와 $\mathbf{b}$가 이루는 평면에 수직입니다.
*   **면적 계산**: 외적 결과 벡터의 크기(Length)는 두 벡터가 이루는 평행사변형의 넓이와 같습니다. 이를 $2$로 나누면 두 벡터로 구성된 삼각형의 넓이가 됩니다.

$$\text{Area}_{\text{parallelogram}} = \|\mathbf{a} \times \mathbf{b}\| = \|\mathbf{a}\| \|\mathbf{b}\| \sin\theta$$

$$\text{Area}_{\text{triangle}} = \frac{1}{2} \|\mathbf{a} \times \mathbf{b}\|$$

학습자는 $\mathbf{a} = (1.5, 0, 0)$, $\mathbf{b} = (0, 2, 0)$의 외적 크기 $\|\mathbf{a} \times \mathbf{b}\| = 3$을 계산해 평행사변형의 넓이를 구하고, 이를 통해 삼각형의 넓이가 $1.5$가 됨을 수학적으로 검증하였습니다.

---

## 2. 라이브러리 추상화: GLM vs DirectXMath

학습자는 동일한 연산(벡터 크기 계산)을 수행하는 두 라이브러리의 인터페이스를 비교 분석하여 각 API의 장단점을 파악했습니다.

### 추상화된 비교 흐름도 (Pseudo-code)

```cpp
// 1. GLM 방식 (직관적, 가독성 중심)
struct GLM_Approach {
    vec3 v = {1.0f, 2.0f, 3.0f};
    float len = length(v); // 단 한 줄로 연산 및 결과 도출
};

// 2. DirectXMath 방식 (성능 중심, SIMD 레지스터 활용)
struct DirectXMath_Approach {
    XMFLOAT4 raw_data = {1.0f, 2.0f, 3.0f, 1.0f};
    
    // CPU 메모리 데이터를 SSE/AVX 레지스터(XMVECTOR)로 로드
    XMVECTOR reg_vector = XMLoadFloat4(&raw_data); 
    
    // SIMD 레지스터 내에서 병렬 연산 수행
    XMVECTOR reg_length = XMVector3Length(reg_vector); 
    
    // 결과를 다시 CPU 메모리(float) 영역으로 언로드
    float len;
    XMStoreFloat(&len, reg_length);
};
```

### 비교 분석
*   **GLM**: GLSL(OpenGL Shading Language) 문법과 거의 일치하도록 설계되어 가독성이 매우 뛰어납니다. 복잡한 메모리 로드/스토어 과정 없이 연산자 오버로딩을 통해 수학 식을 있는 그대로 표현할 수 있어 레이트레이싱 프로토타이핑에 유리합니다.
*   **DirectXMath**: 하드웨어 가속(SIMD: Single Instruction Multiple Data)을 극대화하기 위해 설계되었습니다. 데이터를 연산 전용 128비트 레지스터(`XMVECTOR`)에 적재(`Load`)하고 연산 후 다시 일반 변수로 추출(`Store`)하는 번거로움이 있지만, 대규모 정점(Vertex) 변환 시 압도적인 성능을 보장합니다.

---

## 3. WebGPU 인터랙티브 데모로의 확장 제안

이 커밋에서 다룬 벡터 연산(내적, 외적, 정규화)을 웹 표준 차세대 그래픽스 API인 **WebGPU** 환경에서 시각화한다면 다음과 같은 인터랙티브 데모를 구성할 수 있습니다.

### 1) 데모 컨셉: 실시간 외적 및 노멀 변형 시각화
*   브라우저 화면에 사용자가 마우스로 드래그할 수 있는 두 개의 제어점(벡터 $\mathbf{a}$, $\mathbf{b}$)을 배치합니다.
*   **WebGPU Compute Shader**가 GPU 상에서 실시간으로 두 벡터의 내적과 외적을 계산합니다.

### 2) WGSL(WebGPU Shading Language) 구현 아이디어
GPU 버퍼에 담긴 두 벡터 정보를 바탕으로 Compute Shader가 연산을 수행하고 결과를 렌더링 파이프라인으로 전달합니다.

```wgsl
// WGSL Compute Shader 예시
struct VectorData {
    vectorA : vec3<f32>,
    vectorB : vec3<f32>,
}

struct OutputData {
    dotProduct : f32,
    crossProduct : vec3<f32>,
    area : f32,
}

@group(0) @binding(0) var<storage, read> input : VectorData;
@group(0) @binding(1) var<storage, read_write> output : OutputData;

@compute @workgroup_size(1)
fn main() {
    let a = input.vectorA;
    let b = input.vectorB;

    // 내적 계산
    output.dotProduct = dot(a, b);

    // 외적 계산
    let crossResult = cross(a, b);
    output.crossProduct = crossResult;

    // 외적의 크기를 통한 평행사변형 넓이 계산
    output.area = length(crossResult);
}
```

### 3) 웹 화면 시각화 구성
*   **3D 기하학적 표현**: 화면 중심에서 뻗어나가는 빨간색 화살표($\mathbf{a}$)와 초록색 화살표($\mathbf{b}$)를 그립니다.
*   **법선 벡터 실시간 렌더링**: 파란색 화살표로 외적 결과($\mathbf{a} \times \mathbf{b}$)를 표시하여 두 벡터에 항상 직교함을 시각적으로 보여줍니다.
*   **면적의 시각화**: 두 벡터 사이를 채우는 반투명한 사각형(평행사변형) 또는 삼각형 패치를 그리고, 마우스 움직임에 따라 면적 수치(Compute Shader에서 연산된 `area`)가 텍스트와 면적 크기로 동기화되어 변화하는 모습을 구현합니다.
*   이 데모는 3D 공간에서 평면의 앞/뒤면 판별(Back-face Culling)과 표면 법선 벡터가 빛을 받아 음영이 생기는 원리를 학습자가 직관적으로 이해하도록 돕습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/glm을-활용한-3차원-벡터-연산의-기초-내적-외적-그리고-directx/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
