# 사용 가이드 (E2E Walkthrough)

> 문서 등록부터 GraphRAG 질의·Audit 확인까지, 한 번에 따라가는 60초 데모.
> 아키텍처/원칙은 [README](../README.md)와 [docs/01-architecture.md](01-architecture.md) 참고.

---

## 0. 사전 준비

```bash
cp .env.example .env
docker compose up --build -d
```

4개 컨테이너(`postgres`, `neo4j`, `qdrant`, `app`)가 healthy 상태가 되면 다음으로.

```bash
docker compose exec app alembic upgrade head        # 0001~0006 일괄 적용
docker compose exec app python -m app.seeds.ontology_seed   # 9 Entity + 6 Relation
docker compose exec app python -m app.seeds.prompt_seed     # qa_default v1
curl http://localhost:8000/health
```

`/health` 가 `{"status":"ok","services":{"postgres":"ok","neo4j":"ok","qdrant":"ok"},"errors":{}}` 반환하면 준비 완료.

Neo4j 제약/인덱스(`entity_id_unique`, `chunk_id_unique` 등)는 앱 부팅 시 lifespan에서 자동 ensure.

---

## 1. 문서 등록 → Chunk → Vector

```bash
curl -X POST http://localhost:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"환불 정책 v1","domain":"order","source_type":"policy",
    "version":"v1","access_level":"internal",
    "content":"결제 완료 후 배송 시작 전에는 주문 전체 취소가 가능하다. 부분 취소는 주문상품 단위로만 가능하다. 환불 금액은 실제 결제 금액을 초과할 수 없다."
  }'
```

응답:
```json
{ "document_id": "...", "chunk_count": 3, "vector_status": "INDEXED" }
```

확인:
```bash
curl http://localhost:8000/documents/{document_id}/chunks
curl http://localhost:8000/chunks/{chunk_id}
```

Qdrant 대시보드(http://localhost:6333/dashboard)에 `document_chunks` 컬렉션 + 3 points 생성됨. payload에 `chunk_id, document_id, domain, version, access_level, source_type, text` 포함.

> 같은 content 재등록은 `409 DUPLICATE_CONTENT` + `existing_document_id` 반환.

---

## 2. 온톨로지 확인

```bash
curl http://localhost:8000/ontology/entity-types
curl http://localhost:8000/ontology/relation-types
```

9 entity types, 6 relation types가 활성 상태로 등록되어 있어야 합니다.

---

## 3. LLM 추출 → Staging

```bash
curl -X POST http://localhost:8000/documents/{document_id}/extract
```

응답:
```json
{
  "document_id": "...",
  "chunk_ids": ["...", "...", "..."],
  "entities_extracted": 7,
  "relations_extracted": 6,
  "schema_violations": 1,
  "audit_log_id": "..."
}
```

**`LLM_PROVIDER=fake` 기본값**이라 API 키 없이도 동작합니다. Fake provider는 의도적으로 1건의 **스키마 위반**(`Policy APPLIES_TO Refund` — seed에 없음)을 포함시켜 거버넌스 거부 경로를 데모합니다.

후보 조회:
```bash
curl 'http://localhost:8000/documents/{document_id}/candidates'
curl 'http://localhost:8000/candidates/entities?review_status=PENDING'
curl 'http://localhost:8000/candidates/relations?review_status=REJECTED'   # 스키마 위반 분리
```

---

## 4. 검수 (Review)

### Entity 승인

```bash
curl -X POST http://localhost:8000/candidates/entities/{entity_id}/approve \
  -H 'Content-Type: application/json' \
  -d '{"reviewer":"alice"}'
```

### Relation 승인 — Source/Target 가드

source 또는 target entity가 APPROVED가 아니면 **409**:

```json
{ "detail": {
    "code": "SOURCE_NOT_APPROVED",
    "message": "source entity is not APPROVED — approve it first"
}}
```

양쪽 모두 APPROVED 상태일 때만 승인 통과:

```bash
curl -X POST http://localhost:8000/candidates/relations/{relation_id}/approve \
  -H 'Content-Type: application/json' \
  -d '{"reviewer":"alice"}'
```

### 기타 액션

```bash
# 반려
curl -X POST http://localhost:8000/candidates/entities/{entity_id}/reject \
  -H 'Content-Type: application/json' \
  -d '{"reviewer":"alice","reason":"잘못된 추출"}'

# 수정 (name/normalized_name/entity_type)
curl -X PATCH http://localhost:8000/candidates/entities/{entity_id} \
  -H 'Content-Type: application/json' \
  -d '{"reviewer":"alice","normalized_name":"NewName"}'

# 병합 (중복 normalized_name 통합)
curl -X POST http://localhost:8000/candidates/entities/{entity_id}/merge \
  -H 'Content-Type: application/json' \
  -d '{"reviewer":"alice","into_id":"{canonical_entity_id}"}'
```

---

## 5. Graph Sync (Neo4j 적재)

```bash
curl -X POST http://localhost:8000/graph/sync
```

응답:
```json
{
  "entity_success": 3, "entity_failed": 0, "entity_skipped": 0,
  "relation_success": 2, "relation_failed": 0, "relation_skipped": 0
}
```

같은 요청을 두 번째로 호출하면 기본적으로 모두 `SKIPPED` (이미 SUCCESS 로그가 있으므로). 강제 재동기화는 `?force=true`.

**부분 sync**도 가능:
```bash
curl -X POST http://localhost:8000/graph/sync/entities
curl -X POST http://localhost:8000/graph/sync/relations
```

Sync 이력:
```bash
curl 'http://localhost:8000/graph/sync-logs'
curl 'http://localhost:8000/graph/sync-logs?sync_status=FAILED'
```

### 자동 sync 옵션

`.env` 의 `AUTO_GRAPH_SYNC_ON_APPROVE=true` 설정 시 approve 직후 자동 sync 트리거. 실패해도 review는 항상 성공 (best-effort).

---

## 6. Graph 조회

### REST

```bash
# Entity + 모든 근거 chunk
curl http://localhost:8000/graph/entities/FullCancelPolicy

# 시드 기준 N-hop Subgraph (relation_type whitelist 적용)
curl 'http://localhost:8000/graph/subgraph?seed=FullCancelPolicy&depth=2'
```

### Neo4j Browser (http://localhost:7474)

```cypher
// 모든 Entity와 근거 chunk
MATCH (e:Entity)-[:DEFINED_IN]->(c:DocumentChunk) RETURN e, c LIMIT 25;

// FullCancelPolicy 중심 2-hop
MATCH p=(e:Entity {normalized_name: "FullCancelPolicy"})-[*1..2]-(n) RETURN p;

// 도메인 관계만 (DEFINED_IN 제외)
MATCH (s:Entity)-[r]->(t:Entity)
WHERE type(r) <> 'DEFINED_IN'
RETURN s.normalized_name, type(r), t.normalized_name, r.confidence;
```

---

## 7. GraphRAG 질의

```bash
curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question":"배송 시작 전 결제 완료 주문은 전체 취소 가능한가?"}'
```

응답:
```json
{
  "answer": "결론: 제공된 근거 기준으로 결제 완료 후 배송 시작 전에는 주문 전체 취소가 가능합니다...",
  "graph_context": { "seed_entities": ["FullCancelPolicy", ...], "triple_count": 3 },
  "document_evidence": { "chunk_count": 2 },
  "query_log_id": "..."
}
```

### 폴백 경로 확인

| 시나리오 | 결과 |
|---|---|
| 무관한 질문 (graph + vector 모두 비어 있음) | `"근거 부족: ..."`, LLM 호출 스킵, 로그는 기록 |
| Graph sync 안 한 상태 | vector-only fallback → 답변 시도 |
| 실 OpenAI/Anthropic 호출 실패 | `502 LLM_PROVIDER_FAILED` + `query_log_id` 반환, 로그에 `error_message` 보존 |

---

## 8. Audit Log

### 도메인 변경 이력

```bash
# 추출 실행 기록
curl 'http://localhost:8000/audit-logs?action=EXTRACTION_RUN'

# 특정 문서의 승인 이력
curl 'http://localhost:8000/audit-logs?action=ENTITY_APPROVED&document_id={document_id}'

# 단건 — before_json / after_json / metadata_json 전체
curl http://localhost:8000/audit-logs/{audit_log_id}
```

### QA 이력 (재현·디버깅용)

```bash
curl http://localhost:8000/qa/logs
curl 'http://localhost:8000/qa/logs?contains_question=환불'
curl 'http://localhost:8000/qa/logs?model_provider=fake&limit=10'
curl http://localhost:8000/qa/logs/{query_log_id}
```

단건 응답에 `question / detected_entities_json / graph_context_json / retrieved_chunks_json / final_prompt / answer / token_estimate / latency_ms / error_message` 모두 포함 — **prompt 재현, 비용 추적, 실패 원인 분석** 가능.

---

## 9. 실 LLM Provider로 전환 (선택)

`.env` 변경:

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

또는 Anthropic:

```ini
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

`docker compose restart app` 후 동일 시나리오를 다시 돌리면 Fake가 아닌 실 LLM이 호출됩니다. API 키 누락/오류 시 factory가 자동으로 Fake로 폴백.

---

## 10. 트러블슈팅

| 증상 | 점검 |
|---|---|
| `/health` 가 `neo4j: down` | `docker compose logs neo4j` — 첫 부팅은 30-60s 소요 |
| `POST /documents` 가 409 | `content_hash` 중복 — 같은 본문 재등록은 막힘. `existing_document_id` 확인 |
| `POST /candidates/relations/.../approve` 가 409 | source/target entity가 APPROVED 아님 — entity부터 승인 |
| `POST /graph/sync` 가 모두 SKIPPED | 이미 sync된 상태. 강제 재동기화는 `?force=true` |
| `POST /qa` 가 "근거 부족" | graph에 시드 entity 없음 + vector 검색 0건. Sync 했는지 / 문서 있는지 확인 |
| 실 LLM 호출 502 | `qa/logs/{id}` 의 `error_message` 확인. 키 누락 시 factory가 fake로 fallback해야 정상 |
