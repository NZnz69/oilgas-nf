# -*- coding: utf-8 -*-
"""oilgas-calc MCP 服务器启动入口（stdio）。

用途：MCP stdio 注册的 command 入口——
  command: python
  args:    <本文件绝对路径>
直接以文件方式运行时，Python 自动将本文件所在目录（engine/）加入 sys.path，
从而正确解析 oilgas_calc 包。

可选环境变量：
- NF_KNOWLEDGE_DIR：知识库 references 目录（判据卡片所在）。未设置时
  引擎判据一律返回「未收录」（白盒行为）。
"""

from oilgas_calc.server import main

if __name__ == "__main__":
    main()
