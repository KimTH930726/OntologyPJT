# 5. REST API 설계

> Base: `/api/v1`. 인증은 MVP에서 `X-Admin-Token` 헤더 단일 토큰.
> 응답 공통: `{ "data": ..., "meta": {...} }`. 에러: `{ "error": { "code", "message", "detail" } }`.

## 5.1 문서

| Method | Path | 설명 |
|---|---|---|
| POST | `/documents` | 문서 업로드 (multipart 또는 JSON `{title, domain, text}`) |
| GET | `/documents` | 목록 (page, domain 필터) |
| GET | `/documents/{id}` | 상세 + 메타 |
| GET | `/documents/{id}/chunks` | chunk 목록 |
| POST | `/documents/{id}/reextract` | 강제 재-Chunk & 재추출 트리거 |
| DELETE | `/documents/{id}` | (CASCADE) staging까지 삭제 |

**POST /documents (JSON)**
```json
{ "title": "환불 정책 v1", "domain": "ecommerce", "text": "결제 완료 후 ..." }
```
응답:
```json
{ "data": { "id": "uuid", "version": 1, "chunk_count": 7, "status": "INDEXING" } }
```

## 5.2 Chunk

| Method | Path | 설명 |
|---|---|---|
| GET | `/chunks/{id}` | 원문 + meta |
| GET | `/chunks/{id}/candidates` | 해당 chunk에서 추출된 entity/relation 후보 묶음 |

## 5.3 Ontology Schema

| Method | Path | 설명 |
|---|---|---|
| GET | `/ontology/entity-types` | 활성 entity type 목록 |
| POST | `/ontology/entity-types` | 생성 |
| PATCH | `/ontology/entity-types/{code}` | 수정/비활성 |
| GET | `/ontology/relation-types` | 활성 relation type 목록 |
| POST | `/ontology/relation-types` | `{code, source_type, target_type, description}` |
| PATCH | `/ontology/relation-types/{code}` | 비활성 |

## 5.4 추출 후보 (Staging)

| Method | Path | 설명 |
|---|---|---|
| GET | `/candidates/entities` | `?status=PENDING&document_id=&chunk_id=` |
| GET | `/candidates/entities/{id}` | 단건 |
| POST | `/candidates/entities/{id}/approve` | `{reviewer}` |
| POST | `/candidates/entities/{id}/reject` | `{reviewer, reason}` |
| POST | `/candidates/entities/{id}/modify` | `{reviewer, name?, normalized_name?, type_code?}` |
| POST | `/candidates/entities/{id}/merge` | `{reviewer, into_id}` |
| GET | `/candidates/relations` | 동일 패턴 |
| POST | `/candidates/relations/{id}/approve` | source/target가 모두 APPROVED여야 200, 아니면 409 |
| POST | `/candidates/relations/{id}/reject` | |
| POST | `/candidates/relations/{id}/modify` | |

**Approve 응답 예**
```json
{
  "data": {
    "id": "uuid", "status": "APPROVED",
    "sync": { "scheduled": true, "log_id": "uuid" }
  }
}
```

## 5.5 Graph 반영 / 조회

| Method | Path | 설명 |
|---|---|---|
| POST | `/graph/sync` | 대기 중인 APPROVED 일괄 적재 |
| GET | `/graph/sync-logs` | 적재 이력 |
| GET | `/graph/entities/{normalized_name}` | 노드 + 1-hop 이웃 |
| GET | `/graph/subgraph` | `?seed=Policy&depth=2&types=Policy,Condition,Order` |
| POST | `/graph/cypher` | (admin only) raw Cypher 실행 |

## 5.6 질문 응답

| Method | Path | 설명 |
|---|---|---|
| POST | `/qa` | 질문 응답 (GraphRAG) |

**Request**
```json
{
  "question": "주문 O1001은 환불 가능한가?",
  "options": { "top_k_chunks": 5, "graph_depth": 2, "prompt_template": "qa_default" }
}
```

**Response**
```json
{
  "data": {
    "answer": "결론: 가능합니다. 단, ...",
    "evidence": {
      "graph": [
        {"source":"FullCancelPolicy","relation":"REQUIRES","target":"PaymentCompleted"},
        {"source":"FullCancelPolicy","relation":"REQUIRES","target":"DeliveryNotStarted"}
      ],
      "chunks": [
        {"chunk_id":"...","document_id":"...","text":"결제 완료 후..."}
      ]
    },
    "trace_id": "uuid"
  }
}
```

## 5.7 Audit / Logs

| Method | Path | 설명 |
|---|---|---|
| GET | `/audit` | `?event_type=&from=&to=` |
| GET | `/qa/logs` | 질의 audit 목록 |
| GET | `/qa/logs/{id}` | 단건 (prompt/answer 전체) |

## 5.8 OpenAPI 운영 규칙

- FastAPI 자동 OpenAPI: `/docs`, `/redoc`.
- 모든 4xx는 `error.code` 키 (`VALIDATION_ERROR`, `SCHEMA_VIOLATION`, `NOT_APPROVED_SOURCE` 등) 부여.
- `POST /qa`는 idempotent 아님. `trace_id`로 audit 추적.
