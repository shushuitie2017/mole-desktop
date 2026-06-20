# LESSONS — bluecat-deploy

> 调用本技能时由 skill-lessons 钩子自动注入。新增用 `~/.claude/tools/skill-lesson.py bluecat-deploy "<教训>"`。

- 2026-06-19: SEO 自检是必跑 gate，不是『推荐』；且不只新站——既有站每次结构/内容更新（如加多语言）都要重跑。落地法：直接调本生态 API 拿分逐项核 https://seo.bluecatbot.com/api/audit?url=<域名> ，别凭记忆只补 canonical+OG 就算完。整张清单要到位：title/desc/canonical/OG/og:image(真生成非死链)/hreflang(且页面要真按 ?lang= 渲染否则 URL 是死的)/robots.txt/sitemap.xml/JSON-LD/viewport 不能有 maximum-scale(禁缩放会扣移动端分)。Flask 静态站做法：robots/sitemap/og-cover 放 static/ + app.py 加根路由(带正确 MIME)；无图像工具时 og-cover.png 用 chrome-devtools 渲染品牌卡 1200×630 截图生成。实证：bluecat-claude(learn.bluecatbot.com)首版走本 skill 上线却只补了 canonical+OG+twitter，缺 og:image/hreflang/robots/sitemap/JSON-LD + /app viewport 有 maximum-scale，外部体检只 74/100——缺的全是 §5 清单上的项。
