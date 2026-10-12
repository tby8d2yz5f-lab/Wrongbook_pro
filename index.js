// Cloudflare Worker for Zh icuo V14 optional cloud OCR / vision features.
// Configure Worker Secrets: APP_ACCESS_TOKEN (required), OPENAI_API_KEY (vision),
// MATHPIX_APP_ID and MATHPIX_APP_KEY (formula OCR).
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-App-Token",
  "Access-Control-Max-Age": "86400",
};
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { ...cors, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }
});
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json({ ok: false, error: "请使用 POST 请求。" }, 405);
    if (!env.APP_ACCESS_TOKEN || request.headers.get("X-App-Token") !== env.APP_ACCESS_TOKEN) {
      return json({ ok: false, error: "访问口令错误或 Worker 尚未配置 APP_ACCESS_TOKEN。" }, 401);
    }
    let body;
    try { body = await request.json(); } catch { return json({ ok: false, error: "请求 JSON 格式不正确。" }, 400); }
    try {
      if (url.pathname.endsWith("/api/math-ocr")) return await mathOcr(body, env);
      if (url.pathname.endsWith("/api/vision-correct")) return await visionCorrect(body, env);
      return json({ ok: false, error: "未知 API 路径。" }, 404);
    } catch (e) {
      return json({ ok: false, error: e?.message || "上游服务请求失败。" }, 502);
    }
  }
};
function validImage(s) { return typeof s === "string" && /^data:image\/(png|jpeg|jpg|webp);base64,/i.test(s) && s.length < 12_000_000; }
async function mathOcr(body, env) {
  if (!env.MATHPIX_APP_ID || !env.MATHPIX_APP_KEY) return json({ ok: false, error: "Worker 未设置 MATHPIX_APP_ID / MATHPIX_APP_KEY。" }, 503);
  if (!validImage(body.image)) return json({ ok: false, error: "图片格式不支持或文件过大。请使用 PNG、JPEG 或 WebP 图片。" }, 400);
  const r = await fetch("https://api.mathpix.com/v3/text", {
    method: "POST",
    headers: { "Content-Type": "application/json", "app_id": env.MATHPIX_APP_ID, "app_key": env.MATHPIX_APP_KEY },
    body: JSON.stringify({ src: body.image, formats: ["text", "latex_styled"], ocr: ["math", "text"], skip_recrop: false })
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) return json({ ok: false, error: d.error || `Mathpix 请求失败（HTTP ${r.status}）。` }, 502);
  const text = (d.text || "").trim();
  const latex = (d.latex_styled || d.latex || "").trim();
  if (!text && !latex) return json({ ok: false, error: "Mathpix 未能识别图片，请尝试裁剪题目并上传更清晰的图像。" }, 422);
  return json({ ok: true, text, latex, confidence: d.confidence ?? null });
}
async function visionCorrect(body, env) {
  if (!env.OPENAI_API_KEY) return json({ ok: false, error: "Worker 未设置 OPENAI_API_KEY。" }, 503);
  if (!Array.isArray(body.images) || !body.images.length || body.images.length > 2 || !body.images.every(validImage))
    return json({ ok: false, error: "请提供 1–2 张 PNG、JPEG 或 WebP 图片，且单张请求不要过大。" }, 400);
  const content = [{ type: "input_text", text: `你是严谨的试卷转写与数学公式校对助手。学科：${String(body.subject || "数学").slice(0, 30)}。\n任务：直接观察附图，逐行转写题目，并与下方现有 OCR 结果对照。优先忠实转写，不要解题，不要擅自补充图片里没有的信息。保留题号、选项、单位、变量、负号、指数、分数、根号、上下标、区间和标点。数学公式尽量同时给出可读形式和 LaTeX。任何看不清或无法确定的字符请写成 [不确定:候选]，并在最后列出“需要人工确认”的位置。若 OCR 与图片冲突，以可见原图为准，但不确定时必须明确标注。不要声称已达到百分之百准确。\n\n现有 OCR 结果：\n${String(body.ocrText || "（无现有 OCR 文本）").slice(0, 12000)}` }];
  for (const image of body.images) content.push({ type: "input_image", image_url: image, detail: "high" });
  const r = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { "Authorization": `Bearer ${env.OPENAI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: env.OPENAI_VISION_MODEL || "gpt-4.1-mini", input: [{ role: "user", content }], max_output_tokens: 5000 })
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) return json({ ok: false, error: d.error?.message || `OpenAI 请求失败（HTTP ${r.status}）。` }, 502);
  const text = (d.output || []).flatMap(x => x.content || []).filter(x => x.type === "output_text").map(x => x.text || "").join("\n").trim();
  if (!text) return json({ ok: false, error: "视觉模型没有返回文本。" }, 502);
  return json({ ok: true, text });
}
