# NF · 油气储运智能辅助系统（oilgas-nf）

> 面向 TeleAgent Desktop（星辰超级智能体）的油气储运专业辅助系统。
> 当前版本 v0.1.0 · 阶段 1 机制框架：薄壳 Skill + 确定性计算引擎（MCP）+ 白盒空知识库。
> 设计原则：只信文件不信记忆、计算必须走引擎、未收录即拒答。

## 这是什么

| 组件 | 位置（仓库内） | 作用 |
|---|---|---|
| Skill「油气储运NF专家」 | `skill/oilgas-nf-expert/` | 身份先行路由（学生/教师/运维/设计）+ 反幻觉规则 + 知识库（白盒空置待灌入） |
| 计算引擎 oilgas-calc | `engine/` | MCP stdio 服务，5 个工具：水力/温降/壁厚计算 + 单位换算量纲校验 + 单位诊断；每个结果带可复算的计算书 |
| 基准题库 | `data/baselines/baselines.json` | 5 道带标准答案的基准题，证明引擎没乱算（每日回归与装机自检共用） |
| 每日任务定义 | `jobs/daily-task.json` | 每日五件事（自检/回归/扫描/事件收录/HTML 报告）的任务定义，阶段 4 注册 |
| 身份模板 | `identity/identity-template.md` | 四选一身份模板（个人身份不进包，防多人共用串身份） |
| 安装向导 | `install.ps1` | 一键安装：环境检测→部署 Skill→注册→生成 MCP 配置→引擎自检 |

## 快速开始（下载本仓库的人）

**前置**：已安装并登录 TeleAgent Desktop；Python 3.10+（勾选 Add to PATH）。

```powershell
# 1. 解压（或 git clone）后，进入 NF 目录
cd NF

# 2. 运行一键安装
powershell -ExecutionPolicy Bypass -File install.ps1

# 3. 按脚本打印的 JSON 注册 MCP：
#    TeleAgent Desktop → 左下角头像 → 工具设置 → MCP 配置 → 添加 → 粘贴 → 保存
#    （JSON 同时保存在 mcp-config.generated.json）

# 4. 重启 TeleAgent Desktop

# 5. 试算一句话：
#    「帮我算：流量100m3/h、内径300mm、长度50km、粗糙度0.05mm、密度850kg/m3、黏度20mPa.s 的沿程压降」
```

首次使用会询问身份（学生/教师/运维/设计）。知识库当前为**白盒空置**——专业内容会如实回答「未收录」，请提供正版规范/教材文件灌入（在 TeleAgent 对话中把文件给它即可，五步灌入流程：解析→草稿→校核→转正→登记）。

## 上传到 GitHub（维护者）

本目录即 Git 仓库根（含 .gitignore / manifest.json / install.ps1）。

**路线 A · 命令行（推荐）**

```powershell
# 0. 安装 git：https://git-scm.com/download/win（装完重开终端）
cd "NF 所在目录"

# 1. 初始化并提交
git init
git add .
git commit -m "NF v0.1.0: 阶段1机制框架（Skill+引擎+白盒知识库+一键安装）"

# 2. 在 github.com 上新建仓库（建议先建 Private 私有仓库）
#    然后关联并推送（把 <你的用户名>/<仓库名> 替换掉）：
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

**路线 B · GitHub Desktop（图形界面，无命令行）**
1. 安装 GitHub Desktop（desktop.github.com）并登录；
2. File → Add Local Repository → 选择 NF 目录（若未初始化会提示 Create a New Repository，直接确认）；
3. 填写提交说明 → Commit to main；
4. Publish repository → 勾选 Private（建议）→ Publish。

**后续更新**：改动文件后 `git add . && git commit -m "说明" && git push`（或 GitHub Desktop 的 Commit/Push 按钮）。

## 从 GitHub 安装（其他设备）

```powershell
git clone https://github.com/<你的用户名>/<仓库名>.git
cd <仓库名>
powershell -ExecutionPolicy Bypass -File install.ps1
# 之后同「快速开始」3-5 步：粘贴 MCP JSON → 重启 → 试算
```

没有 git 时：GitHub 仓库页 → Code → Download ZIP → 解压 → 同上运行 install.ps1。

## 验证命令

```powershell
python engine\selftest.py   # 模块级 12 项基准自测
python engine\e2e_test.py   # MCP 协议端到端验证（连接→调用→校验计算书）
```

## 变更记录

**v0.1.1（实机启用验证 + 发行包加固）**：在真实 TeleAgent Desktop 上完成启用验证（Skill 加载、MCP 连接、基准题与手算一致、量纲防御返回结构化错误）。实操发现并落地修复：①引擎 BUG——计算书多判据互相覆盖只留最后一条（`set_judgement` 改为 `judgements` 数组追加）；②压降结果直接附带 Pa/MPa 双单位；③SKILL.md 新增"呈现与翻译规则"（计算书提炼呈现不全文粘贴 JSON、单位别名翻译职责、黏度必须先问类型）；④新增 `references/unit-aliases.md` 单位别名翻译表；⑤install.ps1 面向其他用户加固——Python 不在 PATH 时自动回退探测 TeleAgent 内置运行时、技能目录自动探测 `users\*\skills`、MCP JSON 使用探测到的 Python 路径；⑥新增 `docs/` 目录收录三份设计文档（痛点与解决方案/实施路线图/分发部署方案），发行包自包含。回归验证 selftest 12/12 + e2e 全通过。

**v0.1.0（阶段 1 机制框架）**：Skill + 引擎 + 白盒知识库 + 一键安装；自测捕获并修复三个真实 BUG（腐蚀裕量双重累加、壁厚结果单位标错、server 导入笔误）；install.ps1 真实跑通（含 UTF-8 BOM 修复 PS5.1 中文解析）。

## 诚实边界（v0.1.x）

- 公式溯源状态均为「待校核」：公式形式为教科书通用公式，条文出处待公式卡片收录后绑定，正式使用前须人工校核；
- 判据区间未入库：无 `formulas/judges.json` 时所有计算不判定合理区间（计算书如实标注「未收录」）；
- 基准题为手工预核算例，待教材例题收录后逐题替换；
- 知识库白盒空置是设计行为：未收录即拒答，拒绝用模型记忆编造专业内容；
- 规范全文受版权保护，知识库只存索引、要点摘编与官方查阅渠道，不存全文；
- install.ps1 的平台注册步骤依赖本机 TeleAgent 的 skill-creator 接口，接口不可用时降级为指引提示（不静默失败）。

## 工程结构

```
NF/
├─ install.ps1            # 一键安装向导（UTF-8 BOM，PS 5.1 兼容）
├─ manifest.json          # 包清单：版本、组件、验收状态、诚实边界
├─ .gitignore             # 排除 __pycache__、生成配置、日志
├─ skill/
│  └─ oilgas-nf-expert/   # Skill 源（安装目标：%TELEAGENT_CONFIG_DIR%/skills/）
│     ├─ SKILL.md         # 薄壳：三条铁律 + 身份路由 + 引擎规则
│     └─ references/      # knowledge-index / identity-routing / card-templates + 六个空知识子目录
├─ engine/
│  ├─ run.py              # MCP 启动入口（注册用）
│  ├─ requirements.txt    # mcp>=2.0.0
│  ├─ selftest.py         # 12 项基准自测
│  ├─ e2e_test.py         # MCP 端到端验证
│  └─ oilgas_calc/        # server/units/calcbook/hydraulic/thermal/strength
├─ data/
│  ├─ baselines/baselines.json   # 基准题库（5 题）
│  └─ events/             # 事件库目录（阶段 4 启用 SQLite）
├─ docs/                  # 设计文档：痛点与解决方案 / 实施路线图 / 分发部署方案（HTML，双击即看）
├─ jobs/daily-task.json   # 每日五件事任务定义（阶段 4 注册）
└─ identity/identity-template.md
```

维护规则：**仓库是唯一源**——改 Skill 或引擎请改仓库内文件，运行 install.ps1 同步到本机平台目录；运行产物（mcp-config.generated.json、__pycache__）不入库。

## 路线图

阶段 1 机制框架 ✅ → 阶段 2 内容灌入（待用户提供正版规范/教材）→ 阶段 3 引擎验证（教材例题替换基准）→ 阶段 4 定时任务 → 阶段 5 角色扩展 → 分发（本仓库即"团队源版"基座）。

配套设计文档（本工作区）：《油气储运NF痛点与解决方案汇总》《油气储运NF实施路线图》《油气储运NF分发部署方案》。

> AI生成
