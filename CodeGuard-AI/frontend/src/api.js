const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse failure, fall back to statusText
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  health() {
    return fetch(`${BASE_URL}/health`).then(handle);
  },

  analyze(file) {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${BASE_URL}/analyze`, { method: "POST", body: form }).then(handle);
  },

  analyzeProject(workspaceId) {
    return fetch(`${BASE_URL}/analyze-project/${workspaceId}`, { method: "POST" }).then(handle);
  },

  listFindings(workspaceId) {
    return fetch(`${BASE_URL}/findings/${workspaceId}`).then(handle);
  },

  generateFix(workspaceId, findingId) {
    return fetch(`${BASE_URL}/generate-fix/${workspaceId}/${findingId}`, { method: "POST" }).then(handle);
  },

  applyFix(workspaceId, findingId) {
    return fetch(`${BASE_URL}/apply-fix/${workspaceId}/${findingId}`, { method: "POST" }).then(handle);
  },

  report(workspaceId) {
    return fetch(`${BASE_URL}/report/${workspaceId}`).then(handle);
  },

  downloadUrl(workspaceId) {
    return `${BASE_URL}/download/${workspaceId}`;
  },
};
