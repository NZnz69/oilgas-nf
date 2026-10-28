# -*- coding: utf-8 -*-
"""管道水力计算模块（确定性计算，不含经验判断）。

实现公式（形式为教科书通用公式，溯源状态=待校核，待公式卡片收录后绑定）：
- 断面平均流速：v = Q / A，A = π·d²/4
- 雷诺数：Re = ρ·v·d / μ（判别流态的无量纲准数）
- 流态判别：Re < 2000 层流；2000 ≤ Re < 4000 临界区；Re ≥ 4000 紊流
  （分界值为水力学教科书通用取值，标注待校核）
- 沿程阻力系数：
  - 层流：λ = 64 / Re
  - 紊流：Haaland 显式近似 1/√λ = -1.8·lg[(ε/(3.7d))^1.11 + 6.9/Re]
    （科尔布鲁克方程的显式近似，偏差在工程允许范围内；来源标注待校核）
- 达西公式：h_f = λ·(L/d)·(v²/(2g))；Δp = ρ·g·h_f；水力坡降 i = h_f / L
"""

import math

from .calcbook import (
    add_constant, add_formula, add_input, add_intermediate, add_result,
    add_warning, new_calcbook, set_judgement,
)
from .units import convert_to_si, UnitError

G = 9.81  # 重力加速度 m/s2（标准值，计算书常量栏注明）


def pipe_hydraulic(flow, flow_unit, inner_diameter, diameter_unit,
                   pipe_length, length_unit, roughness, roughness_unit,
                   density, density_unit, dynamic_viscosity=None, viscosity_unit=None,
                   kinematic_viscosity=None, kinematic_unit=None):
    """管道沿程水力计算：流速→雷诺数→流态→λ→沿程损失→压降。

    动力黏度与运动黏度二选一提供；两者都给或都不给将报错（不猜测）。
    所有输入经量纲校验后换算为 SI 单位参与计算。
    """
    book = new_calcbook("pipe_hydraulic")

    # ---- 量纲校验与换算（闸门三）----
    q_si, _ = convert_to_si(flow, flow_unit, "flow_volume")
    d_si, _ = convert_to_si(inner_diameter, diameter_unit, "length")
    l_si, _ = convert_to_si(pipe_length, length_unit, "length")
    eps_si, _ = convert_to_si(roughness, roughness_unit, "roughness")
    rho_si, _ = convert_to_si(density, density_unit, "density")

    if d_si <= 0 or l_si <= 0 or rho_si <= 0:
        raise ValueError("管径、管长、密度必须为正值（当前值存在非正数，拒绝计算）")
    if eps_si < 0:
        raise ValueError("绝对粗糙度不能为负值")

    add_input(book, "体积流量", flow, flow_unit, q_si, "m3/s", "flow_volume")
    add_input(book, "管内径", inner_diameter, diameter_unit, d_si, "m", "length")
    add_input(book, "管道长度", pipe_length, length_unit, l_si, "m", "length")
    add_input(book, "绝对粗糙度", roughness, roughness_unit, eps_si, "m", "roughness")
    add_input(book, "介质密度", density, density_unit, rho_si, "kg/m3", "density")

    # ---- 黏度：二选一，互斥校验（不猜测）----
    if (dynamic_viscosity is None) == (kinematic_viscosity is None):
        raise ValueError(
            "动力黏度与运动黏度必须且只能提供其一："
            "两者都提供或都不提供时拒绝计算（避免口径混淆）"
        )
    if dynamic_viscosity is not None:
        mu_si, _ = convert_to_si(dynamic_viscosity, viscosity_unit or "mPa.s", "viscosity_dynamic")
        if mu_si <= 0:
            raise ValueError("动力黏度必须为正值")
        add_input(book, "动力黏度", dynamic_viscosity, viscosity_unit or "mPa.s",
                  mu_si, "Pa.s", "viscosity_dynamic")
        nu_si = mu_si / rho_si
        add_intermediate(book, "运动黏度 ν=μ/ρ", nu_si, "m2/s", "由动力黏度与密度换算")
    else:
        nu_si, _ = convert_to_si(kinematic_viscosity, kinematic_unit or "mm2/s", "viscosity_kinematic")
        if nu_si <= 0:
            raise ValueError("运动黏度必须为正值")
        add_input(book, "运动黏度", kinematic_viscosity, kinematic_unit or "mm2/s",
                  nu_si, "m2/s", "viscosity_kinematic")
        mu_si = nu_si * rho_si
        add_intermediate(book, "动力黏度 μ=ν·ρ", mu_si, "Pa.s", "由运动黏度与密度换算")

    # ---- 公式登记（溯源状态：待校核，待公式卡片收录后绑定）----
    add_formula(book, "断面平均流速", "v = Q / A, A = π·d²/4",
                "水力学教科书通用公式（公式卡片收录后绑定出处）", status="待校核")
    add_formula(book, "雷诺数", "Re = ρ·v·d / μ = v·d / ν",
                "水力学教科书通用公式（公式卡片收录后绑定出处）", status="待校核")
    add_formula(book, "流态判别", "Re<2000 层流；2000≤Re<4000 临界区；Re≥4000 紊流",
                "分界值为教科书通用取值（待公式卡片收录后绑定出处）", status="待校核")
    add_formula(book, "沿程阻力系数(层流)", "λ = 64/Re",
                "水力学教科书通用公式（待公式卡片收录后绑定出处）", status="待校核")
    add_formula(book, "沿程阻力系数(紊流)", "1/√λ = -1.8·lg[(ε/3.7d)^1.11 + 6.9/Re] (Haaland)",
                "科尔布鲁克方程显式近似（待公式卡片收录后绑定出处）", status="待校核")
    add_formula(book, "达西沿程损失", "h_f = λ·(L/d)·(v²/2g)",
                "水力学教科书通用公式（待公式卡片收录后绑定出处）", status="待校核")
    add_constant(book, "重力加速度 g", G, "m/s2", "物理常量（标准值）")
    add_constant(book, "圆周率 π", math.pi, "-", "数学常量")

    # ---- 计算：中间量逐步留痕 ----
    area = math.pi * d_si ** 2 / 4.0
    v = q_si / area
    add_intermediate(book, "过流断面积 A", area, "m2", "A = π·d²/4")
    add_intermediate(book, "断面平均流速 v", v, "m/s", "v = Q/A")

    re = rho_si * v * d_si / mu_si
    add_intermediate(book, "雷诺数 Re", re, "-", "Re = ρ·v·d/μ")

    if re < 2000.0:
        regime = "层流"
        regime_note = "Re < 2000"
        lam = 64.0 / re
        lam_formula = "λ = 64/Re（层流）"
    elif re < 4000.0:
        regime = "临界区（过渡区）"
        regime_note = "2000 ≤ Re < 4000"
        lam = 64.0 / re  # 临界区无成熟公式，按层流估算并告警
        lam_formula = "λ = 64/Re（临界区无成熟通用公式，按层流估算）"
        add_warning(book, "雷诺数处于临界区（2000≤Re<4000）：流动状态不稳定，"
                          "λ 按层流公式估算仅供参考，工程上应避开该区间运行或做专项分析")
    else:
        regime = "紊流"
        regime_note = "Re ≥ 4000"
        rel = eps_si / (3.7 * d_si)
        lam = (-1.8 * math.log10(rel ** 1.11 + 6.9 / re)) ** -2
        lam_formula = "Haaland 显式近似（紊流）"
    add_intermediate(book, "流态", regime, "-", regime_note)
    add_intermediate(book, "沿程阻力系数 λ", lam, "-", lam_formula)

    hf = lam * (l_si / d_si) * (v ** 2 / (2.0 * G))
    dp = rho_si * G * hf
    i_slope = hf / l_si
    add_intermediate(book, "速度水头 v²/2g", v ** 2 / (2.0 * G), "m", "动能项")

    # ---- 结果（有效位数 6 位，不虚假精确）----
    add_result(book, "断面平均流速 v", v, "m/s")
    add_result(book, "雷诺数 Re", re, "-")
    add_result(book, "流态", regime, "-", regime_note)
    add_result(book, "沿程阻力系数 λ", lam, "-", lam_formula)
    add_result(book, "沿程水头损失 h_f", hf, "m")
    add_result(book, "沿程压降 Δp", dp, "Pa",
               note="Δp = ρ·g·h_f")
    add_result(book, "沿程压降 Δp（MPa）", dp / 1e6, "MPa",
               note="工程常用单位换算值（v0.1.1 起随计算书直接附带，免去二次换算）")
    add_result(book, "水力坡降 i", i_slope, "m/m", "i = h_f / L")

    # ---- 判据对照（知识库状态）----
    set_judgement(book, "输油管道经济流速", value=v, unit="m/s")
    set_judgement(book, "雷诺数", value=re, unit="-")

    if v > 4.5:
        add_warning(book, "流速超过 4.5 m/s（水击与冲刷风险提示阈值，待判据卡片收录后以"
                          "入库区间为准）——本提示为安全兜底，不代表已校核结论")
    return book
