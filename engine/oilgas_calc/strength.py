# -*- coding: utf-8 -*-
"""管道壁厚计算模块（确定性计算）。

实现公式（形式为输气/输油管道设计规范通用公式形式，溯源状态=待校核）：
- 壁厚计算：δ = P·D / (2·σs·F·φ·t) + C
  P：设计压力；D：管外径；σs：管材最小屈服强度；
  F：设计系数（地区等级相关）；φ：焊缝系数；t：温度折减系数；C：腐蚀裕量。
  公式形式对应 GB 50251 输气管道一类地区通用表达（具体条文号待规范卡片收录后绑定）。
- 强度反算（校核模式）：给定壁厚反求允许压力 P_allow = 2·σs·F·φ·t·(δ−C)/D。
"""

from .calcbook import (
    add_formula, add_input, add_intermediate, add_result,
    add_warning, new_calcbook, set_judgement,
)
from .units import convert_to_si


def pipe_wall_thickness(mode, design_pressure, pressure_unit, outer_diameter, diameter_unit,
                        yield_strength, strength_unit, design_factor,
                        weld_factor=1.0, temperature_derating=1.0,
                        corrosion_allowance=0.0, allowance_unit="mm",
                        nominal_thickness=None, thickness_unit="mm"):
    """壁厚计算（mode='design'）或许用压力校核（mode='check'）。

    mode='design'：由设计压力计算所需壁厚；
    mode='check'：由名义壁厚反算最大许用压力。
    设计系数、焊缝系数、温度折减系数由用户按规范选取（Skill 侧引导查卡片），
    引擎只做确定性计算并留痕，不内置未溯源的系数推荐值。
    """
    book = new_calcbook("pipe_wall_thickness")

    # ---- 量纲校验与换算 ----
    p_si, _ = convert_to_si(design_pressure, pressure_unit, "pressure")
    d_si, _ = convert_to_si(outer_diameter, diameter_unit, "length")
    sig_si, _ = convert_to_si(yield_strength, strength_unit, "stress")
    c_si, _ = convert_to_si(corrosion_allowance, allowance_unit, "length")

    if p_si <= 0 or d_si <= 0 or sig_si <= 0:
        raise ValueError("设计压力、管外径、屈服强度必须为正值，拒绝计算")
    if not (0 < design_factor <= 1):
        raise ValueError("设计系数 F 应在 (0, 1] 区间（规范取值待卡片收录后核对），拒绝计算")
    if not (0 < weld_factor <= 1):
        raise ValueError("焊缝系数 φ 应在 (0, 1] 区间，拒绝计算")
    if not (0 < temperature_derating <= 1):
        raise ValueError("温度折减系数 t 应在 (0, 1] 区间，拒绝计算")
    if c_si < 0:
        raise ValueError("腐蚀裕量不能为负值")

    add_input(book, "设计压力", design_pressure, pressure_unit, p_si, "Pa", "pressure")
    add_input(book, "管外径", outer_diameter, diameter_unit, d_si, "m", "length")
    add_input(book, "最小屈服强度", yield_strength, strength_unit, sig_si, "Pa", "stress")
    add_input(book, "设计系数 F", design_factor, "-", design_factor, "-", "dimensionless")
    add_input(book, "焊缝系数 φ", weld_factor, "-", weld_factor, "-", "dimensionless")
    add_input(book, "温度折减系数 t", temperature_derating, "-", temperature_derating, "-", "dimensionless")
    add_input(book, "腐蚀裕量 C", corrosion_allowance, allowance_unit, c_si, "m", "length")

    add_formula(book, "壁厚计算", "δ = P·D / (2·σs·F·φ·t) + C",
                "输气/输油管道设计规范通用公式形式（GB 50251 系列形式；条文号待规范卡片收录后绑定）",
                status="待校核")
    add_warning(book, "公式形式待校核：不同规范（GB 50251/GB 50369/ASME B31.4/B31.8）"
                      "的系数定义与取值存在差异，正式使用前须经公式卡片校核转正")

    denom = 2.0 * sig_si * design_factor * weld_factor * temperature_derating

    if mode == "design":
        calc_thickness = p_si * d_si / denom
        add_intermediate(book, "承压计算壁厚 δ_calc", calc_thickness, "m",
                         "P·D/(2σs·F·φ·t)，不含腐蚀裕量")
        total = calc_thickness + c_si
        add_intermediate(book, "含腐蚀裕量总需求 δ", total, "m", "δ_calc + C")
        add_result(book, "计算所需壁厚 δ", total * 1000.0, "mm",
                   "建议按常用壁厚序列向上取整（序列待规范卡片收录后提供）")
        add_warning(book, "常用壁厚序列与最小壁厚约束尚未入库：本结果为理论计算值，"
                          "选型取整须对照规范卡片人工确认")
        set_judgement(book, "管道壁厚", value=total * 1000.0, unit="mm")
        return book

    if mode == "check":
        if nominal_thickness is None:
            raise ValueError("mode='check' 需要提供 nominal_thickness（名义壁厚）")
        tn_si, _ = convert_to_si(nominal_thickness, thickness_unit, "length")
        add_input(book, "名义壁厚", nominal_thickness, thickness_unit, tn_si, "m", "length")
        if tn_si - c_si <= 0:
            raise ValueError("名义壁厚扣除腐蚀裕量后非正值，无法校核，拒绝计算")
        p_allow = denom * (tn_si - c_si) / d_si
        add_intermediate(book, "有效承压壁厚", tn_si - c_si, "m", "δ_n − C")
        add_result(book, "最大许用压力 P_allow", p_allow, "Pa",
                   "如需 MPa 请用 unit_convert 换算")
        add_result(book, "最大许用压力（MPa）", p_allow / 1e6, "MPa", "换算值")
        if p_allow < p_si:
            add_warning(book, "许用压力 %.4f MPa 低于设计压力 %.4f MPa：壁厚不足，不满足强度要求"
                              % (p_allow / 1e6, p_si / 1e6))
            verdict = "不满足"
        else:
            verdict = "满足"
        add_result(book, "强度校核结论", verdict, "-",
                   "按 P_allow 与设计压力比较（公式形式待校核）")
        return book

    raise ValueError("mode 必须为 'design'（计算壁厚）或 'check'（校核许用压力）")
