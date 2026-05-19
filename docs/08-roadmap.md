# 8. MVP 개발 로드맵 (4주)

> 1주 = 약 15~20시간 (저녁/주말). 매주 끝에 demo-able 산출물.

## Week 0 (사전 0.5주, 선택)

- Docker Compose: Postgres / Neo4j / Qdrant / FastAPI / (option: pgAdmin, Neo4j Browser)
- Python repo scaffold: `app/`, `app/core`, `app/api`, `app/services`, `app/repositories`
- Lint/Test: ruff + pytest + httpx
- Seed: `ontology_entity_type`, `ontology_relation_type` (이커머스)
- 결과물: `docker compose up` 후 `/health` 200

## Week 1 — Document / Chunk / Schema 기반

Goals
- 문서 업로드 + Chunking + Embedding + Qdrant 적재
- Ontology Schema CRUD + 활성 seed
- Admin UI: 문서 목록 / 상세 (Chunks)

Tasks
- DDL 적용 (Alembic migration v1)
- `POST /documents`, `GET /documents/:id/chunks`
- Chunking 규칙: 문장 단위 + 600~800 tokens window, overlap 80
- Embedding worker (BackgroundTasks) → Qdrant upsert
- React: layout + 문서 목록/상세

Done = 문서를 올리면 chunk_status가 INDEXED가 되고 Qdrant에 점이 생긴다.

## Week 2 — LLM Extractor + Review Admin

Goals
- LLM Extractor (schema-constrained) → Staging Table
- Review API + Admin 검수 화면
- Schema 위반 자동 reject + 트리거로 DB 일관성 보장

Tasks
- Prompt: system에 active entity/relation types 주입, JSON 강제 (function calling / response_format)
- Validation: pydantic으로 출력 검증, 위반 시 `status=REJECTED, reason=SCHEMA_VIOLATION`
- `/candidates/*` API 전부
- React: `/candidates` 검수 화면 (좌-원문 / 우-카드)
- Audit Log 시작 (REVIEW_APPROVE/REJECT/MODIFY/MERGE)

Done = 1개 문서로 후보 N개 생성 → admin이 클릭으로 승인까지 가능.

## Week 3 — Neo4j 적재 + Graph Retriever

Goals
- Graph Loader: APPROVED → Neo4j upsert + DEFINED_IN
- Graph Retriever: subgraph API
- Admin UI: Graph 미리보기 (vis-network)

Tasks
- Neo4j 제약/인덱스 생성 마이그레이션
- `POST /graph/sync` 일괄 & 승인 직후 자동 trigger 동시 지원
- `GET /graph/subgraph?seed=...&depth=...`
- React: `/graph` 시각화 + node click → DEFINED_IN chunk 패널

Done = 승인된 데이터가 Neo4j Browser에서 보이고, Admin UI에서도 그래프 탐색 가능.

## Week 4 — GraphRAG QA + Audit

Goals
- `POST /qa` end-to-end
- Prompt template / version 관리
- Audit log 화면 + 질의 테스트 화면

Tasks
- Intent/Entity 추출 (작은 모델)
- Context Builder + token budget
- Prompt Builder (jinja2) + `prompt_template/version` seed
- LLM Gateway: openai + anthropic 어댑터
- `ai_query_log` 기록 + `/qa/logs` API
- React: `/qa`, `/audit`
- README demo 시나리오 + 짧은 영상/스크립트

Done = "주문 O1001은 환불 가능한가?" 질의에 graph+evidence+answer가 반환되고 audit에 남는다.

## 마일스톤 체크리스트

- [ ] W1: 문서 업로드 → chunk 인덱싱
- [ ] W2: 후보 추출 + 검수 승인
- [ ] W3: Neo4j 적재 + 시각화
- [ ] W4: GraphRAG QA + Audit
- [ ] 데모 영상 60초

## 리스크 & 완화

| 리스크 | 완화 |
|---|---|
| LLM 출력 JSON 깨짐 | function calling / json_mode 강제 + pydantic 재시도 1회 |
| normalized_name 중복 폭증 | admin "merge" UX 우선 구현 |
| Neo4j 학습 곡선 | apoc, MERGE 패턴만으로 한정 |
| 토큰 비용 | extractor chunk 상한, embedding은 캐시(checksum) |
