import readline from "node:readline";
import { randomUUID } from "node:crypto";

import { Agent } from "@earendil-works/pi-agent-core";
import { Type, createModels, createProvider } from "@earendil-works/pi-ai";
import { openAICompletionsApi } from "@earendil-works/pi-ai/api/openai-completions.lazy";

const lines = [];
const waiting = [];
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

input.on("line", (line) => {
  try {
    const message = JSON.parse(line);
    const waiter = waiting.shift();
    if (waiter) waiter.resolve(message);
    else lines.push(message);
  } catch {
    process.stderr.write("WinFix Pi runtime received malformed JSON.\n");
  }
});

function receive() {
  const message = lines.shift();
  if (message) return Promise.resolve(message);
  return new Promise((resolve, reject) => waiting.push({ resolve, reject }));
}

function emit(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function ollamaOpenAiUrl(baseUrl) {
  const normalized = baseUrl.replace(/\/$/, "");
  return normalized.endsWith("/v1") ? normalized : `${normalized}/v1`;
}

function buildModel() {
  const baseUrl = ollamaOpenAiUrl(process.env.OLLAMA_BASE_URL || "http://127.0.0.1:11434");
  const modelId = process.env.WINFIX_MODEL || "qwen3:8b";
  const models = createModels();
  const provider = createProvider({
    id: "winfix-ollama",
    name: "WinFix local Ollama",
    baseUrl,
    auth: {
      apiKey: {
        name: "Ollama local endpoint",
        resolve: async () => ({ auth: { apiKey: "ollama" }, source: "local Ollama" }),
      },
    },
    models: [
      {
        id: modelId,
        name: `Ollama ${modelId}`,
        api: "openai-completions",
        provider: "winfix-ollama",
        baseUrl,
        reasoning: false,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 32768,
        maxTokens: 2048,
      },
    ],
    api: openAICompletionsApi(),
  });
  models.setProvider(provider);
  const model = models.getModel("winfix-ollama", modelId);
  if (!model) throw new Error(`Pi could not configure model ${modelId}.`);
  return { models, model };
}

const SYSTEM_PROMPT = `You are WinFix Agent, a Windows diagnostic planner.
You must investigate the user's reported performance problem before drawing conclusions.
Call diagnose_performance exactly once. It is the only tool available.
After receiving its structured evidence, return exactly one JSON object matching this schema:
{
  "summary": "string",
  "probable_causes": [{"title":"string","explanation":"string","evidence_ids":["evidence id"],"confidence":0.0}],
  "findings": [{"title":"string","description":"string","evidence_ids":["evidence id"]}],
  "recommended_actions": [{"action_id":"registered action id","reason":"string","evidence_ids":["evidence id"],"parameters":{}}],
  "overall_confidence": 0.0
}
Facts must be grounded in evidence IDs from the tool result. Do not output markdown, shell commands, scripts, registry paths, or an action outside the registered IDs. If evidence is insufficient, say so and lower confidence.`;

async function waitForToolResult(requestId) {
  while (true) {
    const message = await receive();
    if (message.type === "tool_result" && message.request_id === requestId) return message;
    if (message.type === "tool_error" && message.request_id === requestId) {
      throw new Error(message.error || "The diagnostic tool failed.");
    }
  }
}

async function run(problem) {
  const { models, model } = buildModel();
  let toolCalls = 0;
  const diagnosePerformanceTool = {
    name: "diagnose_performance",
    label: "Diagnose performance",
    description: "Collect read-only CPU, memory, disk, process, startup, and temporary-file evidence. Takes no arguments.",
    parameters: Type.Object({}, { additionalProperties: false }),
    executionMode: "sequential",
    execute: async () => {
      toolCalls += 1;
      if (toolCalls > 1) throw new Error("diagnose_performance may only be called once per WinFix investigation.");
      const requestId = randomUUID();
      emit({ type: "tool_request", request_id: requestId, name: "diagnose_performance", arguments: {} });
      const result = await waitForToolResult(requestId);
      return {
        content: [{ type: "text", text: JSON.stringify(result.evidence) }],
        details: { evidence_count: result.evidence.length },
      };
    },
  };
  const agent = new Agent({
    initialState: {
      systemPrompt: SYSTEM_PROMPT,
      model,
      thinkingLevel: "off",
      tools: [diagnosePerformanceTool],
    },
    streamFn: models.streamSimple.bind(models),
    toolExecution: "sequential",
  });
  await agent.prompt(problem);
  if (toolCalls !== 1) throw new Error("The model did not call diagnose_performance exactly once.");
  const finalMessage = [...agent.state.messages].reverse().find((message) => message.role === "assistant");
  const content = finalMessage?.content?.filter((item) => item.type === "text").map((item) => item.text).join("").trim();
  if (!content) throw new Error("The model returned no final diagnosis JSON.");
  emit({ type: "final", diagnosis_json: content, tool_calls: toolCalls });
}

try {
  const start = await receive();
  if (start.type !== "start" || typeof start.problem !== "string" || !start.problem.trim()) {
    throw new Error("Expected a start message with a non-empty problem.");
  }
  await run(start.problem);
} catch (error) {
  emit({ type: "error", error: error instanceof Error ? error.message : String(error) });
  process.exitCode = 1;
} finally {
  input.close();
}
