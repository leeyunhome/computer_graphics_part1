# 인터랙티브 데모

학습한 C++/DirectX 11 그래픽스 알고리즘을 JavaScript Canvas로 재구현한 데모입니다.  
슬라이더를 조작해 실시간으로 파라미터를 바꿔볼 수 있습니다.

---

## [🎨 픽셀 버퍼 애니메이션](pixel-animation.md)

CPU 픽셀 쓰기 · 모듈로 색상 파동 · `ImageData` 직접 조작

$$R[x,y,t] = \frac{(x+y+t) \bmod P_R}{P_R} \times 255$$

[→ 데모 열기](pixel-animation.md)

---

## [🔮 CPU 레이트레이서](raytracer.md)

레이-구 교차 · Phong 셰이딩 · 그림자 레이

$$I = k_a I_a + k_d (\hat{l} \cdot \hat{n}) I_d + k_s (\hat{r} \cdot \hat{v})^\alpha I_s$$

[→ 데모 열기](raytracer.md)
