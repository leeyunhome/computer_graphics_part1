# 픽셀 버퍼 애니메이션

C++에서 `D3D11_MAPPED_SUBRESOURCE`로 CPU→GPU 픽셀 데이터를 전송한 구조를 Canvas `ImageData`로 재현.  
모듈로(%) 연산으로 각 채널에 다른 주기의 색상 파동을 만듭니다.

$$R[x,y,t] = \frac{(x+y+t) \bmod P_R}{P_R} \times 255$$

<div style="border: 1px solid #4c1d95; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="demo.html" width="100%" height="500" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>

## 핵심 개념

- **픽셀 버퍼**: 매 프레임 CPU에서 픽셀 색상을 계산해 Canvas에 직접 쓰기
- **모듈로 연산**: `(x + y + t) % period` 로 대각선 방향으로 흐르는 색상 파동 생성
- **채널 독립 주기**: R·G·B 각각 다른 주기 → 복잡한 색상 변화

## C++ → JavaScript 대응

| C++ / DX11 | JavaScript |
|---|---|
| `D3D11_MAPPED_SUBRESOURCE` | `canvas.getContext('2d').createImageData()` |
| `memcpy`로 픽셀 버퍼 업로드 | `ctx.putImageData(imgData, 0, 0)` |
| `Present()` 호출 | `requestAnimationFrame()` |
