# Ontology-Grounded RAG Governance Platform (MVP)

> 원문 문서에서 엔티티/관계 후보를 추출하고, 도메인 전문가가 검수·승인한 지식만 Graph DB에 적재한 뒤,
> 질문 시 관련 Subgraph와 문서 Chunk를 함께 찾아 LLM 프롬프트를 증강하는 **GraphRAG + AI Governance** 플랫폼.

---

## 한 줄 포지셔닝

**Enterprise AI Platform Backend** with **Ontology / Knowledge Graph / GraphRAG / AI Governance**.

## 왜 이 프로젝트인가

기존 Vector RAG는 문서 유사도 검색에는 강하지만 도메인 개념 간 **관계 / 규칙 / 정책 / 상태 판단**에는 약합니다.
이 MVP는 다음을 풀기 위한 구조 학습 프로젝트입니다.

- 주문은 결제와 어떤 관계인가
- 환불은 어떤 조건에서 가능한가
- 특정 정책은 어떤 엔티티에 적용되는가
- 이 답변의 **근거 원문**은 무엇이고 **누가 승인**한 지식인가

## 기술 스택 (MVP v1)

| Layer | 선택 |
|---|---|
| Backend | **FastAPI** (Python) |
| RDB | PostgreSQL (문서/Chunk/Staging/Audit) |
| Graph DB | Neo4j (승인된 Ontology Instance) |
| Vector DB | Qdrant (Chunk Embedding) |
| LLM | OpenAI / Claude API (Gateway 추상화) |
| Frontend | React (간단한 Admin UI) |
| Infra | Docker Compose (local-first) |

> v2에서 Spring Boot + JPA 기반 엔터프라이즈 백엔드로 확장 가능한 구조를 전제로 설계합니다.

## 설계 원칙 (불변)

1. LLM 추출 결과를 Graph DB에 **바로 넣지 않는다**.
2. 모든 후보는 **Staging Table + Review Status**를 거친다.
3. 도메인 전문가가 승인한 지식만 Graph DB에 적재한다.
4. 모든 Graph Node / Relation은 **원문 Chunk와 연결**한다 (`DEFINED_IN`).
5. 질문 시 전체 온톨로지가 아니라 **관련 Subgraph만** LLM에 넣는다.
6. Vector DB는 **원문 근거 검색용**, Graph DB는 **개념·관계·규칙 탐색용**.
7. Audit Log에 질문/검색 결과/Prompt/답변을 남긴다.
8. MVP는 local Docker 기반으로 단순하게 시작한다.
9. 구조는 실무 엔터프라이즈 AI 플랫폼으로 확장 가능해야 한다.
10. Ontology Schema(허용 Relation)를 위반한 LLM 출력은 자동 reject.

## 문서 구성

| 문서 | 내용 |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | 전체 아키텍처 & 데이터 흐름 |
| [docs/02-domain-model.md](docs/02-domain-model.md) | 도메인 모델 |
| [docs/03-database-schema.md](docs/03-database-schema.md) | PostgreSQL DDL |
| [docs/04-graph-model.md](docs/04-graph-model.md) | Neo4j 그래프 모델 + Cypher |
| [docs/05-api-spec.md](docs/05-api-spec.md) | REST API 설계 |
| [docs/06-admin-ui.md](docs/06-admin-ui.md) | Admin UI 화면 설계 |
| [docs/07-query-sequence.md](docs/07-query-sequence.md) | 질문 응답 시퀀스 |
| [docs/08-roadmap.md](docs/08-roadmap.md) | 4주 개발 로드맵 |
| [docs/09-out-of-scope.md](docs/09-out-of-scope.md) | MVP 제외 항목 |
| [docs/10-portfolio.md](docs/10-portfolio.md) | 포트폴리오 메시지 |
| [docs/11-implementation-plan.md](docs/11-implementation-plan.md) | 구현 계획서 (디렉토리/Compose/DDL/API/서비스/Prompt/Cypher/체크리스트/DoD) |

## MVP 도메인

이커머스 **주문 / 결제 / 환불 / 정책** 도메인을 기준으로 합니다.

- Entity: `Order`, `OrderItem`, `Product`, `Payment`, `Refund`, `Delivery`, `Policy`, `Condition`
- Relation: `CONTAINS`, `PAID_BY`, `REFUNDS`, `APPLIES_TO`, `REQUIRES`, `DEFINED_IN`

---

## 실행 방법 (W0)

### 1. 환경 변수 준비

```bash
cp .env.example .env
```

기본값으로도 동작합니다. (Postgres `ontology_user/ontology_password/ontology_rag`, Neo4j `neo4j/password`)

### 2. 전체 스택 기동

```bash
docker compose up --build
```

처음 빌드는 1~3분 소요. `postgres`는 healthcheck 통과 후 `app`이 기동됩니다.

### 3. Health Check

```bash
curl http://localhost:8000/health
```

정상 응답:
```json
{
  "status": "ok",
  "services": { "postgres": "ok", "neo4j": "ok", "qdrant": "ok" },
  "errors": {}
}
```

특정 서비스가 죽어도 앱은 살아 있고 어떤 서비스가 `down`인지 표시합니다.

### 4. Alembic (W1에서 첫 마이그 추가 예정)

W0에서는 alembic 환경만 초기화되어 있습니다. 마이그 파일은 W1에서 작성합니다.

```bash
# 컨테이너 내부에서 새 마이그 생성 (W1 작업 시)
docker compose exec app alembic revision -m "init"
docker compose exec app alembic upgrade head
```

### W1 실행 (문서 → Chunk → Vector)

#### 1) 마이그레이션 적용

```bash
docker compose exec app alembic upgrade head
```

`document`, `document_chunk` 두 테이블이 생성됩니다.

#### 2) 문서 등록

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "환불 정책 v1",
    "domain": "order",
    "source_type": "policy",
    "version": "v1",
    "access_level": "internal",
    "content": "결제 완료 후 배송 시작 전에는 주문 전체 취소가 가능하다. 부분 취소는 주문상품 단위로만 가능하다. 환불 금액은 실제 결제 금액을 초과할 수 없다."
  }'
```

응답:
```json
{
  "document_id": "uuid",
  "chunk_count": 2,
  "vector_status": "INDEXED"
}
```

#### 3) Chunk 조회

```bash
curl http://localhost:8000/documents/{document_id}/chunks
curl http://localhost:8000/chunks/{chunk_id}
```

#### 4) Qdrant 확인

- `http://localhost:6333/dashboard` → `document_chunks` 컬렉션
- payload에 `chunk_id`, `document_id`, `domain`, `version`, `access_level`, `text` 포함

> 중복 등록 (같은 content 재요청)은 `409 DUPLICATE_CONTENT` + 기존 `existing_document_id` 반환.

### 5. 접속 정보

| 서비스 | URL | 비고 |
|---|---|---|
| FastAPI | http://localhost:8000 | `/docs` 자동 OpenAPI |
| Neo4j Browser | http://localhost:7474 | user=`neo4j`, pw=`password` |
| Qdrant | http://localhost:6333 | `/dashboard` (Qdrant Web UI) |
| Postgres | localhost:5432 | psql client로 접속 |
