/**
 * api.js -- Axios-based API service layer.
 *
 * All backend calls are centralised here so components never
 * hardcode URLs or worry about request/response shaping.
 */

import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 300000, // ingestion can be slow on large repos
  headers: { "Content-Type": "application/json" },
});

// Interceptors for detailed logging
API.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method.toUpperCase()} ${config.url}`);
    if (config.data) {
      console.log(`[API Request Body]`, config.data);
    }
    return config;
  },
  (error) => {
    console.error(`[API Request Error]`, error);
    return Promise.reject(error);
  }
);

API.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} from ${response.config.url}`);
    console.log(`[API Response Data]`, response.data);
    return response;
  },
  (error) => {
    if (error.response) {
      console.error(`[API Error Response] ${error.response.status} from ${error.config?.url}`);
      console.error(`[API Error Data]`, error.response.data);
    } else {
      console.error(`[API Error]`, error.message);
    }
    return Promise.reject(error);
  }
);

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
