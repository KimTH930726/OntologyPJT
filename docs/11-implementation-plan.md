# 11. 구현 계획 & 현황 (Implementation Plan & Status)

> 이 문서는 W0~W4 구현 진행 상황과 MVP DoD를 한 페이지에 모은 것입니다.
> 디렉토리·DDL·API·Cypher 등 영역별 디테일은 각각의 docs로 분리되어 있습니다 (아래 표 참조).

---

## 11.1 구현 전략 (회고용 — 의도된 원칙)

### 진행 모토
- **걷기 가능한 골격부터(walking skeleton)**: W1 끝에 "업로드 → chunk → vector 인덱싱"이 통하면 그 위에 W2~W4를 얹는다.
- **Schema-first**: ontology type / Pydantic schema / SQL DDL을 코드 전에 정의. LLM 출력 검증 = 같은 schema 재사용.
- **SSOT는 Postgres**: 모든 검수 상태·audit는 Postgres에 산다. Neo4j는 derived view, Qdrant는 derived index.
- **외부 의존은 Fake-first**: LLM·Embedding 둘 다 Fake provider로 먼저 동작 검증 → 실 키 주입은 토글.
- **거버넌스 불변식 4개를 코드로 강제**:
  1. LLM 출력은 무조건 staging만 친다 (직접 Neo4j 경로 없음).
  2. Relation 스키마(source/relation/target 조합)는 service에서 검증, 위반 시 자동 REJECTED.
  3. Relation APPROVE는 양쪽 Entity APPROVED일 때만 가능 — `domain/policies/relation_approval.py` 순수 함수로 추출.
  4. Neo4j 적재 시 반드시 `(:Entity)-[:DEFINED_IN]->(:DocumentChunk)` 생성.

### 품질 가드레일 (현재 그린)
| 도구 | 결과 |
|---|---|
| `pytest` | 58 passed (unit + invariant) |
| `ruff check` | All checks passed |
| `ruff format` | clean |
| `mypy app` | Success: no issues found in 86 source files |

---

## 11.2 실제 디렉토리 구조

```
OntologyPJT/
├─ README.md                  ← 메인 (피치 + 다이어그램 + Quickstart)
├─ docker-compose.yml         ← postgres / neo4j / qdrant / app
├─ Dockerfile
├─ pyproject.toml             ← ruff / mypy / pytest 설정
├─ requirements.txt
├─ alembic/                   ← versions/0001~0006
├─ app/
│   ├─ main.py                ← FastAPI app + lifespan
│   ├─ core/                  ← config, deps, logging, security
│   ├─ db/                    ← Base, session, neo4j/qdrant clients, models/
│   │   └─ models/            ← Document, Chunk, Ontology*, Extracted*, GraphSyncLog, PromptTemplate, PromptVersion, AIQueryLog, AuditLog
│   ├─ domain/                ← enums, exceptions, policies/
│   │   └─ policies/relation_approval.py  ← 순수 정책 함수
│   ├─ schemas/               ← Pydantic DTO (document, chunk, ontology, extraction, review, audit, graph, qa)
│   ├─ repositories/          ← 데이터 접근 (Postgres + Neo4j + Qdrant)
│   ├─ services/              ← 비즈니스 로직 (12개 서비스 + retriever + builder)
│   ├─ integrations/          ← LLM Gateway (base / fake / openai / anthropic / factory)
│   ├─ prompts/               ← jinja2 (extraction.*, qa_default.j2)
│   ├─ api/routes/            ← documents, chunks, ontology, extraction, review, graph, qa, audit, health
│   └─ seeds/                 ← ontology_seed, prompt_seed (멱등 실행)
├─ tests/
│   ├─ conftest.py
│   └─ unit/                  ← chunking, embedding, fake provider, context builder, validators,
│                                relation approval policy, graph sync invariants, QA fallbacks, prompt builder
└─ docs/
    ├─ USAGE.md               ← E2E 가이드
    └─ 01~11                  ← 영역별 설계 + 본 문서
```

자세한 책임 매핑은 [01-architecture.md §1.4](01-architecture.md).

---

## 11.3 영역별 디테일은 다음 문서로

| 영역 | 문서 / 코드 |
|---|---|
| Docker Compose | 루트 [`docker-compose.yml`](../docker-compose.yml) |
| DB 스키마 (설계) | [03-database-schema.md](03-database-schema.md) |
| DB 스키마 (실제) | [`alembic/versions/0001~0006`](../alembic/versions/) |
| Neo4j 모델 | [04-graph-model.md](04-graph-model.md) + [`app/repositories/neo4j_repository.py`](../app/repositories/neo4j_repository.py) |
| REST API (설계) | [05-api-spec.md](05-api-spec.md) |
| REST API (실제) | [`app/api/routes/*`](../app/api/routes/) + 실행 중 `/docs` 자동 OpenAPI |
| GraphRAG 시퀀스 | [07-query-sequence.md](07-query-sequence.md) + [`app/services/qa_service.py`](../app/services/qa_service.py) |
| Extraction Prompt | [`app/prompts/extraction.system.j2`](../app/prompts/extraction.user.j2) |
| QA Prompt | [`app/prompts/qa_default.j2`](../app/prompts/qa_default.j2) |
| Admin UI 디자인 | [06-admin-ui.md](06-admin-ui.md) — **미구현**, v2 후보 |
| MVP 제외 항목 | [09-out-of-scope.md](09-out-of-scope.md) |
| 포트폴리오 메시지 | [10-portfolio.md](10-portfolio.md) |

---

## 11.4 W0~W4 체크리스트 (완료)

### W0 — 인프라 + scaffold
- [x] `docker-compose.yml` (postgres / neo4j(APOC) / qdrant / app + healthcheck)
- [x] `Dockerfile`, `requirements.txt`, `.env.example`
- [x] FastAPI scaffold + `/health` (서비스 down 시에도 앱은 살아 있음)
- [x] Alembic 환경 초기화

### W1 — 문서 → Chunk → Vector
- [x] migration 0001: `document` + `document_chunk` (CHECK on `vector_status`)
- [x] `ChunkingService` (sentence-per-chunk + hard split fallback)
- [x] `EmbeddingService` (deterministic 384-d, L2 normalized)
- [x] Qdrant collection auto-ensure + payload (`chunk_id, document_id, domain, version, access_level, source_type, text`)
- [x] API: `POST /documents`, `GET /documents{,/:id,/:id/chunks}`, `GET /chunks/:id`
- [x] 중복 등록 가드 (`content_hash` UNIQUE + 409)

### W2 — Ontology + Extraction + Staging + Review + Audit
- [x] migration 0002: `ontology_entity_type` + `ontology_relation_type` (UNIQUE on signature)
- [x] migration 0003: `extracted_entity` + `extracted_relation` + `audit_log` (JSONB)
- [x] Seed: 9 entity / 6 relation types 멱등 삽입
- [x] LLM Gateway: base Protocol + Fake/OpenAI/Anthropic + env-driven factory
- [x] Extraction Prompts (jinja2) + 스키마 검증 후 staging insert
- [x] **스키마 위반은 REJECTED + reason=SCHEMA_VIOLATION** 으로 영속화 (추적 가능)
- [x] Review: approve/reject/modify/merge for entity & relation
- [x] **Relation approve = source/target APPROVED 가드** (policy 함수로 분리)
- [x] `audit_log`: 모든 review 액션에 before/after snapshot

### W3 — Graph Sync + Subgraph 조회
- [x] migration 0004: `graph_sync_log`
- [x] Neo4j 제약/인덱스 lifespan 자동 ensure
- [x] `Neo4jRepository`: MERGE 기반 entity/relation/chunk 적재 + `DEFINED_IN` 자동 연결
- [x] Relation type whitelist + 정규식 + 백틱 quoting (3중 보호)
- [x] `GraphSyncService`: APPROVED만 / 양쪽 endpoint Neo4j 존재 재검증 / row 단위 실패 격리
- [x] `force=false` 시 SUCCESS 이력 있으면 SKIPPED (idempotent)
- [x] API: `POST /graph/sync{,/entities,/relations}?force=`, `GET /graph/sync-logs`, `GET /graph/entities/:name`, `GET /graph/subgraph?seed=&depth=`
- [x] `AUTO_GRAPH_SYNC_ON_APPROVE` 옵션 (best-effort)

### W4 — GraphRAG QA + Audit
- [x] migration 0005: `prompt_template` + `prompt_version` (partial-unique active per template)
- [x] migration 0006: `ai_query_log` (JSONB context + final_prompt + answer + token/latency/error)
- [x] LLM Provider Protocol 확장: `answer()` + `extract_intent_entities()`
- [x] Fake provider QA — happy path / vector-only / no-context 3경로 deterministic
- [x] `GraphRetriever`: 직접 매칭 → provider intent 폴백 → 빈 결과
- [x] `VectorRetriever`: graph evidence chunks 우선 → kNN 보강 → dedupe
- [x] `ContextBuilder`: 문자 budget, graph 우선
- [x] `PromptBuilder`: DB active version → 번들 .j2 파일 폴백
- [x] `QAService`: 4경로 (happy / vector-only / no-context / LLM-fail) 모두 `ai_query_log` 영속화
- [x] API: `POST /qa`, `GET /qa/logs{,/:id}`

### 리팩토링 라운드
- [x] `domain/exceptions.py` — `DomainError` 루트 + 4종 + `http_status`
- [x] `domain/policies/relation_approval.py` — 순수 정책 추출
- [x] `pyproject.toml` — ruff / mypy / pytest 통합
- [x] 58 tests (unit + invariant) 추가 — 모든 7 invariant 회귀 보호
- [x] `QdrantRepository.upsert_points()` batch API
- [x] `DocumentService.list` → `list_documents` (mypy shadow 제거)

---

## 11.5 MVP Definition of Done (DoD)

`docker compose up` 한 번 후 다음 시나리오가 처음부터 끝까지 통해야 MVP 완료.

1. **환경**: 4개 컨테이너 healthy. `/health` 200.
2. **Seed**: `GET /ontology/entity-types` 9종, `relation-types` 6종 반환.
3. **문서 업로드**: `POST /documents` 60초 내 `chunk_count > 0`, 모든 chunk `vector_status=INDEXED`, Qdrant point 동일 수.
4. **추출**: `POST /documents/:id/extract` 60초 내 entity ≥ 3, relation ≥ 2. 스키마 위반은 REJECTED로 분리.
5. **검수**: entity/relation approve → `status=APPROVED`, audit_log 기록.
6. **Neo4j 검증**: `MATCH (e:Entity)-[:DEFINED_IN]->(c) RETURN e,c LIMIT 25` 결과 ≥ 3.
7. **GraphRAG QA**: `POST /qa` 응답에 결론/근거/후속 액션 3섹션 + `evidence.graph` + `evidence.chunks` + `trace_id` 포함.
8. **Audit**: `GET /qa/logs/:id` 에 `rendered_prompt`, `answer`, `token_estimate`, `latency_ms` 모두 존재.
9. **거버넌스 가드 동작 확인**:
   - 스키마 위반 relation 자동 REJECTED.
   - source 미승인 상태 relation approve → 409 `SOURCE_NOT_APPROVED`.
   - 직접 Neo4j write 경로 부재 (코드 grep).
10. **운영**: 모든 변경 API에 audit_log 1건 이상 (DOC_UPLOAD / EXTRACTION_RUN / REVIEW_* / GRAPH_SYNC / QUERY).

위 10가지 모두 코드 + 테스트 레벨에서 구현 완료. 로컬 실제 동작 검증은 `docs/USAGE.md` 시나리오로 직접 수행하면 됩니다.

---

## 11.6 남은 리스크 & 다음 단계

| 항목 | 상태 |
|---|---|
| 실 OpenAI/Anthropic happy path 1회 검증 | 미수행 (Fake로만 검증) |
| GitHub Actions CI | 미구성 (`.github/workflows/ci.yml`) |
| testcontainers 기반 통합 테스트 | 단위/모킹만 — 실 Postgres 시나리오 1개 추가 권장 |
| Admin UI | 미구현 — 데모/포트폴리오 임팩트 큼 |
| Extraction을 BackgroundTasks → 워커 분리 | 대용량 문서 대비 v2 |
| Neo4j sync UNWIND batch | 1000+ entity 시점 |
| 권한 모델 | 단일 `X-Admin-Token`, RBAC 없음 |

우선순위 추천: **로컬 실행 검증 → CI yaml 추가 → 실 LLM 키 1회 → Admin UI** 순.
