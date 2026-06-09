# 인터랙티브 데모

학습한 C++/DirectX 11 그래픽스 알고리즘을 JavaScript Canvas로 재구현한 데모입니다.  
슬라이더를 조작해 실시간으로 파라미터를 바꿔볼 수 있습니다.

---

## 픽셀 버퍼 애니메이션

C++에서 `D3D11_MAPPED_SUBRESOURCE`로 CPU→GPU 픽셀 데이터를 전송한 구조를 Canvas `ImageData`로 재현.  
모듈로(%) 연산으로 각 채널에 다른 주기의 색상 파동을 만듭니다.

$$R[x,y,t] = \frac{(x+y+t) \bmod P_R}{P_R} \times 255$$

<div style="border: 1px solid #4c1d95; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="pixel-animation/index.html" width="100%" height="480" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>

---

## CPU 레이트레이서 — Phong 셰이딩 + 그림자

레이-구 교차(Ray-Sphere Intersection)부터 Phong 반사 모델, 그림자 레이까지 구현.  
C++에서 매 프레임 CPU로 픽셀 버퍼를 채운 뒤 GPU 텍스처로 업로드한 패턴과 동일합니다.

$$I = k_a I_a + k_d (\hat{l} \cdot \hat{n}) I_d + k_s (\hat{r} \cdot \hat{v})^\alpha I_s$$

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="raytracer/index.html" width="100%" height="620" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
