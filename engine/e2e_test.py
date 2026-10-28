# -*- coding: utf-8 -*-
"""oilgas-calc MCP 服务器端到端验证（stdio 客户端）。

验证：真实 MCP 协议链路——连接 → 列工具 → 调用 pipe_hydraulic → 校验计算书。
这是将来安装向导 Step 7（MCP ping + 基准题）的雏形。
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(_HERE, "run.py")


async def main():
    params = StdioServerParameters(command="python", args=[RUN])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("tools:", names)
            assert "pipe_hydraulic" in names, "pipe_hydraulic 未注册"
            assert "pipe_wall_thickness" in names, "pipe_wall_thickness 未注册"
            assert "pipe_temperature_drop" in names, "pipe_temperature_drop 未注册"
            assert "unit_convert" in names, "unit_convert 未注册"
            print("[MCP-E2E] 工具注册齐全 -> PASS")

            res = await session.call_tool("pipe_hydraulic", {
                "flow": 100, "flow_unit": "m3/h",
                "inner_diameter": 300, "diameter_unit": "mm",
                "pipe_length": 50000, "length_unit": "m",
                "roughness": 0.05, "roughness_unit": "mm",
                "density": 850, "density_unit": "kg/m3",
                "dynamic_viscosity": 20, "viscosity_unit": "mPa.s",
            })
            text = res.content[0].text
            book = json.loads(text)
            r = {x["name"]: x["value"] for x in book["results"]}
            ok = abs(r["沿程水头损失 h_f"] - 49.63) / 49.63 < 0.02
            print("[MCP-E2E] pipe_hydraulic hf=%.4f m（预期≈49.63）-> %s"
                  % (r["沿程水头损失 h_f"], "PASS" if ok else "FAIL"))
            j = book["judgement"]
            print("[MCP-E2E] judgement.status=%s（白盒：无知识库时未收录）" % j["status"])
            ok2 = j["status"] == "未收录"
            print("[MCP-E2E] 白盒判据行为 -> %s" % ("PASS" if ok2 else "FAIL"))
            if not (ok and ok2):
                sys.exit(1)

            # 量纲防御：错误单位经协议链路返回结构化错误（不抛异常、信息可操作）
            res = await session.call_tool("pipe_hydraulic", {
                "flow": 100, "flow_unit": "MPa",
                "inner_diameter": 300, "diameter_unit": "mm",
                "pipe_length": 50000, "length_unit": "m",
                "roughness": 0.05, "roughness_unit": "mm",
                "density": 850, "density_unit": "kg/m3",
                "dynamic_viscosity": 20, "viscosity_unit": "mPa.s",
            })
            err_text = (res.content[0].text if res.content else "") or ""
            is_error = res.is_error or ("量纲校验失败" in err_text and "MPa" in err_text)
            print("[MCP-E2E] 量纲防御经协议链路（结构化错误）-> %s"
                  % ("PASS" if is_error else "FAIL"))
            if not is_error:
                print("  err_text head:", err_text[:200])
                sys.exit(1)

    print("\n=== MCP 端到端验证全部通过 ===")


asyncio.run(main())
