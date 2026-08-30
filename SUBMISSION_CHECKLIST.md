# AIIC 提交清单

## 必交材料

- [ ] 3 分钟内 Demo 视频
- [ ] 公网产品链接：http://43.132.173.100
- [ ] Product Memo：`PRODUCT_MEMO.md`
- [ ] GitHub public 仓库：https://github.com/unblieving/aiic-project-0830
- [ ] 提交材料总入口：`docs/SUBMISSION_PACKAGE.md`
- [ ] 调研记录：`docs/RESEARCH_NOTES.md`
- [ ] 原型说明：`docs/PROTOTYPE_NOTES.md`
- [ ] 架构图：`docs/ARCHITECTURE.md`
- [ ] 测试与性能记录：`docs/PERFORMANCE_TESTS.md`

## 服务器检查

- [ ] 项目已部署在服务器 `43.132.173.100`
- [ ] 对外暴露 80 端口
- [ ] 语音模式使用 HTTPS 访问，例如 `nohup cloudflared tunnel --url http://127.0.0.1:80 > tunnel.log 2>&1 &`
- [ ] `.env` 未提交到 GitHub
- [ ] 服务器上配置的是 `DEEPSEEK_API_KEY`
- [ ] 没有使用 OpenAI API
- [ ] API 异常时仍能 fallback 完成 Demo

## GitHub 检查

- [ ] 仓库为 public
- [ ] README 包含项目简介、运行方式、技术栈、环境变量、部署方式
- [ ] README 包含产品链接、GitHub、Product Memo 和补充材料索引
- [ ] commit history 清晰，非一次性提交
- [ ] 无敏感文件：`.env`、私钥、credentials
