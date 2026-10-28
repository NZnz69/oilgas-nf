# -*- coding: utf-8 -*-
"""引擎基准自测：手工预核算例 vs 引擎输出（阶段3回归机制的雏形）。

算例与手工预期值（预核）：
[HYD-01] Q=100 m3/h, d=300mm, L=50km, eps=0.05mm, rho=850, mu=20mPa.s
         预期 v≈0.3931 m/s, Re≈5012(紊流), hf≈49.7 m, dp≈0.414 MPa
[THM-01] G=100 kg/s, D=400mm, L=50km, K=1.59 W/(m2.K), T0=5C, TR=50C, cp=2.0 kJ/(kg.K)
         预期 aL≈0.5, TL≈5+45e^-0.5≈32.3 C
[STR-01] P=6.4MPa, D=508mm, sig=360MPa, F=0.5, phi=1, t=1, C=2mm
         预期 delta≈11.03 mm
[STR-02] 同参数 check 模式，名义壁厚 11.03mm → P_allow≈6.4 MPa（回代自洽）
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oilgas_calc import hydraulic, thermal, strength
from oilgas_calc.calcbook import finalize

passed, failed = 0, 0

def check(tag, got, expect, tol=0.02):
    global passed, failed
    ok = abs(got - expect) / max(abs(expect), 1e-9) <= tol
    print("[%s] got=%.6g expect=%.6g -> %s" % (tag, got, expect, "PASS" if ok else "FAIL"))
    if ok: passed += 1
    else: failed += 1

# ---- HYD-01 ----
b = hydraulic.pipe_hydraulic(100, "m3/h", 300, "mm", 50000, "m", 0.05, "mm",
                             850, "kg/m3", dynamic_viscosity=20, viscosity_unit="mPa.s")
r = {x["name"]: x["value"] for x in b["results"]}
check("HYD-01 v", r["断面平均流速 v"], 0.3931, 0.01)
check("HYD-01 Re", r["雷诺数 Re"], 5012, 0.01)
check("HYD-01 hf", r["沿程水头损失 h_f"], 49.7, 0.02)
check("HYD-01 dp_MPa", r["沿程压降 Δp"] / 1e6, 0.414, 0.02)
assert r["流态"] == "紊流", "流态判别错误"
print("[HYD-01 regime] 紊流 -> PASS"); passed += 1

# 量纲防御：错误单位必须报错
try:
    hydraulic.pipe_hydraulic(100, "MPa", 300, "mm", 50000, "m", 0.05, "mm",
                             850, "kg/m3", dynamic_viscosity=20, viscosity_unit="mPa.s")
    print("[HYD-E01] 未报错 -> FAIL"); failed += 1
except Exception as e:
    print("[HYD-E01] 量纲拦截生效: %s -> PASS" % str(e)[:60]); passed += 1

# ---- THM-01 ----
b = thermal.pipe_temperature_drop("drop", 100, "kg/s", 0.4, "m", 50000, "m",
                                  1.59, "W/(m2.K)", 5, "C", inlet_temp=50, specific_heat=2.0)
r = {x["name"]: x["value"] for x in b["results"]}
check("THM-01 TL", r["末端油温 T_L"], 32.3, 0.02)
# 反算自洽：末端 32.293 反推起点应≈50
b = thermal.pipe_temperature_drop("required_inlet", 100, "kg/s", 0.4, "m", 50000, "m",
                                  1.59, "W/(m2.K)", 5, "C", outlet_temp=32.293, specific_heat=2.0)
r = {x["name"]: x["value"] for x in b["results"]}
check("THM-01 TR(back)", r["所需起点油温 T_R"], 50.0, 0.01)

# ---- STR-01 / STR-02 ----
b = strength.pipe_wall_thickness("design", 6.4, "MPa", 508, "mm", 360, "MPa",
                                 0.5, weld_factor=1.0, temperature_derating=1.0,
                                 corrosion_allowance=2, allowance_unit="mm")
r = {x["name"]: x["value"] for x in b["results"]}
check("STR-01 delta_mm", r["计算所需壁厚 δ"], 11.03, 0.02)

b = strength.pipe_wall_thickness("check", 6.4, "MPa", 508, "mm", 360, "MPa",
                                 0.5, weld_factor=1.0, temperature_derating=1.0,
                                 corrosion_allowance=2, allowance_unit="mm",
                                 nominal_thickness=11.03, thickness_unit="mm")
r = {x["name"]: x["value"] for x in b["results"]}
check("STR-02 pallow_MPa", r["最大许用压力（MPa）"], 6.4, 0.02)

# 白盒行为：无知识库时判据必须「未收录」
import os
os.environ.pop("NF_KNOWLEDGE_DIR", None)
b = hydraulic.pipe_hydraulic(100, "m3/h", 300, "mm", 50000, "m", 0.05, "mm",
                             850, "kg/m3", dynamic_viscosity=20, viscosity_unit="mPa.s")
j = b["judgement"]
ok = j.get("status") == "未收录"
print("[WHITE-BOX judgement] status=%s -> %s" % (j.get("status"), "PASS" if ok else "FAIL"))
if ok: passed += 1
else: failed += 1

# 计算书结构完整性：七要素齐全
need = ["inputs", "formulas", "constants", "intermediates", "results", "judgement", "warnings"]
ok = all(k in b for k in need)
print("[CALCBOOK structure] %s -> %s" % ("齐全" if ok else "缺项", "PASS" if ok else "FAIL"))
if ok: passed += 1
else: failed += 1

print("\n=== 自测汇总: PASS=%d FAIL=%d ===" % (passed, failed))
sys.exit(0 if failed == 0 else 1)
