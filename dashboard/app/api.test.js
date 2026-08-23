const assert = require("node:assert/strict");
const test = require("node:test");

global.window = global;
global.localStorage = {
  getItem: () => "test-token",
  setItem: () => {},
  removeItem: () => {},
};
require("./api.js");

function jsonResponse(payload) {
  return { ok: true, status: 200, json: async () => payload };
}

test("portfolio custom asset types support list and CRUD requests", async () => {
  const requests = [];
  global.fetch = async (path, options = {}) => {
    requests.push({ path, options });
    if (!options.method) {
      return jsonResponse({ asset_types: [{ id: "custom_cpf", name: "CPF", color: "#8B5CF6" }] });
    }
    if (options.method === "POST") {
      return jsonResponse({ asset_type: { id: "custom_cpf", name: "CPF", color: "#8B5CF6" } });
    }
    if (options.method === "PATCH") {
      return jsonResponse({ asset_type: { id: "custom_cpf", name: "CPF OA", color: "#0F766E" } });
    }
    return jsonResponse({ deleted: 1 });
  };

  const listed = await apiFetchPortfolioAssetTypes();
  const created = await apiCreatePortfolioAssetType({ name: "CPF", color: "#8B5CF6" });
  const updated = await apiUpdatePortfolioAssetType("custom_cpf", { name: "CPF OA", color: "#0F766E" });
  await apiDeletePortfolioAssetType("custom_cpf");

  assert.deepEqual(listed, [{ id: "custom_cpf", name: "CPF", color: "#8B5CF6" }]);
  assert.deepEqual(created, { id: "custom_cpf", name: "CPF", color: "#8B5CF6" });
  assert.deepEqual(updated, { id: "custom_cpf", name: "CPF OA", color: "#0F766E" });
  assert.deepEqual(
    requests.map(({ path, options }) => [path, options.method || "GET"]),
    [
      ["/api/portfolio/asset-types", "GET"],
      ["/api/portfolio/asset-types", "POST"],
      ["/api/portfolio/asset-types/custom_cpf", "PATCH"],
      ["/api/portfolio/asset-types/custom_cpf", "DELETE"],
    ],
  );
});

test("portfolio valuation history request includes item type and id", async () => {
  let request;
  global.fetch = async (path, options) => {
    request = { path, options };
    return jsonResponse({ valuations: [{ as_of_date: "2026-04-30", value: 1250 }] });
  };

  const history = await apiFetchPortfolioValuations("asset", "asset/id");

  assert.equal(request.path, "/api/portfolio/asset/asset%2Fid/valuations");
  assert.deepEqual(history, [{ as_of_date: "2026-04-30", value: 1250 }]);
});

test("recording a valuation posts its exact date and value", async () => {
  let request;
  global.fetch = async (path, options) => {
    request = { path, options };
    return jsonResponse({ valuation: { as_of_date: "2026-04-30", value: 1250 } });
  };

  const saved = await apiRecordPortfolioValuation("asset", "asset-id", {
    as_of_date: "2026-04-30",
    value: 1250,
  });

  assert.equal(request.path, "/api/portfolio/asset/asset-id/valuations");
  assert.equal(request.options.method, "POST");
  assert.deepEqual(JSON.parse(request.options.body), { as_of_date: "2026-04-30", value: 1250 });
  assert.deepEqual(saved, { as_of_date: "2026-04-30", value: 1250 });
});

test("deleting a valuation targets its exact date", async () => {
  let request;
  global.fetch = async (path, options) => {
    request = { path, options };
    return jsonResponse({ deleted: 1 });
  };

  await apiDeletePortfolioValuation("debt", "debt-id", "2026-04-30");

  assert.equal(request.path, "/api/portfolio/debt/debt-id/valuations/2026-04-30");
  assert.equal(request.options.method, "DELETE");
});
