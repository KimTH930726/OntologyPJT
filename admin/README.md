# Ontology Admin (React + Vite + TS + Tailwind)

`docs/06-admin-ui.md`의 8화면을 구현한 검수/거버넌스 SPA. 빌드 산출물은
`app/static/admin/`에 들어가서 FastAPI가 `/admin` 경로로 정적 서빙합니다.

## 개발

```bash
cd admin
npm install
npm run dev        # http://localhost:5173 (API는 /documents 등 → :8000으로 proxy)
```

API base URL은 dev에서 vite proxy로, 프로덕션은 same-origin(`/`)을 사용합니다.
필요 시 `VITE_API_BASE=http://other-host:8000`을 빌드 시점에 주입하세요.

## 빌드

```bash
npm run build      # → ../app/static/admin/
```

이후 `uvicorn app.main:app` 으로 띄우면 `http://localhost:8000/admin` 에서 접근.

## 화면 목록

| 경로 | 화면 |
|---|---|
| `/` | 대시보드 (count + 최근 문서/audit) |
| `/documents` | 문서 목록 + 업로드 + 재추출 |
| `/documents/:id` | 문서 상세 (Chunks / Extraction / Audit 탭) |
| `/candidates` | ★ Entity/Relation 후보 검수 (a/r/m 단축키, bulk, modify) |
| `/ontology` | Entity/Relation Type 관리 + 허용 매트릭스 |
| `/graph` | vis-network 기반 subgraph 탐색 + Neo4j sync |
| `/qa` | GraphRAG 질의 테스트 + prompt/evidence/log viewer |
| `/audit` | Audit Log + JSON viewer + export |

## 디자인 결정

- `BrowserRouter basename="/admin"` + 서버측 SPA fallback (deep link 안전)
- TanStack Query: 캐시/리프레시 일관 처리, mutation 후 무효화
- Tailwind v3 + 작은 컴포넌트 토큰 (`.btn-*`, `.card`, `.badge`, `.input`)
- vis-network로 그래프 (D3 직접 작성 대비 양산성 ↑)
- reviewer 이름은 localStorage에 캐시 (모든 review API에 자동 전달)
