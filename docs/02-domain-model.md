# 2. 도메인 모델 설계

## 2.1 개요 (Class diagram)

```mermaid
classDiagram
  class Document {
    +UUID id
    +str title
    +str domain
    +int version
    +str access_level
    +str uri
    +datetime created_at
  }
  class DocumentChunk {
    +UUID id
    +UUID document_id
    +int seq
    +str text
    +str checksum
    +int token_count
    +str vector_status  // PENDING/INDEXED/FAILED
  }
  class OntologyEntityType {
    +str code   // Policy / Condition / Order ...
    +str label
    +json json_schema
  }
  class OntologyRelationType {
    +str code   // REQUIRES / APPLIES_TO ...
    +str source_type
    +str target_type
    +bool symmetric
  }
  class ExtractedEntity {
    +UUID id
    +UUID chunk_id
    +str name
    +str normalized_name
    +str type_code
    +float confidence
    +ReviewStatus status
    +UUID merged_into
  }
  class ExtractedRelation {
    +UUID id
    +UUID chunk_id
    +UUID source_entity_id
    +UUID target_entity_id
    +str type_code
    +float confidence
    +ReviewStatus status
  }
  class ReviewStatus {
    <<enum>>
    PENDING
    APPROVED
    REJECTED
    MODIFIED
  }
  class GraphSyncLog {
    +UUID id
    +str object_kind   // ENTITY / RELATION
    +UUID staging_id
    +str neo4j_id
    +str action        // CREATE / UPDATE / DELETE
    +datetime synced_at
  }
  class AuditLog {
    +UUID id
    +str event_type    // QUERY / REVIEW / SCHEMA_CHANGE
    +UUID actor_id
    +json payload
    +datetime created_at
  }
  class PromptTemplate {
    +UUID id
    +str name
    +int version
    +str body
    +bool is_active
  }

  Document "1" --> "*" DocumentChunk
  DocumentChunk "1" --> "*" ExtractedEntity
  DocumentChunk "1" --> "*" ExtractedRelation
  ExtractedEntity "1" --> "*" ExtractedRelation : source
  ExtractedEntity "1" --> "*" ExtractedRelation : target
  OntologyEntityType "1" --> "*" ExtractedEntity
  OntologyRelationType "1" --> "*" ExtractedRelation
  ExtractedEntity --> GraphSyncLog
  ExtractedRelation --> GraphSyncLog
```

## 2.2 핵심 불변식 (Invariants)

1. `ExtractedRelation`은 두 `ExtractedEntity`(source, target)가 모두 `APPROVED` 상태여야 `APPROVED` 가능.
2. `(source_type, type_code, target_type)` 조합은 반드시 `OntologyRelationType`에 존재해야 한다. 위반 시 LLM 출력은 자동 `REJECTED`.
3. 모든 `APPROVED` Entity/Relation은 `GraphSyncLog`에 1건 이상 기록되어야 한다.
4. `normalized_name`은 같은 `type_code` 내에서 unique. 중복 시 admin이 **merge** 액션으로 병합 (`merged_into` 세팅).
5. `DocumentChunk.checksum` 변경 시 해당 chunk에서 파생된 staging 엔트리는 invalidate.

## 2.3 ReviewStatus 전이도

```mermaid
stateDiagram-v2
  [*] --> PENDING
  PENDING --> APPROVED: admin approve
  PENDING --> REJECTED: admin reject (reason)
  PENDING --> MODIFIED: admin edit (name/type)
  MODIFIED --> APPROVED: re-approve
  APPROVED --> [*]: synced to Neo4j
  REJECTED --> [*]
```

## 2.4 정규화 규칙 (normalized_name)

- 한글/영문 혼용 명사 → snake/Pascal 변환 후 영문 우선
  - "전체 취소 정책" → `FullCancelPolicy`
  - "결제 완료" → `PaymentCompleted`
- Extractor가 1차 제안, admin이 수정 시 audit 기록.

## 2.5 Ontology Seed (이커머스 도메인)

| Entity Type | 설명 |
|---|---|
| Order | 주문 |
| OrderItem | 주문 상품 |
| Product | 상품 |
| Payment | 결제 |
| Refund | 환불 |
| Delivery | 배송 |
| Policy | 정책 |
| Condition | 조건 |

| Relation | Source → Target |
|---|---|
| CONTAINS | Order → OrderItem |
| PAID_BY | Order → Payment |
| REFUNDS | Refund → Payment |
| APPLIES_TO | Policy → Order \| Refund \| Payment |
| REQUIRES | Policy → Condition |
| DEFINED_IN | * → DocumentChunk (자동) |
