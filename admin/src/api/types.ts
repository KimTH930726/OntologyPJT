export type ReviewStatus = "PENDING" | "APPROVED" | "REJECTED" | "MERGED";
export type VectorStatus = "INDEXED" | "PENDING" | "FAILED";

export interface DocumentOut {
  id: string;
  title: string;
  domain: string;
  source_type: string;
  version: string;
  access_level: string;
  content_hash: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentOut {
  chunk_count: number;
  vector_status: string;
}

export interface DocumentCreated {
  document_id: string;
  chunk_count: number;
  vector_status: string;
}

export interface ChunkOut {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  token_count: number;
  text_hash: string;
  vector_status: string;
  qdrant_point_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedEntity {
  id: string;
  document_id: string;
  chunk_id: string;
  entity_type: string;
  name: string;
  normalized_name: string;
  confidence: number | string;
  evidence_text: string | null;
  source: string;
  review_status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  merged_into_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedRelation {
  id: string;
  document_id: string;
  chunk_id: string;
  source_entity_id: string | null;
  source_entity_name: string;
  source_entity_type: string;
  relation_type: string;
  target_entity_id: string | null;
  target_entity_name: string;
  target_entity_type: string;
  confidence: number | string;
  evidence_text: string | null;
  source: string;
  review_status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractionRunResponse {
  document_id: string;
  chunk_ids: string[];
  entities_extracted: number;
  relations_extracted: number;
  schema_violations: number;
  audit_log_id: string | null;
}

export interface OntologyEntityType {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OntologyRelationType {
  id: string;
  source_entity_type: string;
  relation_name: string;
  target_entity_type: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GraphSyncResult {
  entity_success: number;
  entity_failed: number;
  entity_skipped: number;
  relation_success: number;
  relation_failed: number;
  relation_skipped: number;
}

export interface GraphSyncLog {
  id: string;
  target_type: string;
  target_id: string;
  sync_status: string;
  neo4j_node_id: string | null;
  neo4j_relation_id: string | null;
  error_message: string | null;
  synced_at: string | null;
  created_at: string;
}

export interface GraphNode {
  id: string;
  type: string;
  normalized_name: string;
  name: string | null;
}

export interface GraphRelationship {
  id: string | null;
  source: string;
  target: string;
  relation: string;
  confidence: number | null;
  chunk_id: string | null;
}

export interface SubgraphResponse {
  seed: string;
  depth: number;
  nodes: GraphNode[];
  relationships: GraphRelationship[];
}

export interface GraphEntityResponse {
  id: string;
  type: string;
  name: string;
  normalized_name: string;
  source_document_id: string | null;
  chunk_id: string | null;
  confidence: number | null;
  defined_in: {
    chunk_id: string;
    document_id: string | null;
    text: string | null;
  }[];
}

export interface QAResponse {
  answer: string;
  graph_context: { seed_entities: string[]; triple_count: number };
  document_evidence: { chunk_count: number };
  query_log_id: string;
}

export interface AIQueryLog {
  id: string;
  question: string;
  detected_entities_json: unknown;
  graph_context_json: unknown;
  retrieved_chunks_json: unknown;
  final_prompt: string;
  answer: string | null;
  model_provider: string | null;
  model_name: string | null;
  token_estimate: number | null;
  latency_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  action: string;
  actor: string | null;
  target_type: string | null;
  target_id: string | null;
  document_id: string | null;
  chunk_id: string | null;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface HealthResponse {
  status: "ok" | "down";
  services: Record<string, "ok" | "down">;
  errors: Record<string, string>;
}
