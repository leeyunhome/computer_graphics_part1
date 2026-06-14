# GLM을 활용한 벡터 연산의 수학적 이해 및 DirectXMath와의 비교 분석

우선 기초 그래픽스 및 레이트레이싱의 핵심 초석이 되는 **벡터 연산(Vector Operations)** 단계를 성공적으로 구현하고 커밋한 것을 축하합니다. 3차원 그래픽스에서 모든 정점의 변환, 광선(Ray)의 생성, 조명 연산은 결국 벡터 수학으로 귀결됩니다. 

이번 커밋은 단순히 라이브러리 사용법을 익히는 것을 넘어, 그래픽스 API에서 벡터가 기하학적으로 어떻게 해석되고 활용되는지 핵심적인 개념들을 잘 짚어내고 있습니다. 학습한 내용을 바탕으로 수학적 의미와 코드의 구조적 특징을 분석해 드립니다.

---

## 1. 핵심 기하학적 개념 및 수학적 공식

이 커밋에서 학습자가 다룬 가장 중요한 기하학적 개념은 **벡터의 크기(Magnitude), 내적(Dot Product), 그리고 외적(Cross Product)**입니다.

### ① 벡터의 길이 및 안전한 정규화 (Normalization)
벡터 $\mathbf{v} = (x, y, z)$의 길이(L2 Norm)는 피타고라스 정리에 의해 다음과 같이 정의됩니다.

$$||\mathbf{v}|| = \sqrt{x^2 + y^2 + z^2}$$

방향만을 나타내는 **유닛 벡터(Unit Vector)**를 만들기 위해 벡터를 자신의 길이로 나누는 정규화 과정을 거칩니다. 이때 수학적으로 **길이가 0인 벡터(Zero Vector)**를 나누면 $0$으로 나누기 오류(Divide by Zero)가 발생하여 프로그램이 크래시되거나 `NaN`(Not a Number) 값이 발생합니다.

이를 방지하기 위해 학습자는 수치적 안정성(Numerical Stability)을 확보하는 안전 장치(Safeguard)를 주석으로 고려했습니다. 특히, 제곱근($\sqrt{}$) 연산은 컴퓨터에게 비용이 많이 드는 연산이므로, 내적을 활용해 제곱 길이를 먼저 비교하는 최적화 기법을 제안한 점이 매우 훌륭합니다.

$$\mathbf{v} \cdot \mathbf{v} = ||\mathbf{v}||^2 < \epsilon \quad (\text{where } \epsilon \approx 10^{-16})$$

---

### ② 내적 (Dot Product)의 수학적 의미
두 벡터 $\mathbf{a}$와 $\mathbf{b}$의 내적은 각 성분의 곱의 합으로 표현되며, 기하학적으로는 두 벡터가 이루는 각도 $\theta$와 관련이 있습니다.

$$\mathbf{a} \cdot \mathbf{b} = a_x b_x + a_y b_y + a_z b_z = ||\mathbf{a}|| ||\mathbf{b}|| \cos\theta$$

*   **직교 판별**: 두 벡터가 서로 직교할 때($\theta = 90^\circ$), $\cos 90^\circ = 0$이므로 내적값은 $0$이 됩니다. 학습자의 코드에서 `dot(vec3(1,0,0), vec3(0,1,0))`의 결과가 `0`이 나오는 것을 통해 이를 검증했습니다.
*   **투영 (Projection) 및 조명 연산**: 광선과 표면 법선 벡터(Normal) 사이의 각도를 구해 빛의 세기를 결정하는 Lambertian Reflection 모델의 기초가 됩니다.

---

### ③ 외적 (Cross Product)과 평행사변형/삼각형의 넓이
외적은 3차원 공간에서만 정의되는 연산으로, 두 벡터 $\mathbf{a}$와 $\mathbf{b}$에 동시에 수직인 새로운 벡터를 생성합니다.

$$\mathbf{a} \times \mathbf{b} = (a_y b_z - a_z b_y, \ a_z b_x - a_x b_z, \ a_x b_y - a_y b_x)$$

*   **법선 벡터(Normal Vector) 생성**: 두 벡터가 평행하지 않다면, 외적의 결과는 두 벡터가 이루는 평면의 법선 방향이 됩니다. (이때 결과 벡터의 방향은 오른손 법칙을 따릅니다.)
*   **면적 계산**: 외적 결과 벡터의 크기 $||\mathbf{a} \times \mathbf{b}||$는 두 벡터 $\mathbf{a}, \mathbf{b}$를 이웃한 두 변으로 하는 **평행사변형의 넓이**와 같습니다.

$$\text{Area}_{\text{parallelogram}} = ||\mathbf{a} \times \mathbf{b}|| = ||\mathbf{a}|| ||\mathbf{b}|| \sin\theta$$

따라서, 이 평행사변형을 절반으로 나눈 **삼각형의 넓이**는 다음과 같이 계산됩니다.

$$\text{Area}_{\text{triangle}} = \frac{1}{2} ||\mathbf{a} \times \mathbf{b}||$$

학습자는 구체적인 수치인 $\mathbf{a} = (1.5, 0, 0)$, $\mathbf{b} = (0, 2, 0)$을 대입하여 외적 결과가 $(0, 0, 3)$이 되고, 이 크기(평행사변형 넓이)가 $3.0$, 따라서 삼각형의 넓이가 $1.5$가 됨을 완벽하게 검증하였습니다.

---

## 2. 추상화된 핵심 알고리즘 (Pseudo-code)

학습자가 C++ 코드 내부에서 다룬 연산 흐름을 컴퓨터 그래픽스 파이프라인에서 범용적으로 사용하는 형태로 추상화하면 다음과 같습니다. 이 알고리즘은 레이트레이싱에서 삼각형 메시(Triangle Mesh)의 충돌 검사 및 충돌 지점의 법선 벡터를 구할 때 기초 공식이 됩니다.

```text
// 정점 3개로 구성된 삼각형 정보로부터 법선 벡터와 넓이를 계산하는 함수
function CalculateTriangleProperties(Vertex v0, Vertex v1, Vertex v2):
    // 1. 두 개의 변(Edge) 벡터 계산
    Vector3 edge1 = v1.position - v0.position
    Vector3 edge2 = v2.position - v0.position
    
    // 2. 외적(Cross Product)을 통한 평면의 수직 벡터 계산
    Vector3 crossProduct = Cross(edge1, edge2)
    
    // 3. 외적 결과물의 길이를 통한 면적 계산
    float parallelogramArea = Length(crossProduct)
    float triangleArea = parallelogramArea * 0.5
    
    // 4. 안전한 정규화(Safe Normalization)를 통한 단위 법선 벡터 생성
    Vector3 normal
    float squaredLength = Dot(crossProduct, crossProduct)
    
    if squaredLength > 1e-8:
        normal = crossProduct / sqrt(squaredLength)
    else:
        normal = Vector3(0, 0, 0) // degenerate triangle 처리
        
    return normal, triangleArea
```

---

## 3. 라이브러리 비교 관점: GLM vs DirectXMath

학습자는 코드 내에서 DirectXMath와 GLM의 가독성 차이를 명확히 체감하고 주석으로 남겼습니다. 이 둘의 구조적 차이를 그래픽스 전문가 입장에서 보완 설명해 드립니다.

### GLM (OpenGL Mathematics)
*   **설계 철학**: GLSL(OpenGL Shading Language) 명세와 거의 1:1 대응되도록 설계되었습니다.
*   **가독성**: C++ 연산자 오버로딩이 적극적으로 활용되어 복잡한 식도 수학 공식과 거의 유사하게 작성할 수 있어 가독성이 압도적으로 높습니다 (`u = (b - a) / length(b - a)`).
*   **다목적 데이터 바인딩**: `vec3` 객체 하나로 위치/방향(`.x, .y, .z`), 색상(`.r, .g, .b`), 배열 형태(`.operator[]`)로 모두 접근 가능한 편의성을 제공합니다.

### DirectXMath
*   **설계 철학**: 하드웨어 가속(SIMD - Single Instruction Multiple Data, SSE/AVX/NEON)을 극대화하도록 설계되었습니다.
*   **데이터 타입 분리**: CPU 연산 및 메모리 저장에 적합한 데이터 타입(`XMFLOAT3`, `XMFLOAT4`)과 실제 CPU 레지스터(SIMD 레지스터)에 직접 매핑되어 병렬 계산을 수행하는 데이터 타입(`XMVECTOR`)을 엄격히 분리합니다.
*   **복잡한 로드/스토어**: 연산을 위해 `XMLoadFloat4()`를 통해 메모리에서 레지스터로 데이터를 가져오고, 연산이 끝난 후 다시 `XMStoreFloat()`로 저장해야 하는 무거운 문법적 오버헤드가 존재합니다. 대신 하드웨어 레벨의 병렬 연산 속도가 보장됩니다.

---

## 4. WebGPU 인터랙티브 데모로의 확장 시각화

이 학습 내용을 브라우저의 차세대 그래픽 API인 **WebGPU**의 **Compute Shader**로 시각화한다면 다음과 같이 흥미로운 인터랙티브 데모를 구성할 수 있습니다.

```
       [ WebGPU CPU Side (TypeScript) ]
  - 삼각형의 세 정점 위치 데이터를 버퍼에 저장
  - 마우스 드래그를 통해 정점(v1, v2) 실시간 이동
                 │
                 ▼ (GPU Buffer 전송)
       [ WebGPU Compute Shader (WGSL) ]
  - 각 GPU 스레드가 삼각형 1개씩 할당받아 연산
  - WGSL 내장 함수 cross(), length(), normalize() 활용
                 │
                 ▼ (결과물 렌더링)
       [ HTML5 Canvas 실시간 시각화 ]
  - 외적으로 계산된 Normal 벡터 방향에 따라 화살표 드로잉
  - 계산된 삼각형 넓이 수치(예: 1.5)를 화면에 텍스트 표시
  - 실시간으로 넓이가 변할 때마다 색상 변화 (넓을수록 Red, 좁을수록 Blue)
```

### 데모 연출 방식
1.  **실시간 인터랙션**: 브라우저 화면 상에서 사용자가 마우스로 삼각형의 정점을 클릭해 드래그할 수 있습니다.
2.  **외적과 넓이의 시각화**: 두 변이 이루는 평행사변형 영역을 반투명한 사각형 격자 모양으로 그리드 표시하고, 삼각형 영역은 다른 색상으로 채웁니다. 정점을 움직여 사잇각이나 변의 길이를 늘리면, 외적 결과 벡터의 길이를 나타내는 3D 화살표가 실시간으로 길어지거나 짧아집니다.
3.  **성능 이점**: 이 연산을 WebGPU Compute Shader(`WGSL`) 내부에서 처리하면, CPU의 간섭 없이 수백만 개의 삼각형 면적과 법선 벡터를 단 1ms(밀리초) 만에 계산하여 실시간 물리 시뮬레이션(예: 천 시뮬레이션의 표면 압력 연산 등)에 즉각 활용할 수 있습니다.

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="../../demos/glm을-활용한-벡터-연산의-수학적-이해-및-directxmath와의-비/demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
