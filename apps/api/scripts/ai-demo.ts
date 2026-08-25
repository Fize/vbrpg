import { buildApp } from "../src/app.js";
import { loadConfig } from "../src/config.js";

const definition = {
  manifest: {
    gameId: "ai-demo",
    slug: "ai-demo",
    version: "1.0.0",
    dslVersion: "v1",
    engineVersion: "native-test",
    authorId: "demo-author",
    license: "MIT",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["ai"] },
      {
        id: "ai",
        type: "aiGenerate",
        config: {
          input: { task: "Choose one option", options: ["red", "blue"] },
          timeoutMs: 30_000,
          maxAttempts: 1,
          fallbackNodeId: "end",
          resultKey: "choice",
        },
        next: ["end"],
      },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [],
  variables: {},
  visibility: {},
  presentation: {},
};

const app = buildApp({ config: loadConfig() });
const response = await app.inject({
  method: "POST",
  url: "/v1/mvp/runtime/ai-dispatch",
  payload: {
    definition,
    state: {
      instanceId: "ai-demo-instance",
      gameVersionId: "ai-demo-version",
      engineVersion: "native-test",
      sequence: 0,
      status: "created",
      currentNodeId: "start",
      variables: {},
      participants: [],
      waiting: null,
      randomSeed: "demo-seed",
    },
    event: {
      eventId: "ai-demo-create",
      instanceId: "ai-demo-instance",
      sequence: 1,
      type: "instanceCreated",
      actor: null,
      occurredAtMs: Date.now(),
      idempotencyKey: "ai-demo-create",
      payload: {},
    },
    recentEvents: [],
  },
});

console.log(JSON.stringify({ statusCode: response.statusCode, body: response.json() }, null, 2));
await app.close();
if (response.statusCode >= 400) process.exitCode = 1;
