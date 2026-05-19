# 4. Neo4j 그래프 모델 설계

## 4.1 Node Labels

| Label | 설명 | 주요 Property |
|---|---|---|
| `:Entity` | 공통 부모 (모든 도메인 노드에 부착) | `id`, `normalized_name`, `name`, `type_code`, `version`, `source_document_id`, `source_chunk_id`, `created_at`, `updated_at` |
| `:Policy` | 정책 | + `applies_domain` |
| `:Condition` | 조건 | - |
| `:Order` | 주문 개념 노드 | - |
| `:OrderItem` | - | - |
| `:Product` | - | - |
| `:Payment` | - | - |
| `:Refund` | - | - |
| `:Delivery` | - | - |
| `:DocumentChunk` | 원문 chunk (근거 추적용) | `chunk_id`, `document_id`, `seq`, `text_preview`, `checksum` |

> 도메인 노드는 항상 `:Entity` 라벨을 함께 가집니다 (`(:Entity:Policy)`). 공통 인덱스/쿼리에 유리.

## 4.2 Relationship Types

| Type | Source → Target | 비고 |
|---|---|---|
| `:CONTAINS` | Order → OrderItem | |
| `:PAID_BY` | Order → Payment | |
| `:REFUNDS` | Refund → Payment | |
| `:APPLIES_TO` | Policy → Order \| Refund \| Payment | |
| `:REQUIRES` | Policy → Condition | |
| `:DEFINED_IN` | Entity / Relation → DocumentChunk | 근거 추적 |
| `:SUPERSEDES` | Entity → Entity (이전 버전) | 버전 변경 시 |

모든 관계 공통 property: `staging_id`, `source_chunk_id`, `version`, `created_at`, `created_by`.

## 4.3 제약/인덱스

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

## 4.4 적재 Cypher (Graph Loader)

### Entity Upsert

```cypher
MERGE (e:Entity {id: $id})
ON CREATE SET
  e.normalized_name = $normalized_name,
  e.name = $name,
  e.type_code = $type_code,
  e.version = 1,
  e.source_document_id = $document_id,
  e.source_chunk_id = $chunk_id,
  e.created_at = datetime()
ON MATCH SET
  e.name = $name,
  e.version = e.version + 1,
  e.updated_at = datetime()
WITH e
CALL apoc.create.addLabels(e, [$type_code]) YIELD node
RETURN node;
```

### DEFINED_IN 연결

```cypher
MATCH (e:Entity {id: $entity_id})
MERGE (c:DocumentChunk {chunk_id: $chunk_id})
  ON CREATE SET c.document_id = $document_id, c.seq = $seq, c.text_preview = $preview
MERGE (e)-[r:DEFINED_IN]->(c)
  ON CREATE SET r.created_at = datetime(), r.staging_id = $staging_id;
```

### Relation Upsert

```cypher
MATCH (s:Entity {id: $source_id}), (t:Entity {id: $target_id})
CALL apoc.merge.relationship(s, $type_code,
  {staging_id: $staging_id},
  {version: 1, source_chunk_id: $chunk_id, created_at: datetime()},
  t,
  {updated_at: datetime()}
) YIELD rel
RETURN rel;
```

## 4.5 Query 시 Subgraph Retrieval

### Q. "주문 O1001은 환불 가능한가?" → 관련 정책/조건 탐색

```cypher
// 1) 주문/환불에 적용되는 정책과 그 조건들
MATCH (p:Policy)-[:APPLIES_TO]->(target:Entity)
WHERE target.type_code IN ['Order','Refund','Payment']
OPTIONAL MATCH (p)-[:REQUIRES]->(c:Condition)
OPTIONAL MATCH (p)-[:DEFINED_IN]->(doc:DocumentChunk)
RETURN p, collect(DISTINCT c) AS conditions, collect(DISTINCT doc.chunk_id) AS evidence_chunks
LIMIT 20;
```

### Subgraph 시각 형태

```
(FullCancelPolicy:Policy)
  ├─[:APPLIES_TO]→ (:Order)
  ├─[:REQUIRES]→ (PaymentCompleted:Condition)
  ├─[:REQUIRES]→ (DeliveryNotStarted:Condition)
  └─[:DEFINED_IN]→ (chunk_003:DocumentChunk)
```

## 4.6 변경 이력 처리 (간단)

MVP에서는 **append-only `graph_sync_log` + Entity `version` 증분**으로 처리.
완전한 시점 조회(time-travel)는 v2 범위. 현재는 가장 최근 버전만 Neo4j에 유지하고, 히스토리는 Postgres `graph_sync_log` 조회.
