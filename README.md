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
