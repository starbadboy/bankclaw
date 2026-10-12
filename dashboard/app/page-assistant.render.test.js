// Executed render probe for the Assistant page (same approach as page-goals.render.test.js).
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const esbuild = require("esbuild");

global.window = global;
global.React = React;
Object.assign(global, {
  Icon: ({ name }) => React.createElement("i", { "data-icon": name }),
  apiAssistantSend: async () => ({ thread: { id: "t1", title: "Q" }, reply: "A" }),
});

const src = fs.readFileSync(path.join(__dirname, "page-assistant.jsx"), "utf8");
vm.runInThisContext(esbuild.transformSync(src, { loader: "jsx" }).code, { filename: "page-assistant.jsx" });

const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));
const base = { messages: [], pending: false, error: "", draft: "", configured: true, onDraft() {}, onSend() {} };

test("page renders its empty state with example prompts", () => {
  const html = render(AssistantPage, { currentProfileId: "all" });
  assert.match(html, /Assistant/);
  assert.match(html, /How much did I spend/);
});

test("conversation shows user and assistant messages in order", () => {
  const html = render(AssistantChat, {
    ...base,
    messages: [{ role: "user", content: "How much on food?" }, { role: "assistant", content: "SGD 30.00\n- Grab: 20.50" }],
  });
  assert.ok(html.indexOf("How much on food?") < html.indexOf("SGD 30.00"));
  assert.match(html, /chat-msg user/);
  assert.match(html, /chat-msg assistant/);
  assert.doesNotMatch(html, /How much did I spend/); // examples only when empty
});

test("pending turn shows the thinking indicator and disables sending", () => {
  const html = render(AssistantChat, { ...base, pending: true, draft: "Q", messages: [{ role: "user", content: "Q" }] });
  assert.match(html, /Thinking/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>[^<]*(<i[^>]*><\/i>)?\s*Send/);
});

test("error keeps the typed message in the composer", () => {
  const html = render(AssistantChat, { ...base, error: "Assistant unavailable — try again", draft: "my question" });
  assert.match(html, /Assistant unavailable/);
  assert.match(html, /<textarea[^>]*>my question<\/textarea>/);
});

test("thread list shows New chat, titles, the active thread and a delete control per thread", () => {
  const html = render(AssistantThreads, {
    threads: [{ id: "t1", title: "Food last month" }, { id: "t2", title: "Net worth" }],
    activeId: "t2", onNew() {}, onOpen() {}, onDelete() {},
  });
  assert.match(html, /New chat/);
  assert.ok(html.indexOf("Food last month") < html.indexOf("Net worth"));
  assert.match(html, /class="chat-thread active"[^>]*>(?:(?!chat-thread ).)*Net worth/s);
  assert.equal((html.match(/aria-label="Delete thread/g) || []).length, 2);
});

test("thread list empty state", () => {
  const html = render(AssistantThreads, { threads: [], activeId: null, onNew() {}, onOpen() {}, onDelete() {} });
  assert.match(html, /No saved chats yet/);
});
