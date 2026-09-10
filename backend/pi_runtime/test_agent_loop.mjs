import { Agent } from "@earendil-works/pi-agent-core";
import { Type, createModels } from "@earendil-works/pi-ai";
import { fauxAssistantMessage, fauxProvider, fauxText, fauxToolCall } from "@earendil-works/pi-ai/providers/faux";

const faux = fauxProvider({ provider: "winfix-test", models: [{ id: "qwen3:8b" }] });
const models = createModels();
models.setProvider(faux.provider);
const model = models.getModel("winfix-test", "qwen3:8b");
if (!model) throw new Error("Faux Qwen model was not registered.");

let calls = 0;
const evidence = [{ id: "evidence-1", title: "CPU utilization" }];
const diagnosticTool = {
  name: "diagnose_performance",
  label: "Diagnose performance",
  description: "Collect read-only performance evidence.",
  parameters: Type.Object({}, { additionalProperties: false }),
  executionMode: "sequential",
  execute: async () => {
    calls += 1;
    return { content: [{ type: "text", text: JSON.stringify(evidence) }], details: { evidence_count: evidence.length } };
  },
};

faux.setResponses([
  fauxAssistantMessage(fauxToolCall("diagnose_performance", {})),
  fauxAssistantMessage(fauxText(JSON.stringify({
    summary: "Performance evidence was collected.",
    probable_causes: [{ title: "Transient load", explanation: "The snapshot is limited.", evidence_ids: ["evidence-1"], confidence: 0.4 }],
    findings: [{ title: "CPU utilization", description: "A read-only snapshot was collected.", evidence_ids: ["evidence-1"] }],
    recommended_actions: [],
    overall_confidence: 0.4,
  }))),
]);

const agent = new Agent({
  initialState: { systemPrompt: "Use the diagnostic tool.", model, thinkingLevel: "off", tools: [diagnosticTool] },
  streamFn: models.streamSimple.bind(models),
  toolExecution: "sequential",
});
await agent.prompt("My PC is slow");

const final = [...agent.state.messages].reverse().find((message) => message.role === "assistant");
const text = final?.content?.filter((item) => item.type === "text").map((item) => item.text).join("") ?? "";
if (calls !== 1 || faux.state.callCount !== 2 || !text.includes("evidence-1")) {
  throw new Error("Pi tool-loop contract failed.");
}
console.log("Pi agent loop passed: one diagnostic tool call and a structured final response.");
