# 11. 구현 계획서 (Implementation Plan)

> 본 문서는 `docs/01~10`의 설계를 **곧바로 코드로 옮기기 위한 태스크 분해**다.
> 모든 결정은 "로컬 Docker Compose에서 60분 안에 동작" 기준으로 단순화한다.

---

## 11.1 전체 구현 전략

### 11.1.1 진행 모토
- **걷기 가능한 골격부터(walking skeleton)**: 1주차 끝에 "업로드 → chunk → vector 인덱싱"이 한 번 통하게 만든다. 나머지는 그 위에 얹는다.
- **Schema-first**: ontology type, Pydantic schema, SQL DDL은 코드 작성 전 먼저 만든다. LLM 출력 검증 = 같은 schema 재사용.
- **하나의 진실(SSOT)**: 모든 검수 상태와 audit는 Postgres가 SSOT. Neo4j는 derived view. Qdrant는 derived index.
- **거버넌스 불변식 4개를 코드 레벨에서 강제**:
  1. LLM 출력은 무조건 staging만 친다 (직접 Neo4j 경로 없음).
  2. Relation은 (source_type, type_code, target_type) DB 트리거로 검증.
  3. Relation APPROVE는 양쪽 Entity APPROVED일 때만 가능 (서비스 + DB 가드).
  4. Neo4j 적재 시 반드시 `(:Entity)-[:DEFINED_IN]->(:DocumentChunk)` 생성.

### 11.1.2 빌드 순서 원칙
- **Top-down API + Bottom-up worker**: API 윤곽(라우터/DTO)을 먼저 박고, 내부 service/worker를 채운다.
- **외부 의존(LLM, embedding)은 처음부터 Gateway 인터페이스 + Fake 구현**으로 시작. 실제 호출은 환경변수 토글.
- **Migration은 Alembic** (auto-generate 금지, 수동 작성). 단일 `0001_init.sql` 정도로 시작 가능.

### 11.1.3 품질 가드레일
- ruff + black + mypy (strict는 services/*만)
- pytest + httpx + testcontainers (Postgres/Neo4j/Qdrant 컨테이너 띄워 통합 테스트)
- pre-commit hook으로 lint/type/test 일부 실행

---

## 11.2 디렉토리 구조

```
OntologyPJT/
├─ README.md
├─ docker-compose.yml
├─ .env.example
├─ pyproject.toml                # ruff, black, mypy, pytest 설정
├─ alembic.ini
├─ alembic/
│   └─ versions/
│       └─ 0001_init.py
├─ app/
│   ├─ main.py                   # FastAPI 진입점, router include
│   ├─ core/                     # 설정, 로깅, 예외, 의존성 wiring
│   │   ├─ config.py             # Pydantic Settings (env 로드)
│   │   ├─ logging.py
│   │   ├─ errors.py             # AppError/HTTPException mapping
│   │   ├─ deps.py               # FastAPI Depends 모음
│   │   └─ security.py           # X-Admin-Token 검사
│   ├─ db/
│   │   ├─ base.py               # SQLAlchemy Base
│   │   ├─ session.py            # engine, SessionLocal
│   │   ├─ models/               # ORM models
│   │   │   ├─ document.py
│   │   │   ├─ chunk.py
│   │   │   ├─ ontology.py
│   │   │   ├─ staging.py
│   │   │   ├─ graph_sync.py
│   │   │   ├─ audit.py
│   │   │   └─ prompt.py
│   │   └─ neo4j_client.py       # Neo4j 드라이버 wrapper
│   ├─ domain/                   # 순수 도메인 모델/Enum/value objects
│   │   ├─ enums.py              # ReviewStatus, VectorStatus, ObjectKind
│   │   ├─ ontology.py           # OntologyEntityTypeVO, OntologyRelationTypeVO
│   │   └─ rag.py                # GraphContext, DocumentEvidence VO
│   ├─ schemas/                  # Pydantic v2 (Request/Response DTO)
│   │   ├─ document.py
│   │   ├─ chunk.py
│   │   ├─ ontology.py
│   │   ├─ candidate.py
│   │   ├─ graph.py
│   │   ├─ qa.py
│   │   └─ common.py             # ApiResponse[T], ErrorBody
│   ├─ repositories/             # SQL/Neo4j/Qdrant 데이터 접근만
│   │   ├─ document_repo.py
│   │   ├─ chunk_repo.py
│   │   ├─ ontology_repo.py
│   │   ├─ staging_repo.py
│   │   ├─ graph_sync_repo.py
│   │   ├─ audit_repo.py
│   │   ├─ prompt_repo.py
│   │   ├─ neo4j_repo.py
│   │   └─ qdrant_repo.py
│   ├─ services/                 # 비즈니스 로직 (트랜잭션 경계)
│   │   ├─ document_service.py
│   │   ├─ chunking_service.py
│   │   ├─ embedding_service.py
│   │   ├─ ontology_schema_service.py
│   │   ├─ extraction_service.py
│   │   ├─ review_service.py
│   │   ├─ graph_sync_service.py
│   │   ├─ graph_retriever.py
│   │   ├─ vector_retriever.py
│   │   ├─ context_builder.py
│   │   ├─ prompt_builder.py
│   │   ├─ qa_service.py
│   │   └─ audit_service.py
│   ├─ integrations/             # 외부 시스템 어댑터
│   │   ├─ llm/
│   │   │   ├─ base.py           # LLMGateway 인터페이스
│   │   │   ├─ openai_provider.py
│   │   │   ├─ anthropic_provider.py
│   │   │   └─ fake_provider.py  # 테스트/오프라인
│   │   ├─ embedding/
│   │   │   ├─ base.py
│   │   │   ├─ openai_embed.py
│   │   │   └─ fake_embed.py
│   │   └─ qdrant_client.py
│   ├─ workers/                  # BackgroundTasks/async job
│   │   ├─ chunk_embed_worker.py
│   │   ├─ extraction_worker.py
│   │   └─ graph_sync_worker.py
│   ├─ prompts/                  # 텍스트 템플릿 (jinja2)
│   │   ├─ extraction.system.j2
│   │   ├─ extraction.user.j2
│   │   └─ qa_default.j2
│   ├─ api/
│   │   ├─ v1/
│   │   │   ├─ router.py
│   │   │   └─ endpoints/
│   │   │       ├─ documents.py
│   │   │       ├─ chunks.py
│   │   │       ├─ ontology.py
│   │   │       ├─ candidates.py
│   │   │       ├─ graph.py
│   │   │       ├─ qa.py
│   │   │       └─ audit.py
│   └─ seeds/
│       ├─ ontology_seed.py       # 이커머스 entity/relation type seed
│       └─ prompt_seed.py
├─ tests/
│   ├─ conftest.py                # testcontainers, FastAPI TestClient
│   ├─ unit/
│   └─ integration/
└─ scripts/
    ├─ wait_for_services.sh
    └─ load_sample_docs.py
```

### 디렉토리 역할 요약

| 디렉토리 | 책임 |
|---|---|
| `app/main.py` | FastAPI app 생성, router include, lifespan(startup/shutdown) |
| `app/core` | 설정, 로깅, 예외, 인증, FastAPI Depends |
| `app/db` | SQLAlchemy 모델/세션, Neo4j 드라이버 |
| `app/domain` | 프레임워크 무관 enum/value object |
| `app/schemas` | Pydantic DTO (입/출력). 도메인과 분리 |
| `app/repositories` | DB I/O. 비즈니스 로직 금지 |
| `app/services` | 트랜잭션 경계 + 비즈니스 규칙 |
| `app/integrations` | OpenAI/Claude/Embedding/Qdrant 어댑터 + Fake 구현 |
| `app/workers` | BackgroundTasks 단위 작업 (chunk/embed/extract/sync) |
| `app/prompts` | jinja2 템플릿 (DB의 prompt_template과 동기화) |
| `app/api/v1` | REST 라우터 (얇은 컨트롤러) |
| `app/seeds` | 부팅 시 멱등 seed (ontology, prompt) |
| `tests` | 단위/통합 테스트 |
| `scripts` | 운영 보조 스크립트 |

---

## 11.3 Docker Compose 설계

### 11.3.1 `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: ogp-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ogp}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ogp}
      POSTGRES_DB: ${POSTGRES_DB:-ogp}
    ports: ["5432:5432"]
    volumes: ["pg_data:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ogp}"]
      interval: 5s
      timeout: 3s
      retries: 20

  neo4j:
    image: neo4j:5-community
    container_name: ogp-neo4j
    environment:
      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-neo4jtest}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_security_procedures_unrestricted: "apoc.*"
    ports: ["7474:7474", "7687:7687"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

  qdrant:
    image: qdrant/qdrant:latest
    container_name: ogp-qdrant
    ports: ["6333:6333", "6334:6334"]
    volumes: ["qdrant_data:/qdrant/storage"]

  app:
    build: .
    container_name: ogp-app
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_started
      qdrant:
        condition: service_started
    ports: ["8000:8000"]
    volumes:
      - ./app:/code/app
      - ./alembic:/code/alembic
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

volumes:
  pg_data:
  neo4j_data:
  neo4j_logs:
  qdrant_data:
```

### 11.3.2 `.env.example`

```ini
# App
APP_ENV=local
ADMIN_TOKEN=dev-admin-token
LOG_LEVEL=INFO

# Postgres
POSTGRES_USER=ogp
POSTGRES_PASSWORD=ogp
POSTGRES_DB=ogp
DATABASE_URL=postgresql+psycopg://ogp:ogp@postgres:5432/ogp

# Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jtest
NEO4J_URI=bolt://neo4j:7687

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=chunks

# LLM
LLM_PROVIDER=openai          # openai | anthropic | fake
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

# Embedding
EMBED_PROVIDER=openai         # openai | fake
EMBED_MODEL=text-embedding-3-small
EMBED_DIM=1536

# Extraction
EXTRACT_MAX_CHUNKS_PER_DOC=50
EXTRACT_MIN_CONFIDENCE=0.5
```

### 11.3.3 `Dockerfile` (간단)

```dockerfile
FROM python:3.12-slim
WORKDIR /code
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system -e .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 11.4 PostgreSQL 스키마 (구현 순서)

전체 DDL은 `docs/03-database-schema.md` 참조. 여기서는 **생성 순서와 마이그레이션 단위**만 정의.

### 11.4.1 마이그레이션 분할

| Rev | 파일 | 내용 |
|---|---|---|
| 0001 | `0001_init.py` | ENUM + `document` + `document_chunk` |
| 0002 | `0002_ontology.py` | `ontology_entity_type` + `ontology_relation_type` |
| 0003 | `0003_staging.py` | `extracted_entity` + `extracted_relation` + 트리거 |
| 0004 | `0004_graph_sync.py` | `graph_sync_log` |
| 0005 | `0005_prompt.py` | `prompt_template` + `prompt_version` |
| 0006 | `0006_audit.py` | `audit_log` + `ai_query_log` |

### 11.4.2 핵심 컬럼 / 인덱스 요약

> 세부 DDL은 §3 참조. 여기서는 **잊으면 안 되는 인덱스/제약**만 강조.

- `document`: `UNIQUE(title, version)`, `INDEX(domain)`
- `document_chunk`: `UNIQUE(document_id, seq)`, `INDEX(vector_status)`, `checksum`은 not null
- `ontology_relation_type`: PK = `(code, source_type, target_type)`
- `extracted_entity`:
  - `INDEX(status)`
  - **부분 UNIQUE**: `(normalized_name, type_code) WHERE status='APPROVED' AND merged_into IS NULL`
- `extracted_relation`:
  - `INDEX(status)`
  - **트리거** `fn_validate_relation_schema()` (스키마 위반 INSERT/UPDATE 거부)
- `graph_sync_log`: `INDEX(object_kind, staging_id)`
- `ai_query_log`: `INDEX(actor_id)`, `INDEX(created_at)`
- `audit_log`: `INDEX(event_type, created_at DESC)`
- `prompt_version`: 부분 UNIQUE `(template_id) WHERE is_active=TRUE`

### 11.4.3 생성 순서 (논리적 의존)

1. ENUM (`review_status`, `vector_status`, `sync_action`, `object_kind`)
2. `document` → `document_chunk`
3. `ontology_entity_type` → `ontology_relation_type`
4. `extracted_entity` → `extracted_relation` → **검증 트리거**
5. `graph_sync_log`
6. `prompt_template` → `prompt_version`
7. `audit_log` → `ai_query_log`

### 11.4.4 Seed

- `app/seeds/ontology_seed.py`: §2.5 표 그대로 `INSERT ... ON CONFLICT DO NOTHING`.
- `app/seeds/prompt_seed.py`: `qa_default v1`, `extraction_default v1` 삽입 + `is_active=TRUE`.
- `app.main:lifespan` startup에서 호출 (멱등).

---

## 11.5 API 명세 (Phase별)

> 응답 공통 envelope: `{"data": ..., "meta": {...}}`. 에러: `{"error": {"code","message","detail"}}`.
> 인증: `X-Admin-Token: ${ADMIN_TOKEN}` (모든 변경 API).

### Phase 1 — 문서/Chunk

#### P1-1. 문서 등록

- **Method/URL**: `POST /api/v1/documents`
- **Request**:
  ```json
  { "title": "환불 정책 v1", "domain": "ecommerce", "text": "결제 완료 후 ..." }
  ```
  또는 multipart `file` + `title` + `domain`
- **Response 201**:
  ```json
  { "data": { "id": "uuid", "version": 1, "chunk_count": 0, "status": "INDEXING" } }
  ```
- **흐름**:
  1. `DocumentService.create(title, domain, text)` — `document` row insert
  2. `BackgroundTasks.add_task(chunk_embed_worker.run, document_id)`
  3. worker: `ChunkingService.split → document_chunk insert → EmbeddingService.embed → QdrantRepo.upsert → vector_status=INDEXED`
  4. `AuditLogService.log("DOC_UPLOAD", payload={document_id})`

#### P1-2. 문서 목록

- **GET** `/api/v1/documents?domain=&page=1&size=20`
- **Response**: `{ "data": [Document...], "meta": { "page", "size", "total" } }`
- **흐름**: `DocumentRepo.list(filters, page, size)`

#### P1-3. 문서 상세

- **GET** `/api/v1/documents/{id}`
- **Response**: 문서 메타 + `chunk_count` + `pending/approved` 후보 통계
- **흐름**: 단일 select + `staging_repo.count_by_status(document_id)`

#### P1-4. Chunk 목록

- **GET** `/api/v1/documents/{id}/chunks?status=`
- **Response**: `[{id, seq, token_count, vector_status, text_preview}]`
- **흐름**: `ChunkRepo.list_by_document(id, status)`

#### P1-5. Chunk 단건

- **GET** `/api/v1/chunks/{id}` → 원문 전체

---

### Phase 2 — Ontology Schema

#### P2-1. Entity Type

- **GET** `/api/v1/ontology/entity-types`
- **POST** `/api/v1/ontology/entity-types` `{code,label,description,json_schema?}`
- **PATCH** `/api/v1/ontology/entity-types/{code}` `{label?, description?, is_active?}`
- **흐름**: `OntologySchemaService.upsert_entity_type` → audit

#### P2-2. Relation Type

- **GET** `/api/v1/ontology/relation-types`
- **POST** `/api/v1/ontology/relation-types` `{code,source_type,target_type,description}`
- **PATCH** `/api/v1/ontology/relation-types/{code,source_type,target_type}` (deactivate)
- **흐름**: source/target가 존재하는 entity type인지 검증 → insert → audit

---

### Phase 3 — Extraction & Review

#### P3-1. 추출 실행

- **POST** `/api/v1/documents/{id}/extract`
- **Request**: `{ "chunk_ids": ["..."]?, "force": false }`
- **Response 202**: `{ "data": { "job_id": "uuid", "scheduled": N } }`
- **흐름**:
  1. `ExtractionService.schedule(document_id, chunk_ids?, force)` — pending인 chunk 한정
  2. `BackgroundTasks.add_task(extraction_worker.run, ...)`
  3. worker: chunk 단위 LLM 호출 → JSON 검증(pydantic) → `(source_type,type_code,target_type)` 스키마 매칭 검증 → staging insert (위반 시 status=REJECTED, reason=SCHEMA_VIOLATION)
  4. audit `EXTRACTION_RUN`

#### P3-2. 후보 목록

- **GET** `/api/v1/candidates/entities?status=PENDING&document_id=&chunk_id=`
- **GET** `/api/v1/candidates/relations?status=PENDING&document_id=&chunk_id=`

#### P3-3. 후보 승인/반려/수정/병합

- **POST** `/api/v1/candidates/entities/{id}/approve` `{reviewer}`
- **POST** `/api/v1/candidates/entities/{id}/reject` `{reviewer, reason}`
- **POST** `/api/v1/candidates/entities/{id}/modify` `{reviewer, name?, normalized_name?, type_code?}`
- **POST** `/api/v1/candidates/entities/{id}/merge` `{reviewer, into_id}`
- **POST** `/api/v1/candidates/relations/{id}/approve|reject|modify`

**Approve 흐름 (entity)**:
1. `ReviewService.approve_entity(id, reviewer)` — status update, reviewed_at/by 기록
2. `GraphSyncService.schedule_entity(id)` (혹은 즉시 upsert)
3. audit `REVIEW_APPROVE`

**Approve 흐름 (relation)**:
1. source/target entity의 status=APPROVED 확인 (아니면 409 `NOT_APPROVED_SOURCE`)
2. status update
3. `GraphSyncService.schedule_relation(id)`
4. audit

---

### Phase 4 — Graph Sync & Query

#### P4-1. 일괄 적재

- **POST** `/api/v1/graph/sync`
- **Response**: `{ "data": { "entities": N, "relations": M, "errors": [...] } }`
- **흐름**: `GraphSyncService.sync_pending()` — APPROVED인데 graph_sync_log에 CREATE 없는 것 일괄 upsert

#### P4-2. Sync Log

- **GET** `/api/v1/graph/sync-logs?object_kind=&from=`

#### P4-3. Graph 조회

- **GET** `/api/v1/graph/entities/{normalized_name}` → 노드 + 1-hop
- **GET** `/api/v1/graph/subgraph?seed=&depth=2&types=`
- **흐름**: `GraphRetriever.subgraph(seeds, depth, types)` → 직렬화

#### P4-4. (admin) Raw Cypher

- **POST** `/api/v1/graph/cypher` `{cypher, params}` — admin token 필수, read 전용 검사 (정규식 가드)

---

### Phase 5 — QA & Audit

#### P5-1. 질문 응답

- **POST** `/api/v1/qa`
- **Request**:
  ```json
  { "question": "주문 O1001은 환불 가능한가?",
    "options": { "top_k_chunks": 5, "graph_depth": 2, "prompt_template": "qa_default" } }
  ```
- **Response 200**:
  ```json
  { "data": { "answer": "...",
              "evidence": { "graph": [...], "chunks": [...] },
              "trace_id": "uuid" } }
  ```
- **흐름**: `QAService.answer(question, options)` — §7 시퀀스 그대로. 최종 `ai_query_log` insert 후 trace_id 반환.

#### P5-2. Audit 조회

- **GET** `/api/v1/audit?event_type=&from=&to=`
- **GET** `/api/v1/qa/logs?from=&to=`
- **GET** `/api/v1/qa/logs/{id}` — prompt/answer 전문

---

## 11.6 핵심 서비스 클래스 설계

> 표기: `메서드(입력) -> 반환`. 의존성은 생성자 주입.

### DocumentService
- **책임**: 문서 메타 CRUD, chunk/embed 잡 스케줄
- **의존성**: `DocumentRepo`, `ChunkRepo`, `BackgroundTasks`, `AuditLogService`
- **메서드**
  - `create(title, domain, text|file) -> Document` — row 생성 후 chunk/embed 백그라운드 큐잉
  - `get(id) -> DocumentDetail` — meta + chunk_count + status 집계
  - `list(filters, page, size) -> Paginated[Document]`
  - `schedule_reextract(id, force) -> JobInfo`
  - `delete(id) -> None`

### ChunkingService
- **책임**: 텍스트 → 청크 분할 (한국어 문장 + 토큰 윈도우)
- **의존성**: 없음 (또는 tiktoken)
- **메서드**
  - `split(text, max_tokens=700, overlap=80) -> list[ChunkDraft]`
  - `compute_checksum(text) -> str`

### EmbeddingService
- **책임**: 텍스트 임베딩 + Qdrant 적재
- **의존성**: `EmbeddingClient(integrations.embedding.base)`, `QdrantRepo`, `ChunkRepo`
- **메서드**
  - `embed_chunks(document_id) -> int` — vector_status=PENDING chunk만 처리
  - `embed_text(text) -> list[float]` (재사용)

### OntologySchemaService
- **책임**: Entity/Relation Type 관리, **active schema snapshot 제공** (Extractor가 사용)
- **의존성**: `OntologyRepo`, `AuditLogService`
- **메서드**
  - `upsert_entity_type(dto) -> OntologyEntityType`
  - `upsert_relation_type(dto) -> OntologyRelationType`
  - `active_snapshot() -> OntologySnapshot` — `{entity_types[], relation_types[]}` (prompt 주입용)

### EntityRelationExtractionService
- **책임**: chunk 단위 LLM 호출 → 후보 검증 → staging insert
- **의존성**: `OntologySchemaService`, `LLMGateway`, `PromptBuilder`, `StagingRepo`, `ChunkRepo`, `AuditLogService`
- **메서드**
  - `extract_chunk(chunk_id) -> ExtractionResult`
    - 1) `snap = OntologySchemaService.active_snapshot()`
    - 2) `prompt = PromptBuilder.build_extraction(snap, chunk.text)`
    - 3) `raw = LLMGateway.complete_json(prompt, schema=ExtractionResponse)`
    - 4) pydantic 검증 → relation은 (src_type, type, tgt_type) 매칭 체크 → 위반은 REJECTED+SCHEMA_VIOLATION
    - 5) `StagingRepo.bulk_insert(entities, relations)`
    - 6) audit
  - `extract_document(document_id, chunk_ids?) -> int`

### ReviewService
- **책임**: 상태 전이 + Graph sync 트리거
- **의존성**: `StagingRepo`, `GraphSyncService`, `AuditLogService`
- **메서드**
  - `approve_entity(id, reviewer) -> ExtractedEntity`
  - `reject_entity(id, reviewer, reason) -> ExtractedEntity`
  - `modify_entity(id, reviewer, patch) -> ExtractedEntity` — status `MODIFIED`
  - `merge_entity(id, into_id, reviewer)`
  - 위와 동일한 4개 for relation. relation approve는 source/target APPROVED 가드.

### GraphSyncService
- **책임**: Postgres staging → Neo4j upsert + log
- **의존성**: `StagingRepo`, `Neo4jRepo`, `GraphSyncLogRepo`
- **메서드**
  - `sync_entity(staging_id) -> SyncResult`
  - `sync_relation(staging_id) -> SyncResult`
  - `sync_pending() -> SyncSummary` — 일괄
  - 내부: 항상 `(:Entity)-[:DEFINED_IN]->(:DocumentChunk)` 함께 보장

### GraphRetriever
- **책임**: Cypher 기반 Subgraph 탐색
- **의존성**: `Neo4jRepo`
- **메서드**
  - `subgraph(seed_names: list[str], depth: int, type_filter: list[str]|None) -> GraphContext`
  - `neighbors(normalized_name, depth=1) -> GraphContext`

### VectorRetriever
- **책임**: Qdrant kNN
- **의존성**: `QdrantRepo`, `EmbeddingService`
- **메서드**
  - `search(query: str, top_k: int, chunk_id_in: list[str]|None) -> list[DocumentEvidence]`

### ContextBuilder
- **책임**: Graph + Chunk → 평탄화/budget cut
- **의존성**: 없음
- **메서드**
  - `build(graph: GraphContext, chunks: list[DocumentEvidence], token_budget: int) -> StructuredContext`

### PromptBuilder
- **책임**: 활성 prompt_version 로드 + jinja2 렌더
- **의존성**: `PromptRepo`
- **메서드**
  - `build_extraction(snapshot: OntologySnapshot, chunk_text: str) -> RenderedPrompt`
  - `build_qa(context: StructuredContext, question: str, template_name="qa_default") -> RenderedPrompt`

### LLMGateway (interface)
- **책임**: provider 추상화, retry/timeout, token usage 노출
- **메서드**
  - `complete(prompt: RenderedPrompt, *, model: str|None, max_tokens: int|None) -> LLMResponse`
  - `complete_json(prompt: RenderedPrompt, *, schema: type[BaseModel]) -> tuple[BaseModel, LLMUsage]` — `response_format=json` / Anthropic은 tool use

### AuditLogService
- **책임**: 모든 도메인 이벤트와 질의 audit 기록
- **의존성**: `AuditRepo`, `QueryLogRepo`
- **메서드**
  - `log(event_type: str, actor_id: str|None, payload: dict) -> None`
  - `log_query(...) -> uuid`  (질의 전용; ai_query_log row)

### QAService (오케스트레이션)
- **책임**: §7 Sequence 실행
- **의존성**: `LLMGateway`(intent), `GraphRetriever`, `VectorRetriever`, `ContextBuilder`, `PromptBuilder`, `LLMGateway`(answer), `AuditLogService`
- **메서드**
  - `answer(question: str, opts: QAOptions) -> QAAnswer`

---

## 11.7 LLM 프롬프트

### 11.7.1 Entity/Relation 추출 프롬프트

#### System (`prompts/extraction.system.j2`)

```
너는 도메인 온톨로지 추출기다. 아래 규칙을 반드시 지켜라.

[규칙]
1. 반드시 아래 "허용 Entity Type"과 "허용 Relation Type" 안에서만 추출한다.
2. 입력 문장에 명시되지 않은 사실이나 관계를 만들지 않는다.
3. 출력은 오직 하나의 JSON 객체여야 한다. 코드블록/설명/주석 금지.
4. 각 entity와 relation에는 0.0~1.0 사이의 confidence를 부여한다.
5. 판단이 애매하거나 근거 문장이 분명치 않으면 needs_review=true로 표기한다.
6. 각 항목에 evidence_sentence(원문에서 그대로 발췌한 문장)를 포함한다.
7. relation의 source/target은 동일 응답의 entities.normalized_name과 정확히 일치해야 한다.

[허용 Entity Type]
{% for t in entity_types %}
- {{ t.code }}: {{ t.description or "" }}
{% endfor %}

[허용 Relation Type]
{% for r in relation_types %}
- {{ r.code }} ( {{ r.source_type }} -> {{ r.target_type }} ): {{ r.description or "" }}
{% endfor %}

[출력 JSON 스키마]
{
  "entities": [
    {
      "name": "원문 표기",
      "normalized_name": "PascalCase 또는 snake_case 정규화 이름",
      "type": "Policy",
      "confidence": 0.0,
      "needs_review": false,
      "evidence_sentence": "..."
    }
  ],
  "relations": [
    {
      "source": "normalized_name",
      "target": "normalized_name",
      "type": "REQUIRES",
      "confidence": 0.0,
      "needs_review": false,
      "evidence_sentence": "..."
    }
  ]
}
```

#### User (`prompts/extraction.user.j2`)

```
[Chunk 원문]
{{ chunk_text }}

위 원문에서 허용된 Entity/Relation만 추출하여 위 JSON 스키마로만 응답하라.
원문에 없는 내용을 추론하지 말 것. 빈 결과는 {"entities": [], "relations": []} 로 답하라.
```

#### Pydantic 검증 (`schemas/candidate.py`)

```python
class ExtractedEntityOut(BaseModel):
    name: str
    normalized_name: str
    type: str
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False
    evidence_sentence: str

class ExtractedRelationOut(BaseModel):
    source: str
    target: str
    type: str
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False
    evidence_sentence: str

class ExtractionResponse(BaseModel):
    entities: list[ExtractedEntityOut]
    relations: list[ExtractedRelationOut]
```

OpenAI는 `response_format={"type":"json_schema", ...}`, Claude는 tool use(`input_schema`)로 강제. 실패 시 1회 재시도, 두 번째 실패는 chunk 전체 `EXTRACTION_FAILED` 기록.

---

### 11.7.2 GraphRAG QA 프롬프트 (`prompts/qa_default.j2`)

```
[System]
너는 이커머스 주문/결제/환불 도메인 전문가다.
아래 "Graph Context"와 "Document Evidence"에 명시된 내용만 근거로 답하라.

[금지사항]
- 제공된 근거 외 사실 추론 금지.
- 모르면 반드시 "근거 부족: 추가 자료 필요"라고 답한다.
- Graph Context와 Document Evidence를 섞지 말고 근거 종류를 구분하여 인용한다.
- 외부 일반 상식을 답변에 사용하지 마라.

[Graph Context]
{% if graph_triples %}
{% for tri in graph_triples %}
- {{ tri.source }} {{ tri.relation }} {{ tri.target }}
{% endfor %}
{% else %}
(없음)
{% endif %}

[Document Evidence]
{% if chunks %}
{% for c in chunks %}
- chunk_id={{ c.chunk_id }} (document_id={{ c.document_id }}):
  "{{ c.text }}"
{% endfor %}
{% else %}
(없음)
{% endif %}

[User Question]
{{ question }}

[Answer Format]
1. 결론: (한 문장)
2. 근거:
   - Graph 근거: (위 Graph Context에서 사용한 triple만 그대로 인용)
   - 문서 근거: (chunk_id 와 함께 한 문장 인용)
3. 필요한 후속 액션: (없으면 "없음")
```

---

## 11.8 Neo4j Cypher

### 11.8.1 부팅 시 1회 (제약/인덱스)

```cypher
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
  FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT entity_norm_type_unique IF NOT EXISTS
  FOR (e:Entity) REQUIRE (e.normalized_name, e.type_code) IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
  FOR (c:DocumentChunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE INDEX entity_type_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.type_code);
```

### 11.8.2 Entity 적재 (MERGE 기반)

```cypher
MERGE (e:Entity {normalized_name: $normalized_name, type_code: $type_code})
ON CREATE SET
  e.id = $id,
  e.name = $name,
  e.version = 1,
  e.source_document_id = $document_id,
  e.source_chunk_id = $chunk_id,
  e.review_id = $review_id,
  e.created_by = $reviewer,
  e.created_at = datetime()
ON MATCH SET
  e.name = $name,
  e.version = e.version + 1,
  e.review_id = $review_id,
  e.updated_at = datetime()
WITH e
CALL apoc.create.addLabels(e, [$type_code]) YIELD node
WITH node
MERGE (c:DocumentChunk {chunk_id: $chunk_id})
  ON CREATE SET c.document_id = $document_id, c.seq = $seq, c.text_preview = $preview
MERGE (node)-[r:DEFINED_IN]->(c)
  ON CREATE SET r.created_at = datetime(), r.review_id = $review_id
RETURN node.id AS entity_id;
```

### 11.8.3 Relation 적재 (confidence 포함)

```cypher
MATCH (s:Entity {normalized_name: $source_norm, type_code: $source_type})
MATCH (t:Entity {normalized_name: $target_norm, type_code: $target_type})
CALL apoc.merge.relationship(
  s,
  $rel_type,
  {review_id: $review_id},                                        // 식별 키
  {                                                               // ON CREATE
    source_document_id: $document_id,
    source_chunk_id: $chunk_id,
    version: 1,
    confidence: $confidence,
    created_by: $reviewer,
    created_at: datetime()
  },
  t,
  {                                                               // ON MATCH
    confidence: $confidence,
    version: coalesce(0, 0) + 1,
    updated_at: datetime()
  }
) YIELD rel
WITH rel, s, t
MATCH (c:DocumentChunk {chunk_id: $chunk_id})
MERGE (s)-[:DEFINED_IN]->(c)
MERGE (t)-[:DEFINED_IN]->(c)
RETURN id(rel) AS neo4j_rel_id;
```

### 11.8.4 Subgraph 검색 (질의용)

예: "배송 시작 전 결제 완료 주문은 전체 취소 가능한가?"
시드 후보 = `["Order","PaymentCompleted","DeliveryNotStarted","FullCancelPolicy"]` (intent extractor 결과)

```cypher
// 1) 시드에 닿는 정책 + 조건 + 적용대상 + 근거 chunk
WITH $seeds AS seeds
MATCH (n:Entity)
WHERE n.normalized_name IN seeds
WITH collect(DISTINCT n) AS seedNodes
UNWIND seedNodes AS s
CALL apoc.path.subgraphAll(s, {
  maxLevel: $depth,
  relationshipFilter: 'REQUIRES>|APPLIES_TO>|REFUNDS>|PAID_BY>|CONTAINS>|DEFINED_IN>'
}) YIELD nodes, relationships
WITH collect(nodes) AS ns, collect(relationships) AS rs
UNWIND ns AS nodeList UNWIND nodeList AS node
WITH collect(DISTINCT node) AS allNodes, rs
UNWIND rs AS relList UNWIND relList AS rel
WITH allNodes, collect(DISTINCT rel) AS allRels

// 2) 정책/조건/적용대상 분리
WITH
  [n IN allNodes WHERE 'Policy' IN labels(n)] AS policies,
  [n IN allNodes WHERE 'Condition' IN labels(n)] AS conditions,
  [n IN allNodes WHERE any(l IN ['Order','Payment','Refund'] WHERE l IN labels(n))] AS targets,
  [n IN allNodes WHERE 'DocumentChunk' IN labels(n)] AS chunks,
  allRels AS rels

RETURN
  [p IN policies | {id:p.id, name:p.normalized_name, type:p.type_code}] AS policies,
  [c IN conditions | {id:c.id, name:c.normalized_name}] AS conditions,
  [t IN targets | {id:t.id, name:t.normalized_name, type:t.type_code}] AS targets,
  [ch IN chunks | ch.chunk_id] AS evidence_chunk_ids,
  [r IN rels WHERE type(r) <> 'DEFINED_IN' |
    {source: startNode(r).normalized_name,
     relation: type(r),
     target: endNode(r).normalized_name,
     confidence: coalesce(r.confidence, null)}] AS paths;
```

### 11.8.5 단일 노드 1-hop (graph preview)

```cypher
MATCH (e:Entity {normalized_name: $name})
OPTIONAL MATCH (e)-[r]-(m:Entity)
RETURN e, collect({rel: type(r), neighbor: m.normalized_name, dir: CASE WHEN startNode(r) = e THEN 'OUT' ELSE 'IN' END}) AS neighbors;
```

---

## 11.9 GraphRAG 질의 흐름 (런타임 의사코드)

```python
# app/services/qa_service.py
async def answer(self, question: str, opts: QAOptions) -> QAAnswer:
    started = monotonic()

    # 1) Intent + Entity 추출 (작은 모델)
    intent = await self.llm_small.complete_json(
        self.prompt_builder.build_intent(question),
        schema=IntentResponse,
    )

    # 2) Graph Retriever
    seeds = [e.normalized_name for e in intent.entities] or [question]
    graph_ctx = await self.graph_retriever.subgraph(
        seeds=seeds, depth=opts.graph_depth, type_filter=None,
    )

    # 3) Vector Retriever (graph evidence chunk 우선, 모자라면 free search)
    primary = await self.vector_retriever.search(
        query=question, top_k=opts.top_k_chunks,
        chunk_id_in=graph_ctx.evidence_chunk_ids or None,
    )
    if len(primary) < opts.top_k_chunks:
        extra = await self.vector_retriever.search(
            query=question, top_k=opts.top_k_chunks - len(primary), chunk_id_in=None,
        )
        chunks = dedupe(primary + extra)
    else:
        chunks = primary

    # 4) Context Builder
    ctx = self.context_builder.build(graph_ctx, chunks, token_budget=3500)

    # 5) Prompt Builder
    rendered = self.prompt_builder.build_qa(ctx, question, template_name=opts.prompt_template)

    # 6) LLM Gateway (메인 답변)
    answer, usage = await self.llm_main.complete(rendered)

    # 7) Audit
    trace_id = await self.audit.log_query(
        question=question,
        intent=intent.model_dump(),
        graph_context=ctx.graph.model_dump(),
        vector_context=[c.chunk_id for c in chunks],
        rendered_prompt=rendered.text,
        answer=answer.text,
        provider=self.llm_main.provider,
        model=self.llm_main.model,
        latency_ms=int((monotonic() - started) * 1000),
        usage=usage,
    )

    return QAAnswer(
        answer=answer.text,
        evidence=Evidence(graph=ctx.graph.triples, chunks=chunks),
        trace_id=trace_id,
    )
```

폴백 규칙 요약 (§7.4 참조):
- intent 실패 → seeds=[]로 graph_ctx 빈 객체, vector only
- graph 0건 → graph_context "(없음)"
- vector 0건 → answer 강제 "근거 부족"
- LLM 5xx → backoff 2회 후 5xx 그대로 노출

---

## 11.10 개발 체크리스트 (실행 순서)

### W0. 환경
- [ ] `docker-compose.yml` + `.env.example` 작성
- [ ] `Dockerfile` 작성, `pyproject.toml`(FastAPI, sqlalchemy, alembic, neo4j, qdrant-client, openai, anthropic, jinja2, pydantic-settings, httpx, pytest, ruff, black, mypy)
- [ ] `docker compose up -d postgres neo4j qdrant` 정상 healthcheck
- [ ] FastAPI hello + `/health` 200

### W1. 문서/Chunk/Vector
- [ ] Alembic init + `0001_init` ENUM + document + chunk
- [ ] `core/config.py` (Pydantic Settings), `core/security.py`(X-Admin-Token), `core/errors.py`
- [ ] `repositories/document_repo.py`, `chunk_repo.py`
- [ ] `services/chunking_service.py` (문장 split + token window)
- [ ] `integrations/embedding/{base,openai_embed,fake_embed}.py`
- [ ] `repositories/qdrant_repo.py` (collection ensure, upsert, search)
- [ ] `workers/chunk_embed_worker.py`
- [ ] `api/v1/endpoints/documents.py` (P1-1~3), `chunks.py` (P1-4~5)
- [ ] `services/audit_service.py` + audit_log 테이블 → `DOC_UPLOAD` 기록
- [ ] 통합 테스트: 문서 업로드 → chunk INDEXED → Qdrant point 존재

### W2. Ontology Schema + Extraction + Review
- [ ] `0002_ontology` + `0003_staging` + 검증 트리거 + `0006_audit/ai_query_log` 일부
- [ ] `seeds/ontology_seed.py` (이커머스 type)
- [ ] `repositories/ontology_repo.py`, `staging_repo.py`
- [ ] `services/ontology_schema_service.py`
- [ ] `api/v1/endpoints/ontology.py` (P2)
- [ ] `integrations/llm/{base, openai_provider, anthropic_provider, fake_provider}.py`
- [ ] `prompts/extraction.*.j2` + `schemas/candidate.py`
- [ ] `services/extraction_service.py` + `workers/extraction_worker.py`
- [ ] `api/v1/endpoints/candidates.py` (P3-1~3)
- [ ] `services/review_service.py` (approve/reject/modify/merge)
- [ ] 통합 테스트: 1개 문서 → extract → staging row N → approve → status APPROVED
- [ ] audit 기록 (`EXTRACTION_RUN`, `REVIEW_APPROVE/REJECT/MODIFY/MERGE`)

### W3. Neo4j 적재 + Graph 조회
- [ ] `0004_graph_sync` 마이그
- [ ] `db/neo4j_client.py` + 부팅 시 §11.8.1 제약/인덱스 ensure
- [ ] `repositories/neo4j_repo.py` (entity_upsert, relation_upsert, subgraph)
- [ ] `services/graph_sync_service.py` + approve 직후 trigger + `POST /graph/sync` 일괄
- [ ] `services/graph_retriever.py`
- [ ] `api/v1/endpoints/graph.py` (P4-1~3, 4는 옵션)
- [ ] 통합 테스트: approve → Neo4j MATCH로 노드/관계/DEFINED_IN 존재 검증
- [ ] sync 실패 케이스: APPROVED relation인데 source 누락 → 의미있는 에러

### W4. GraphRAG QA + Audit
- [ ] `0005_prompt` 마이그 + `seeds/prompt_seed.py` (qa_default, extraction_default)
- [ ] `services/prompt_builder.py` (jinja2 렌더 + active version 로드)
- [ ] `services/vector_retriever.py` (graph evidence 우선 → 부족 시 free)
- [ ] `services/context_builder.py` (token budget cut, dedupe)
- [ ] `prompts/qa_default.j2`
- [ ] `services/qa_service.py` + intent용 작은 LLM 호출
- [ ] `api/v1/endpoints/qa.py` (P5-1)
- [ ] `api/v1/endpoints/audit.py` (P5-2)
- [ ] 통합 테스트: 시나리오 "주문 O1001 환불 가능한가?" → answer + evidence + trace_id, `ai_query_log` row 존재
- [ ] 데모용 sample documents 스크립트 (`scripts/load_sample_docs.py`)

### 마무리
- [ ] README에 60초 데모 시나리오 추가
- [ ] Postman/Insomnia collection 또는 `/docs` 안내
- [ ] (옵션) React Admin은 W2부터 점진적

---

## 11.11 MVP 완성 기준 (Definition of Done)

다음 시나리오가 **로컬 `docker compose up` 단일 명령 후 처음부터 끝까지 통과**해야 MVP 완료다.

1. **환경**: `docker compose up -d` → 4개 컨테이너 healthy. `/health` 200.
2. **Seed 확인**: `GET /api/v1/ontology/entity-types`가 8종 반환. `GET /ontology/relation-types`가 6종 이상.
3. **문서 업로드**: `POST /documents` 환불 정책 텍스트 → 60초 내 `chunk_count > 0`, 모든 chunk `vector_status=INDEXED`. Qdrant 콜렉션에 동일 수의 point 존재.
4. **추출**: `POST /documents/{id}/extract` → 60초 내 staging entity ≥ 3, relation ≥ 2. 스키마 위반 출력은 자동 REJECTED로 기록.
5. **검수**: entity 3+, relation 2+ approve → `extracted_entity.status=APPROVED`, `graph_sync_log`에 CREATE 기록.
6. **Neo4j 검증**: Neo4j Browser에서 `MATCH (e:Entity)-[:DEFINED_IN]->(c:DocumentChunk) RETURN e,c LIMIT 25` 반환 ≥ 3.
7. **GraphRAG QA**: `POST /qa { "question": "주문 O1001은 환불 가능한가?" }` →
   - `answer`에 결론/근거/후속 액션 3섹션 포함
   - `evidence.graph`에 최소 1개 triple, `evidence.chunks`에 최소 1개 chunk_id
   - `trace_id` 반환
8. **Audit**: `GET /qa/logs/{trace_id}` → `rendered_prompt`, `answer`, `token_input/output`, `latency_ms` 모두 존재.
9. **거버넌스 가드 동작 확인**:
   - 스키마 위반 relation을 직접 staging insert 시도 → DB 트리거가 거부.
   - relation approve를 source가 APPROVED가 아닌 상태에서 호출 → 409 `NOT_APPROVED_SOURCE`.
   - 추출은 staging만 친다 (직접 Neo4j 적재 경로 없음 = 코드 grep으로 검증).
10. **운영**: 모든 변경 API에 audit_log 1건 이상 기록 (DOC_UPLOAD / EXTRACTION_RUN / REVIEW_* / GRAPH_SYNC / QUERY).

위 10가지가 자동 또는 수동으로 통과되면 MVP DoD 충족.
