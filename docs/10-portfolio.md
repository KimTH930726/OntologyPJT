# 10. 포트폴리오 메시지

## 10.1 한 줄 포지셔닝

> **Enterprise AI Platform Backend Engineer**
> with hands-on design of **Ontology / Knowledge Graph / GraphRAG / AI Governance**.

## 10.2 이력서 1-문단 설명

> 사내 정책 문서에서 LLM이 추출한 엔티티/관계 후보를 도메인 전문가가 검수·승인해야만 Graph DB(Neo4j)에 적재되도록 한 **거버넌스형 GraphRAG MVP**를 설계·구현. 질의 시 관련 Subgraph를 먼저 탐색하고, 해당 노드의 근거 chunk를 Qdrant에서 보강하여 LLM 프롬프트를 증강. 모든 질의/검색/프롬프트/답변은 Audit Log로 남겨 **AI Governance**를 백엔드 단에서 구조화. FastAPI/Postgres/Neo4j/Qdrant + Docker Compose 기반, Spring Boot/JPA 기반 엔터프라이즈로 확장 가능한 구조로 설계.

## 10.3 면접에서 설명할 때 (STAR)

- **Situation**: 기존 Vector-only RAG는 "결제와 환불의 관계", "환불 가능 조건" 같은 **규칙·관계 질의**에 약하다.
- **Task**: 도메인 지식을 LLM이 자유 생성하게 두지 않고, **사람이 승인한 지식만** 답변 근거가 되도록 한다.
- **Action**:
  - Ontology Schema(허용 Entity/Relation)를 사람이 정의 → LLM 출력은 이 스키마에 강제 (function calling + DB trigger 이중 검증)
  - LLM 추출 결과는 **Staging Table**로 격리 → admin 검수 → APPROVED만 Neo4j 적재
  - 모든 Graph Node/Edge는 `DEFINED_IN → DocumentChunk`로 원문 근거를 보존
  - 질의 시 Graph Retriever가 먼저 Subgraph를 찾고, Vector Retriever가 chunk 근거 보강
  - 질의/Prompt/Answer를 `ai_query_log`에 영속화하여 거버넌스 확보
- **Result**: 단순 챗봇이 아닌 **"왜 이 답이 나왔는가"를 그래프 + 근거 + 승인자까지 역추적 가능한** 구조 완성.

## 10.4 어필 가능한 7가지 역량 (요청 그대로)

1. RAG 고도화 이해 — Vector / Graph 역할 분리, 한계와 보완
2. Ontology / Knowledge Graph 기반 지식 관리 — Schema-first
3. LLM 기반 Entity/Relation 추출 — Schema-constrained, JSON 강제, 이중 검증
4. 도메인 전문가 검수 플로우 — Staging + 상태기계 + UI/UX
5. GraphRAG 질의 응답 구조 — Subgraph-first, evidence-backed
6. AI Governance / Audit Log — 질의/Prompt/Answer 영속화, 변경 이력
7. Enterprise AI Platform Backend 설계 — 모듈 경계, v2 Spring Boot 확장 전제

## 10.5 면접 예상 질문 & 답변 포인트

- "왜 Vector + Graph를 같이 썼나?"
  - Vector는 **어떤 문서가 비슷한가**에 강하고, Graph는 **어떤 개념이 어떻게 연결되었는가**에 강하다. 정책/규칙 질의는 후자가 필수.
- "LLM이 만든 그래프를 그대로 쓰면 안 되나?"
  - 환각·일관성 위반·중복 normalized_name 문제. Staging + Review + Schema 검증 트리거로 거버넌스 확보.
- "Schema-constrained 추출은 어떻게 보장?"
  - (1) prompt에 active relation type 주입 (2) JSON 강제 (response_format/function calling) (3) pydantic 검증 (4) DB 트리거로 source/target 타입 매칭 검증.
- "왜 FastAPI? Spring Boot가 아니고?"
  - 1차 목표는 구조 검증/빠른 실험. LLM/Embedding 생태계가 Python이 유리. 2차에서 DDD/JPA 기반 Spring Boot로 확장하는 것을 전제로 모듈 경계를 설계.
- "확장성은?"
  - 모듈 12개가 명확한 경계로 분리되어 있고, Spring Boot로 재구현 시 그대로 매핑 가능. 비동기는 Kafka 도입 지점, 권한은 RBAC 도입 지점이 미리 표시되어 있다.
- "비용 통제는?"
  - chunk 상한, embedding은 checksum 캐시, 모든 호출 token usage를 `ai_query_log`에 적재.

## 10.6 데모 시나리오 (60초)

1. 환불 정책 문서 업로드 → chunk 인덱싱
2. `/candidates` 화면에서 LLM 후보 검수 → approve 3개
3. `/graph`에서 `FullCancelPolicy` 노드 + REQUIRES 관계 시각화
4. `/qa`에 "주문 O1001은 환불 가능한가?" 질의 → answer + graph + chunk evidence + rendered prompt 모두 표시
5. `/audit`에서 방금 질의가 로그로 남은 것 확인
