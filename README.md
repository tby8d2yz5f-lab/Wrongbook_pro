# 知错智能错题本 V14：数学公式 OCR + AI 图片校对

这是静态前端 + 可选 Cloudflare Worker 后端的 GitHub Pages 项目。原有错题本、复习、统计、导入导出和浏览器本地 OCR 功能保留。

## 新增能力

- **Mathpix 数学公式 OCR**：通过 Mathpix OCR API 识别数学表达式，并尽可能返回 LaTeX 与可读文本。需要自己的 Mathpix API 凭据，可能产生费用。
- **AI 图片理解与校对**：将原图和当前 OCR 文本交给 OpenAI 视觉模型，要求逐行转写、对照差异，并将不确定字符明确标注。需要自己的 OpenAI API 凭据，按服务商价格计费。
- **安全代理**：浏览器不会直接持有 Mathpix/OpenAI API 密钥；密钥只配置在你自己的 Cloudflare Worker Secrets 中。前端保存的是 Worker 地址和访问口令。不要把 Worker 访问口令分享给别人或在公用设备保存。
- **本地 OCR 仍可用**：不配置云端服务时，Tesseract.js 本地识别照常工作。

> OCR 与视觉模型都可能误读数学符号，不能保证准确。尤其要人工核对负号、指数、分数线、根号、上下标、几何图形和题目条件。使用云端功能时，图片和题目文本会发送给你配置的 Mathpix/OpenAI 服务商；请阅读其数据政策。

## A. 发布前端到 GitHub Pages

1. 把本目录全部文件上传到 GitHub 仓库根目录（不要只上传 ZIP）。
2. 仓库 Settings → Pages → Build and deployment，选择 `Deploy from a branch`、`main`、`/(root)`。
3. 保存并等待发布。前端网址应为 HTTPS。

## B. 配置可选云端 OCR / AI 后端（一次性设置）

需要一个 Cloudflare 账号，并安装 Node.js/npm。也可以用 Cloudflare 网页控制台部署 Worker，但命令行步骤更容易复现。

1. 安装 Wrangler：`npm install -g wrangler`
2. 在本目录登录：`npx wrangler login`
3. 部署 Worker：`npx wrangler deploy`
4. 设置一个自己生成的长随机访问口令：
   - `npx wrangler secret put APP_ACCESS_TOKEN`
   - 按提示输入长随机字符串（不要使用示例口令，不要提交到 GitHub）。
5. 如需 Mathpix 数学公式 OCR，配置：
   - `npx wrangler secret put MATHPIX_APP_ID`
   - `npx wrangler secret put MATHPIX_APP_KEY`
6. 如需 AI 图片理解与校对，配置：
   - `npx wrangler secret put OPENAI_API_KEY`
7. 如要更改视觉模型，在 `wrangler.toml` 的 `OPENAI_VISION_MODEL` 中设置可用模型，然后重新部署。
8. 复制 Worker 的 `https://...workers.dev` 地址，在网站录入表单中的“服务地址”填写它，在“访问口令”填写刚设置的 `APP_ACCESS_TOKEN`，点击“保存服务配置”。

**安全与费用：**请只在自己的 Worker 中设置自己的 API 密钥。访问口令相当于调用保护，不要公开分享；如疑似泄露，立即更换 `APP_ACCESS_TOKEN` 并重新部署/更新浏览器配置。公开网站的访问者仍可能尝试滥用公开 API 端点，因此请设置服务商账单限额并监控用量。生产环境建议进一步加入速率限制、来源域名限制和 Cloudflare Turnstile。

## C. 使用方法

1. 在“录入一道错题”上传题目图片。
2. 可先点“识别已上传图片中的题干与公式”进行免费（服务自身无 API 费用，CDN/网络除外）的本地 Tesseract OCR。
3. 点“数学公式专用识别”调用 Mathpix。
4. 如需对照原图复核，点“AI 看图理解与校对”；它会读取原图及当前 OCR 结果，并把校对文本放回识别框。
5. 仔细检查后再点“填入题目内容”，并保存错题。

AI 校对会替换识别框里的当前文本。如果需要保留原始结果，请在点击前复制原文。

## 隐私与数据

- 错题库默认保存在当前浏览器；GitHub Pages 不提供数据同步。
- 本地 Tesseract 识别在浏览器中进行；Mathpix / AI 按钮会把所选图片发送到你配置的后端及相应服务商。
- 不要将 API 密钥写入 `index.html`、`wrangler.toml` 或 Git 仓库。
- 云端 OCR 和视觉校对不是离线功能，需联网并有可用 API 凭据。

## 项目结构

```text
index.html
manifest.webmanifest
sw.js
wrangler.toml
worker/index.js
icons/icon-192.png
icons/icon-512.png
README.md
.nojekyll
```
