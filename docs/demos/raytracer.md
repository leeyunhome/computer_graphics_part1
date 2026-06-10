# CPU 레이트레이서 — Phong 셰이딩 + 그림자

레이-구 교차(Ray-Sphere Intersection)부터 Phong 반사 모델, 그림자 레이까지 구현.  
C++에서 매 프레임 CPU로 픽셀 버퍼를 채운 뒤 GPU 텍스처로 업로드한 패턴과 동일합니다.

$$I = k_a I_a + k_d (\hat{l} \cdot \hat{n}) I_d + k_s (\hat{r} \cdot \hat{v})^\alpha I_s$$

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>

## 핵심 개념

### 레이-구 교차 (Ray-Sphere Intersection)

레이 $\mathbf{r}(t) = \mathbf{o} + t\mathbf{d}$ 와 구 $|\mathbf{p} - \mathbf{c}|^2 = r^2$ 의 교차:

$$t = -(\mathbf{d} \cdot \mathbf{oc}) \pm \sqrt{(\mathbf{d} \cdot \mathbf{oc})^2 - (|\mathbf{oc}|^2 - r^2)}$$

판별식(discriminant)이 0 이상일 때만 교차점이 존재합니다.

### Phong 반사 모델

| 항 | 의미 |
|---|---|
| $k_a I_a$ | 주변광(Ambient) — 전역 조명 근사 |
| $k_d (\hat{l} \cdot \hat{n}) I_d$ | 난반사(Diffuse) — 면의 기울기에 비례 |
| $k_s (\hat{r} \cdot \hat{v})^\alpha I_s$ | 정반사(Specular) — 광택 하이라이트 |

### 그림자 레이 (Shadow Ray)

교차점에서 광원 방향으로 새 레이를 쏘아 다른 물체와의 교차 여부로 그림자 판정.
