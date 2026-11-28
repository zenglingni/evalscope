```
mcp_agent_eval/
├── mcp_traces.jsonl    # MCP会话trace数据
├── mcp_eval_demo.py    # 主评测脚本
├── start_service.py    # 可视化看板启动脚本
└── outputs/            # 评测结果输出目录
```
mcp_traces.jsonl（评测样本，MCP Agent 会话轨迹）

浏览器打开：`http://127.0.0.1:9000`

- 可以看到每一条 MCP 会话、工具调用、LLM-Judge 分数 + 理由
- 支持筛选低分 case，专门抓 Agent 漏调用、错调用工具的样本

### 6. 扩展说明（对接真实 MCP Agent）

真实 MCP Agent 产出 trace 时，只需要按照上面`mcp_traces.jsonl`的格式持续写入：

- `query`：原始用户提问
- `target_tool`：预期应该调用的工具（基线）
- `trace`：完整对话 + toolcall+tool 返回的数组
- `judge_rubric`：该条 case 对应的评审规则

> 
> 规避坑：不再依赖`mcp`库子进程通信，避开 FastMCP/MCPServer 版本冲突，专心做评测。

### 7. 可选升级点

如果你想要**自动统计指标**：通过率（score≥6 视为合格）、错用工具 top 排行，我可以再加一段结果解析脚本，读取`result_summary.json`自动汇总报表。

conda create -n evalscope python=3.12 #创建名称为evalscope, python版本为3.12的虚拟环境
conda activate evalscope # 激活虚拟环境
(evalscope) zengzini@zengzinideMacBook-Air mcp_agent_eval % PYTHONNOUSERSITE=1 python judge_and_export.py
(evalscope) zengzini@zengzinideMacBook-Air mcp_agent_eval % PYTHONNOUSERSITE=1 python start_service.py
ls -R ./outputs
ls -lah
brew install tree
tree ./outputs -L 4
# 1. 先进入项目目录
cd /Users/zengzini/Downloads/eval/test/evalscope/mcp_agent_eval

# 2. 初始化git（只需要执行一次）
git init

# 3. 添加当前目录所有文件
git add .

# 4. 提交
git commit -m "feat: mcp bridge evalscope demo"
# 把远程仓库地址绑定（替换成你自己仓库地址）
git remote add origin https://github.com/zenglingni/evalscope.git

# 第一次推送
git push -u origin main
