# 9. MVP에서 제외 (Out of Scope)

> "구조 학습 + 포트폴리오 증명"이 목표. 아래는 명시적으로 제외해 과설계를 방지한다.

## 9.1 온톨로지 / 표준

- ❌ OWL / RDF / SPARQL / Reasoner
  - 이유: 학습 비용 대비 MVP 가치 낮음. 표현은 PostgreSQL + Neo4j property 모델로 충분.
- ❌ 완전 자동 온톨로지 생성 (스키마까지 LLM이 결정)
  - 이유: 본 프로젝트의 핵심 가치는 **사람-검수 거버넌스**. Schema는 사람이 정의.
- ❌ 멀티 도메인 동시 운영
  - 이커머스 한 도메인만. 도메인 분리 구조는 컬럼만 두고 미구현.

## 9.2 인증 / 권한

- ❌ RBAC / SSO / OAuth2 Authorization Code Flow
- ❌ 멀티테넌시 (tenant_id 컬럼/스코프)
- ❌ 세분화된 권한 (chunk-level access)
- ✅ 단일 admin token만

## 9.3 운영 / 인프라

- ❌ Kubernetes 매니페스트, Helm
- ❌ 운영용 대시보드 (Grafana/Prometheus 통합)
- ❌ 백업 / 재해복구 절차
- ❌ Blue-Green / Canary 배포
- ❌ 다중 노드 Neo4j Cluster
- ✅ Docker Compose 단일 노드

## 9.4 데이터 처리

- ❌ 실시간 스트리밍 (Kafka, CDC)
- ❌ 대용량 분산 임베딩 (Ray, Spark)
- ❌ OCR / 이미지/표 추출 (PDF는 텍스트만)
- ❌ 다국어 자동 감지 / 번역 파이프라인
- ✅ 한국어 텍스트 + 단일 LLM provider

## 9.5 모델 / 알고리즘

- ❌ Fine-tuning, LoRA
- ❌ Re-ranking 모델 (cross-encoder)
- ❌ Self-RAG / Multi-hop reasoning 자동화
- ❌ 자체 임베딩 모델 학습
- ✅ provider API 호출만, kNN + prompt 증강 수준

## 9.6 거버넌스 / 컴플라이언스

- ❌ PII 자동 마스킹
- ❌ 감사 보고서 자동 생성 (PDF)
- ❌ Policy-as-Code 통합 (OPA)
- ✅ audit_log 테이블 + 조회 화면

## 9.7 v2 후보 (이번 MVP에서 빼고 다음 단계 후보로 적어두기)

- Spring Boot/JPA 마이그레이션 + DDD 적용
- 권한 모델 (Project / Role / Resource)
- Time-travel 그래프 (버전 시점 조회)
- Re-ranker + Hybrid Search (BM25 + dense)
- 자동 회귀 평가 (QA truth set, eval pipeline)
- Prompt A/B + 비용 대시보드
- 멀티 도메인 / 멀티테넌시
- Kafka 기반 비동기 파이프라인
