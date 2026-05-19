import { api } from "./client";
import type {
  AIQueryLog,
  AuditLog,
  ChunkOut,
  DocumentCreated,
  DocumentDetail,
  DocumentOut,
  ExtractedEntity,
  ExtractedRelation,
  ExtractionRunResponse,
  GraphEntityResponse,
  GraphSyncLog,
  GraphSyncResult,
  HealthResponse,
  OntologyEntityType,
  OntologyRelationType,
  QAResponse,
  SubgraphResponse,
} from "./types";

// =========== health ===========
export const getHealth = () =>
  api.get<HealthResponse>("/health").then((r) => r.data);

// =========== documents ===========
export const listDocuments = (params: { domain?: string; limit?: number; offset?: number } = {}) =>
  api.get<DocumentOut[]>("/documents", { params }).then((r) => r.data);

export const getDocument = (id: string) =>
  api.get<DocumentDetail>(`/documents/${id}`).then((r) => r.data);

export const listDocumentChunks = (id: string) =>
  api.get<ChunkOut[]>(`/documents/${id}/chunks`).then((r) => r.data);

export const createDocument = (payload: {
  title: string;
  domain: string;
  content: string;
  source_type?: string;
  version?: string;
  access_level?: string;
}) => api.post<DocumentCreated>("/documents", payload).then((r) => r.data);

export const extractDocument = (id: string) =>
  api.post<ExtractionRunResponse>(`/documents/${id}/extract`).then((r) => r.data);

export const extractChunk = (chunkId: string) =>
  api.post<ExtractionRunResponse>(`/chunks/${chunkId}/extract`).then((r) => r.data);

// =========== chunks ===========
export const getChunk = (id: string) =>
  api.get<ChunkOut>(`/chunks/${id}`).then((r) => r.data);

// =========== candidates ===========
export const listEntityCandidates = (
  params: {
    document_id?: string;
    chunk_id?: string;
    review_status?: string;
    entity_type?: string;
    limit?: number;
    offset?: number;
  } = {},
) =>
  api
    .get<ExtractedEntity[]>("/candidates/entities", { params })
    .then((r) => r.data);

export const listRelationCandidates = (
  params: {
    document_id?: string;
    chunk_id?: string;
    review_status?: string;
    relation_type?: string;
    limit?: number;
    offset?: number;
  } = {},
) =>
  api
    .get<ExtractedRelation[]>("/candidates/relations", { params })
    .then((r) => r.data);

export const approveEntity = (id: string, reviewer: string) =>
  api
    .post<ExtractedEntity>(`/candidates/entities/${id}/approve`, { reviewer })
    .then((r) => r.data);

export const rejectEntity = (id: string, reviewer: string, reason: string) =>
  api
    .post<ExtractedEntity>(`/candidates/entities/${id}/reject`, { reviewer, reason })
    .then((r) => r.data);

export const modifyEntity = (
  id: string,
  payload: {
    reviewer: string;
    name?: string;
    normalized_name?: string;
    entity_type?: string;
  },
) =>
  api
    .patch<ExtractedEntity>(`/candidates/entities/${id}`, payload)
    .then((r) => r.data);

export const mergeEntity = (id: string, reviewer: string, into_id: string) =>
  api
    .post<ExtractedEntity>(`/candidates/entities/${id}/merge`, {
      reviewer,
      into_id,
    })
    .then((r) => r.data);

export const approveRelation = (id: string, reviewer: string) =>
  api
    .post<ExtractedRelation>(`/candidates/relations/${id}/approve`, { reviewer })
    .then((r) => r.data);

export const rejectRelation = (id: string, reviewer: string, reason: string) =>
  api
    .post<ExtractedRelation>(`/candidates/relations/${id}/reject`, {
      reviewer,
      reason,
    })
    .then((r) => r.data);

export const modifyRelation = (
  id: string,
  payload: {
    reviewer: string;
    relation_type?: string;
    source_entity_name?: string;
    source_entity_type?: string;
    target_entity_name?: string;
    target_entity_type?: string;
  },
) =>
  api
    .patch<ExtractedRelation>(`/candidates/relations/${id}`, payload)
    .then((r) => r.data);

// =========== ontology ===========
export const listEntityTypes = (active_only = false) =>
  api
    .get<OntologyEntityType[]>("/ontology/entity-types", { params: { active_only } })
    .then((r) => r.data);

export const listRelationTypes = (active_only = false) =>
  api
    .get<OntologyRelationType[]>("/ontology/relation-types", { params: { active_only } })
    .then((r) => r.data);

export const createEntityType = (payload: {
  name: string;
  display_name: string;
  description?: string;
}) =>
  api.post<OntologyEntityType>("/ontology/entity-types", payload).then((r) => r.data);

export const updateEntityType = (
  id: string,
  payload: { display_name?: string; description?: string; is_active?: boolean },
) =>
  api
    .patch<OntologyEntityType>(`/ontology/entity-types/${id}`, payload)
    .then((r) => r.data);

export const deactivateEntityType = (id: string) =>
  api.delete<OntologyEntityType>(`/ontology/entity-types/${id}`).then((r) => r.data);

export const createRelationType = (payload: {
  source_entity_type: string;
  relation_name: string;
  target_entity_type: string;
  display_name: string;
  description?: string;
}) =>
  api
    .post<OntologyRelationType>("/ontology/relation-types", payload)
    .then((r) => r.data);

export const updateRelationType = (
  id: string,
  payload: { display_name?: string; description?: string; is_active?: boolean },
) =>
  api
    .patch<OntologyRelationType>(`/ontology/relation-types/${id}`, payload)
    .then((r) => r.data);

export const deactivateRelationType = (id: string) =>
  api.delete<OntologyRelationType>(`/ontology/relation-types/${id}`).then((r) => r.data);

// =========== graph ===========
export const syncAll = (force = false) =>
  api.post<GraphSyncResult>("/graph/sync", null, { params: { force } }).then((r) => r.data);

export const listSyncLogs = (params: { limit?: number; offset?: number } = {}) =>
  api.get<GraphSyncLog[]>("/graph/sync-logs", { params }).then((r) => r.data);

export const getGraphEntity = (normalized_name: string) =>
  api
    .get<GraphEntityResponse>(`/graph/entities/${encodeURIComponent(normalized_name)}`)
    .then((r) => r.data);

export const getSubgraph = (seed: string, depth = 2) =>
  api
    .get<SubgraphResponse>("/graph/subgraph", { params: { seed, depth } })
    .then((r) => r.data);

// =========== qa ===========
export const ask = (question: string) =>
  api.post<QAResponse>("/qa", { question }).then((r) => r.data);

export const listQaLogs = (
  params: { limit?: number; offset?: number; contains_question?: string } = {},
) => api.get<AIQueryLog[]>("/qa/logs", { params }).then((r) => r.data);

export const getQaLog = (id: string) =>
  api.get<AIQueryLog>(`/qa/logs/${id}`).then((r) => r.data);

// =========== audit ===========
export const listAuditLogs = (
  params: {
    action?: string;
    target_type?: string;
    document_id?: string;
    chunk_id?: string;
    limit?: number;
    offset?: number;
  } = {},
) => api.get<AuditLog[]>("/audit-logs", { params }).then((r) => r.data);

export const getAuditLog = (id: string) =>
  api.get<AuditLog>(`/audit-logs/${id}`).then((r) => r.data);
