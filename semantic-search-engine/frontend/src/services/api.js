/**
 * api.js -- Axios-based API service layer.
 *
 * All backend calls are centralised here so components never
 * hardcode URLs or worry about request/response shaping.
 */

import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 60_000, // ingestion can be slow on large repos
  headers: { "Content-Type": "application/json" },
});

/* ── Search ────────────────────────────────────────────────────── */

/**
 * Semantic search over the indexed codebase.
 *
 * @param {string} query  Natural-language search query.
 * @param {number} [k=5]  Number of results to return.
 * @returns {Promise<{query: string, total_indexed: number, results: Array}>}
 */
export async function search(query, k = 5) {
  const { data } = await API.get("/api/v1/search", {
    params: { q: query, k },
  });
  return data;
}

/* ── Ingest ────────────────────────────────────────────────────── */

/**
 * Ingest a local directory into the vector store.
 *
 * @param {object}  payload
 * @param {string}  payload.directory   Absolute or relative path.
 * @param {boolean} [payload.reset]     Wipe collection before ingesting.
 * @returns {Promise<{status: string, chunks_indexed: number, files_processed: number, message: string}>}
 */
export async function ingest(payload) {
  const { data } = await API.post("/api/v1/ingest", payload);
  return data;
}

/**
 * Get current ingestion status.
 */
export async function getIngestStatus() {
  const { data } = await API.get("/api/v1/ingest/status");
  return data;
}

/**
 * Get repository statistics.
 */
export async function getRepoStats() {
  const { data } = await API.get("/api/v1/repo/stats");
  return data;
}

/**
 * Get specific file content.
 */
export async function getRepoFile(path) {
  const { data } = await API.get(`/api/v1/repo/file?path=${encodeURIComponent(path)}`);
  return data;
}

/* ── Ask (RAG placeholder) ─────────────────────────────────────── */

/**
 * Ask a natural-language question about the codebase.
 *
 * @param {string} question
 * @param {Array} history
 * @returns {Promise<{question: string, answer: string, sources: Array}>}
 */
export async function ask(question, history = []) {
  const { data } = await API.post("/api/v1/ask", { question, history, stream: false });
  return data;
}

/* ── Health ────────────────────────────────────────────────────── */

export async function healthCheck() {
  const { data } = await API.get("/health");
  return data;
}

export default API;
