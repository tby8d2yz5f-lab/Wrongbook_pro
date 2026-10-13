# 知错智能错题本（GitHub Pages 版）

这是一个可直接部署到 GitHub Pages 的静态网页，无需安装依赖或构建。错题及学习记录保存在当前浏览器中。请定期从页面导出 JSON 备份；更换浏览器或设备时，可通过导入备份恢复数据。

## 发布到 GitHub Pages

1. 在 GitHub 新建一个仓库。
2. 将本目录中的所有文件上传到仓库根目录，并提交到 `main` 分支。
3. 打开仓库 **Settings → Pages**。
4. 在 **Build and deployment** 中选择 **Deploy from a branch**，分支选择 `main`，目录选择 `/ (root)`，然后保存。
5. 等待 GitHub Pages 发布完成，再打开页面显示的站点地址。

入口文件是 `index.html`。manifest、图标和离线缓存文件均使用相对路径，可部署在 `username.github.io/repository/` 这样的项目子路径下。

## 使用说明

- 页面不会自动把错题上传到 AI 服务。请在“解析与变式”中生成请求，复制到 ChatGPT 等 AI 对话中，再将回答粘贴回来。
- 在“学习闭环”中粘贴完整解析和知识点，并填写三道递进练习及答案，然后点击“保存解析、知识点与练习”。
- 导出 JSON 时，解析、知识点和练习会随错题记录保存；文件还包含独立的 `practiceSets` 清单。
- OCR 识图使用 Tesseract.js CDN，因此首次识图需要联网。其他本地记录功能使用浏览器存储。
- HTTPS 下会启用 Service Worker；离线时可以打开已缓存页面，但 CDN 识图需要联网。

## 隐私与备份

错题数据默认存储在当前浏览器的 IndexedDB / localStorage 中，不会随 GitHub Pages 自动同步到其他设备。不要将导出的 JSON 备份提交到公开仓库，因为其中可能包含个人学习资料。
