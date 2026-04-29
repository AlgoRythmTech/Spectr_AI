/**
 * Spectr Puter.js Client — free Claude Opus 4.7 access via browser.
 *
 * Add to your HTML:
 *   <script src="https://js.puter.com/v2/"></script>
 *   <script src="/static/spectr-puter-client.js"></script>
 *
 * Then:
 *   const result = await spectrAgent({
 *     prompt: "Reconcile this GSTR-1 against my books",
 *     files: [file1, file2],
 *     model: "claude-opus-4-7",
 *   });
 *
 *   // result.download_urls[0].url  — download the generated Excel
 *   // result.google.connected     — can we upload to user's Drive?
 */

const SPECTR_API_BASE = window.SPECTR_API_BASE || "/api";

/**
 * Spectr Python agent prompt — tells Claude how to write code for our sandbox.
 */
const SPECTR_PYTHON_SYSTEM_PROMPT = `You are a senior Indian CA/lawyer data analyst operating as a Python code agent.

Given a user prompt + uploaded file profile, generate ONE complete Python script that:
1. Reads files from /workspace/input/ (already uploaded to sandbox)
2. Writes output files to /workspace/output/
3. Prints a concise success summary

AVAILABLE LIBRARIES (all auto-installed):
openpyxl, xlsxwriter, python-docx (import docx), pdfplumber, pypdf, reportlab,
PIL, rapidfuzz, jinja2, dateutil, tabulate. Try pandas/numpy in try/except.

MATH RULES:
- Use decimal.Decimal for money (never float)
- ROUND_HALF_UP, paisa precision
- Excel: use formulas as strings: ws.cell().value='=B2*C2/100' (F2 shows formula)
- Indian number format: #,##0.00

INDIAN FY 2025-26:
TDS: 192 slab/₹2.5L, 194J 10%/₹30K, 194C 1-2%/₹30K, 194I 10%(L&B)/2%(P&M)/₹2.4L,
194IB 2% (amended 01-10-2024)/₹50K/m, 194Q 0.1%>₹50L, 194T 10%/₹20K, 195 12.5%+surcharge.
Advance tax: 15/45/75/100% by 15-Jun/15-Sep/15-Dec/15-Mar.
New regime slabs: 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, 24L+ 30%.

Output ONE complete Python script. No markdown fences. Start with #!/usr/bin/env python3.`;

/**
 * Generate Python code via Puter.js (Claude, free).
 */
async function spectrGenerateCode({ prompt, fileProfile, model = "claude-opus-4-7" }) {
  if (typeof puter === "undefined") {
    throw new Error("Puter.js not loaded. Include <script src='https://js.puter.com/v2/'></script>");
  }

  const fullPrompt = `USER REQUEST:
${prompt}

UPLOADED FILES PROFILE:
${fileProfile || "(no files uploaded)"}

Generate the Python script.`;

  const response = await puter.ai.chat(
    fullPrompt,
    {
      model: model,
      // Note: puter.ai.chat accepts a string OR an array of messages; use the string form
      // Some Puter.js versions prefix with a system message param. Fallback: prepend inline.
    }
  );

  // Extract code
  let text = "";
  if (response?.message?.content) {
    if (Array.isArray(response.message.content)) {
      text = response.message.content.map(p => p.text || "").join("\n");
    } else {
      text = response.message.content;
    }
  } else if (typeof response === "string") {
    text = response;
  }

  // Strip markdown fences
  const match = text.match(/```(?:python|py)?\s*\n([\s\S]*?)```/);
  return match ? match[1].trim() : text.trim();
}

/**
 * Combined workflow: profile files → generate Python (via Puter.js Claude) → execute in backend sandbox.
 */
async function spectrAgent({ prompt, files = [], model = "claude-opus-4-7", authToken }) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  // 1. Profile uploaded files (compact data context for Claude)
  let fileProfile = "";
  if (files && files.length > 0) {
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    const resp = await fetch(`${SPECTR_API_BASE}/agent/profile-files`, {
      method: "POST",
      body: formData,
      headers,
    });
    if (resp.ok) {
      const profileData = await resp.json();
      fileProfile = profileData.profile_text;
    }
  }

  // 2. Generate Python code via Puter.js (free Claude, user-pays model)
  const code = await spectrGenerateCode({ prompt, fileProfile, model });

  // 3. Execute code in backend sandbox (files re-uploaded since sandbox doesn't persist)
  const execForm = new FormData();
  execForm.append("code", code);
  files.forEach(f => execForm.append("files", f));

  const execResp = await fetch(`${SPECTR_API_BASE}/agent/execute-code`, {
    method: "POST",
    body: execForm,
    headers,
  });

  if (!execResp.ok) {
    throw new Error(`Execution failed: ${execResp.status} ${await execResp.text()}`);
  }

  const result = await execResp.json();
  return { ...result, generated_code: code };
}

/**
 * Connect user's Google Drive (pops up consent).
 */
async function spectrConnectDrive({ authToken } = {}) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const resp = await fetch(`${SPECTR_API_BASE}/google/auth/start`, { headers });
  const data = await resp.json();
  if (data.auth_url) {
    const popup = window.open(data.auth_url, "spectr-google-auth", "width=550,height=700");
    // Poll for completion
    return new Promise((resolve) => {
      const interval = setInterval(async () => {
        try {
          if (!popup || popup.closed) {
            clearInterval(interval);
            // Check status
            const statusResp = await fetch(`${SPECTR_API_BASE}/google/status`, { headers });
            const status = await statusResp.json();
            resolve(status);
          }
        } catch (e) {
          clearInterval(interval);
          resolve({ connected: false, error: e.message });
        }
      }, 1000);
    });
  }
  throw new Error("Failed to get auth URL");
}

/**
 * Upload a generated file (by file_id) to user's Drive.
 */
async function spectrUploadToDrive({ fileId, folderId = "root", convert = true, authToken }) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const form = new FormData();
  form.append("file_id", fileId);
  form.append("folder_id", folderId);
  form.append("convert", convert);

  const resp = await fetch(`${SPECTR_API_BASE}/google/upload`, {
    method: "POST",
    body: form,
    headers,
  });
  if (!resp.ok) throw new Error(`Drive upload failed: ${resp.status}`);
  return await resp.json();
}

/**
 * List user's Drive folders (for folder picker UI).
 */
async function spectrListFolders({ parentId = "root", query = "", authToken } = {}) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const params = new URLSearchParams({ parent_id: parentId });
  if (query) params.append("q", query);

  const resp = await fetch(`${SPECTR_API_BASE}/google/folders?${params}`, { headers });
  if (!resp.ok) throw new Error(`List folders failed: ${resp.status}`);
  return await resp.json();
}

/**
 * Iterative agent — for complex data exploration.
 * Returns an async iterator yielding SSE events.
 */
async function* spectrIterate({ prompt, files = [], maxRounds = 4, authToken }) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const form = new FormData();
  form.append("prompt", prompt);
  form.append("max_rounds", maxRounds);
  files.forEach(f => form.append("files", f));

  const resp = await fetch(`${SPECTR_API_BASE}/agent/iterate`, {
    method: "POST",
    body: form,
    headers,
  });

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;
        try {
          yield JSON.parse(payload);
        } catch (e) {
          // ignore parse errors
        }
      }
    }
  }
}

/**
 * OPUS 4.7 ADVISORY — High-level legal/tax reasoning via Puter.js.
 *
 * Flow:
 *   1. Get SPECTR system prompt + statute DB context + IK cases from backend
 *   2. Stream Claude Opus 4.7 via Puter.js (browser-side, free, unlimited)
 *   3. Post the response back to backend for Trust Layer verification + critique
 *   4. Return final augmented response to UI
 */

async function spectrOpusAdvisory({
  query,
  model = "claude-opus-4-7",
  matterId = "",
  conversationHistory = [],
  authToken,
  onChunk = null,        // callback(text) for streaming chunks
  onStep = null,         // callback(step) for progress events
}) {
  const headers = { "Content-Type": "application/json" };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  // 1. Get prepared context from backend (statute DB + IK + SPECTR prompt + deep research if needed)
  if (onStep) onStep({ step: "prepare", message: "Gathering legal research context..." });
  const ctxResp = await fetch(`${SPECTR_API_BASE}/assistant/prepare-context`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query, matter_id: matterId, conversation_history: conversationHistory }),
  });
  if (!ctxResp.ok) throw new Error(`prepare-context failed: ${ctxResp.status}`);
  const { system_prompt, user_content, sources_used } = await ctxResp.json();

  // 2. Stream Claude Opus 4.7 via Puter.js (FREE, browser-side)
  if (onStep) onStep({ step: "reasoning", message: `Running ${model} deep reasoning...` });

  let fullResponse = "";
  try {
    // Puter chat with streaming
    const stream = await puter.ai.chat(
      `${system_prompt}\n\n===\n\n${user_content}`,
      { model, stream: true }
    );
    for await (const part of stream) {
      const chunk = part?.text || "";
      fullResponse += chunk;
      if (onChunk) onChunk(chunk);
    }
  } catch (e) {
    // Fallback to non-streaming
    if (onStep) onStep({ step: "reasoning_fallback", message: "Streaming failed, trying non-stream..." });
    const response = await puter.ai.chat(
      `${system_prompt}\n\n===\n\n${user_content}`,
      { model }
    );
    if (response?.message?.content) {
      fullResponse = Array.isArray(response.message.content)
        ? response.message.content.map(p => p.text || "").join("\n")
        : response.message.content;
    } else if (typeof response === "string") {
      fullResponse = response;
    }
  }

  // 3. Send response to backend for Trust Layer verification (citation checks, math check, critique)
  if (onStep) onStep({ step: "verify", message: "Verifying citations + running critique pass..." });
  const verifyResp = await fetch(`${SPECTR_API_BASE}/assistant/verify-response`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      query,
      response: fullResponse,
      sources_used: sources_used || [],
    }),
  });

  let verification = {};
  if (verifyResp.ok) {
    verification = await verifyResp.json();
  }

  if (onStep) onStep({ step: "complete", message: "Done" });

  return {
    response: fullResponse,
    augmented: verification.augmented_text || fullResponse,
    trust_score: verification.trust_score,
    verification: verification,
    sources_used,
    model_used: model,
  };
}

/**
 * DEEP RESEARCH — Blaxel sandbox web research (Claude Opus 4.7 as reasoner).
 *
 * When the user explicitly asks for deep research ("investigate", "find latest cases", etc.)
 * this triggers the 5-phase sandbox pipeline on the backend AND feeds findings into Opus 4.7
 * for final synthesis.
 */
async function spectrDeepResearch({ query, model = "claude-opus-4-7", authToken, onStep = null }) {
  const headers = { "Content-Type": "application/json" };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  if (onStep) onStep({ step: "sandbox_research", message: "Launching Blaxel sandbox for 5-phase web research..." });

  // Kick off sandbox research on backend (streaming)
  const sandboxResp = await fetch(`${SPECTR_API_BASE}/assistant/deep-research-only`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query }),
  });
  if (!sandboxResp.ok) throw new Error(`Deep research failed: ${sandboxResp.status}`);

  const researchData = await sandboxResp.json();

  if (onStep) onStep({
    step: "sandbox_done",
    message: `Research complete: ${researchData.sources_count} sources from ${researchData.sites_hit} sites`,
  });

  // Feed research into Opus 4.7 for synthesis
  if (onStep) onStep({ step: "synthesis", message: `Synthesizing findings via ${model}...` });

  const synthPrompt = `You are Spectr, a senior Indian legal/tax expert. The user asked: "${query}"

Deep web research has been conducted. Findings below:

${researchData.findings}

SOURCES: ${researchData.sources.map(s => `${s.url} (${s.site})`).join(", ")}

Synthesize a comprehensive, senior-associate-grade response. Cite sources inline. Quantify any exposures. End with a <risk_analysis> block.`;

  const response = await puter.ai.chat(synthPrompt, { model });
  let synthesis = "";
  if (response?.message?.content) {
    synthesis = Array.isArray(response.message.content)
      ? response.message.content.map(p => p.text || "").join("\n")
      : response.message.content;
  } else if (typeof response === "string") {
    synthesis = response;
  }

  return {
    query,
    findings: researchData.findings,
    sources: researchData.sources,
    synthesis,
    model_used: model,
  };
}

// Expose globally
if (typeof window !== "undefined") {
  window.spectrAgent = spectrAgent;
  window.spectrGenerateCode = spectrGenerateCode;
  window.spectrConnectDrive = spectrConnectDrive;
  window.spectrUploadToDrive = spectrUploadToDrive;
  window.spectrListFolders = spectrListFolders;
  window.spectrIterate = spectrIterate;
  window.spectrOpusAdvisory = spectrOpusAdvisory;
  window.spectrDeepResearch = spectrDeepResearch;
}
