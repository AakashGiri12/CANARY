// Typed client for the FastAPI service (api/main.py). Config keys/labels
// here are already the generic display strings the API returns — no
// internal llm_registry name (e.g. "deepseek") ever reaches this file or
// anything that imports it. See api/display.py for why.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export type ConfigOut = {
  key: string;
  label: string;
};

export type AttackOut = {
  id: string;
  label: string;
  payload_preview: string;
};

export type HitOut = {
  attack_id: string | null;
  attack_label: string;
  payload_preview: string | null;
  blocked: boolean;
  utility: boolean;
};

export type ComparePointOut = {
  config_key: string;
  config_label: string;
  asr_rate: number;
  utility_rate: number;
};

export type StaticRunOut = {
  config_label: string;
  hits: HitOut[];
  asr_rate: number;
  utility_rate: number;
};

export type GenerationOut = {
  generation: number;
  framing_index: number;
  blocked: boolean;
  utility: boolean;
};

export type AdaptiveRunOut = {
  target_label: string;
  generations: GenerationOut[];
};

export type ClassifierResultOut = {
  model_label: string;
  accuracy: number;
  f1: number;
  status: string;
  note: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function listConfigs(): Promise<ConfigOut[]> {
  return request("/api/configs");
}

export function listStaticAttacks(): Promise<AttackOut[]> {
  return request("/api/static-attacks");
}

export function runStatic(config: string): Promise<StaticRunOut> {
  return request(`/api/eval/static-run/${encodeURIComponent(config)}`, {
    method: "POST",
  });
}

export function compareConfigs(): Promise<ComparePointOut[]> {
  return request("/api/eval/compare", { method: "POST" });
}

export function classifierResults(): Promise<ClassifierResultOut[]> {
  return request("/api/classifier-results");
}

export function runAdaptive(
  config: string,
  generations = 5
): Promise<AdaptiveRunOut> {
  return request(
    `/api/eval/adaptive-run/${encodeURIComponent(config)}?generations=${generations}`,
    { method: "POST" }
  );
}
