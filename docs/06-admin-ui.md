# 6. Admin UI 화면 설계

> React + Vite + Tailwind. 좌측 nav, 상단 status bar. MVP는 desktop 한정.

## 6.1 화면 IA

```
/                       대시보드 (count: docs, pending, approved, queries today)
/documents              문서 목록
/documents/:id          문서 상세 + chunk 목록
/candidates             추출 후보 검수 (entity + relation)
/ontology               Ontology Schema 관리
/graph                  Graph 미리보기 / 탐색
/qa                     질의 테스트
/audit                  Audit Log
```

## 6.2 문서 목록 `/documents`

- Columns: `title | domain | version | chunks | pending | approved | uploaded_at | actions`
- Actions: 상세, 재추출, 삭제
- 상단: "문서 업로드" 버튼 (모달, title/domain/text or file)

## 6.3 문서 상세 `/documents/:id`

- 헤더: 메타 정보 (title, domain, version, access_level, uri)
- 탭: `Chunks` / `Extraction Status` / `Audit`
- Chunks: 좌측 목록(seq, token, status), 우측 원문 패널
- 각 chunk 행에서 → "이 chunk 검수하러 가기" 링크 → `/candidates?chunk_id=...`

## 6.4 추출 후보 검수 `/candidates` ★핵심

```
+--------------------------------------------------+
|  필터: status | type | document | chunk          |
+--------------------+-----------------------------+
| (좌) Chunk 원문    | (우) Entity 후보 카드들     |
|                    |  [name][type][confidence]   |
|                    |  approve / reject / modify  |
|                    |---------------------------- |
|                    | Relation 후보 (src→tgt)     |
|                    | 빨강: 양쪽 entity 미승인    |
|                    | 회색: 스키마 위반(자동 reject)|
+--------------------+-----------------------------+
| 하단: 일괄 선택 → bulk approve/reject            |
+--------------------------------------------------+
```

Key UX:
- Relation은 양쪽 source/target entity가 APPROVED일 때만 approve 활성화
- "Merge" 액션: 동일 normalized_name 후보 병합
- 키보드 단축키: `a` approve, `r` reject, `m` modify

## 6.5 Ontology Schema 관리 `/ontology`

- 탭1 **Entity Types**: 테이블 + 추가/비활성
- 탭2 **Relation Types**: `code | source_type | target_type | description | active`
  - 추가 폼: dropdown으로 source/target 선택 (불일치 방지)
- 우측 패널: "허용 관계 매트릭스" 시각화

```
        Order  OrderItem  Payment  Condition
Policy    ✓                ✓          ✓(REQ)
Order            ✓         ✓
Refund                     ✓
```

## 6.6 Graph 미리보기 `/graph`

- 좌측: 검색 (normalized_name autocomplete) / depth slider (1~3) / type 필터
- 중앙: D3 또는 vis-network 그래프 캔버스
- 우측 패널: 노드 클릭 시 properties + `DEFINED_IN` chunk 원문 미리보기
- 토글: "Pending도 함께 표시 (점선)" - 승인 시 어떻게 될지 미리보기

## 6.7 질의 테스트 `/qa`

```
[질문 입력]
[옵션] top_k_chunks / graph_depth / template

→ [Answer]
→ [Graph Context]  (subgraph 시각)
→ [Document Evidence] (chunk 카드 + 하이라이트)
→ [Rendered Prompt] (collapsible)
→ [Stats] latency / tokens / model
```

## 6.8 Audit Log `/audit`

- 필터: event_type (`DOC_UPLOAD / REVIEW_APPROVE / SCHEMA_CHANGE / QUERY ...`), 기간, actor
- Row 클릭 시 payload JSON viewer
- "Export CSV" (MVP optional)

## 6.9 컴포넌트 재사용 목록

- `<ChunkViewer>` 원문 + highlight span
- `<EntityCard>` / `<RelationCard>`
- `<ReviewActions>` approve/reject/modify/merge 버튼셋
- `<GraphCanvas>` 노드/엣지 렌더링
- `<JsonViewer>` payload 표시
- `<StatusBadge>` review_status / vector_status

## 6.10 와이어프레임 (텍스트)

`/candidates` 화면 와이어:

```
┌─ Header: 검수 ────────────────────────────────────────────┐
│ Filter: [status ▼ PENDING] [type ▼ all] [doc ▼ 환불정책v1] │
├──────────────────────────────┬────────────────────────────┤
│ Chunk #003                   │ Entities (3)               │
│ "결제 완료 후 배송 시작 전에는│ ┌────────────────────────┐ │
│  주문 전체 취소가 가능하다..."│ │ FullCancelPolicy       │ │
│                              │ │ type=Policy  conf=0.91 │ │
│                              │ │ [a] [r] [m]            │ │
│                              │ └────────────────────────┘ │
│                              │ ...                        │
│                              │ Relations (3)              │
│                              │ FullCancelPolicy           │
│                              │   --REQUIRES-->            │
│                              │   PaymentCompleted   0.90  │
│                              │ [a disabled until entities]│
└──────────────────────────────┴────────────────────────────┘
```
