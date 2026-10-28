# -*- coding: utf-8 -*-
"""管道热力计算模块（苏霍夫温降公式，确定性计算）。

实现公式（教科书通用形式，溯源状态=待校核，待公式卡片收录后绑定）：
- 温降（苏霍夫公式）：T_L = T_0 + (T_R − T_0)·exp(−a·L)
  其中 a = K·π·D / (G·c_p)
  T_R：起点油温；T_0：环境温度（周围介质温度）；T_L：距起点 L 处油温；
  K：总传热系数；D：管外径（计算外表面积用）；G：质量流量；c_p：比热容。
- 反算模式：给定末端温度求需要起点温度（同一公式代数变形，不引入新经验式）。
"""

import math

from .calcbook import (
    add_constant, add_formula, add_input, add_intermediate, add_result,
    add_warning, new_calcbook, set_judgement,
)
from .units import convert_to_si


def pipe_temperature_drop(mode, mass_flow, flow_unit, outer_diameter, diameter_unit,
                           length, length_unit, total_heat_transfer_coefficient, kt_unit,
                           environment_temp, env_temp_unit,
                           inlet_temp=None, inlet_temp_unit="C",
                           outlet_temp=None, outlet_temp_unit="C",
                           specific_heat=None, cp_unit="kJ/(kg.K)"):
    """苏霍夫公式温降计算。

    mode="drop"：由起点温度计算末端温度（需提供 inlet_temp）；
    mode="required_inlet"：由末端温度反算所需起点温度（需提供 outlet_temp）。
    温度换算按偏移换算（℃↔K）处理，公式在 SI（K）下执行，结果按输入温度类别返回。
    """
    book = new_calcbook("pipe_temperature_drop")

    # ---- 量纲校验与换算 ----
    g_si, _ = convert_to_si(mass_flow, flow_unit, "flow_mass")
    d_si, _ = convert_to_si(outer_diameter, diameter_unit, "length")
    l_si, _ = convert_to_si(length, length_unit, "length")
    k_si, _ = convert_to_si(total_heat_transfer_coefficient, kt_unit, "thermal_conductance")
    cp_si, _ = convert_to_si(specific_heat or 2.0, cp_unit, "specific_heat")
    t0_si, _ = convert_to_si(environment_temp, env_temp_unit, "temperature")

    if g_si <= 0 or d_si <= 0 or l_si <= 0 or k_si <= 0 or cp_si <= 0:
        raise ValueError("质量流量、管径、长度、总传热系数、比热容必须为正值，拒绝计算")
    if k_si <= 0:
        raise ValueError("总传热系数必须为正值")

    add_input(book, "质量流量", mass_flow, flow_unit, g_si, "kg/s", "flow_mass")
    add_input(book, "管外径", outer_diameter, diameter_unit, d_si, "m", "length")
    add_input(book, "计算段长度", length, length_unit, l_si, "m", "length")
    add_input(book, "总传热系数 K", total_heat_transfer_coefficient, kt_unit,
              k_si, "W/(m2.K)", "thermal_conductance")
    add_input(book, "比热容 cp", specific_heat, cp_unit, cp_si, "J/(kg.K)", "specific_heat",
              source="user" if specific_heat is not None else "default_2.0kJ:默认值，建议按介质卡片取值")
    add_input(book, "环境温度", environment_temp, env_temp_unit, t0_si, "K", "temperature")
    if specific_heat is None:
        add_warning(book, "比热容未提供，已采用默认值 2.0 kJ/(kg·K)——该默认值未经卡片校核，"
                          "正式计算请提供介质实测值或引用介质物性卡片")

    # ---- 公式登记 ----
    add_formula(book, "苏霍夫温降公式", "T_L = T_0 + (T_R − T_0)·exp(−a·L)",
                "油气集输/输油管道教科书通用公式（待公式卡片收录后绑定出处）", status="待校核")
    add_formula(book, "温降系数", "a = K·π·D / (G·c_p)",
                "苏霍夫公式配套定义（待公式卡片收录后绑定出处）", status="待校核")
    add_constant(book, "圆周率 π", math.pi, "-", "数学常量")

    # ---- 计算 ----
    a = k_si * math.pi * d_si / (g_si * cp_si)
    add_intermediate(book, "温降系数 a", a, "1/m", "a = K·π·D/(G·c_p)")
    exponent = a * l_si
    add_intermediate(book, "指数项 a·L", exponent, "-", "e 的指数")
    decay = math.exp(-exponent)
    add_intermediate(book, "衰减因子 e^(−aL)", decay, "-", "温降几何衰减项")

    if mode == "drop":
        if inlet_temp is None:
            raise ValueError("mode='drop' 需要提供 inlet_temp（起点温度）")
        tr_si, _ = convert_to_si(inlet_temp, inlet_temp_unit, "temperature")
        add_input(book, "起点油温", inlet_temp, inlet_temp_unit, tr_si, "K", "temperature")
        tl_si = t0_si + (tr_si - t0_si) * decay
        add_intermediate(book, "末端油温 T_L", tl_si, "K", "代入苏霍夫公式")
        out_si = tl_si
        out_name = "末端油温 T_L"
        out_note = "T_L = T_0 + (T_R − T_0)·e^(−aL)"
    elif mode == "required_inlet":
        if outlet_temp is None:
            raise ValueError("mode='required_inlet' 需要提供 outlet_temp（末端温度）")
        tl_si, _ = convert_to_si(outlet_temp, outlet_temp_unit, "temperature")
        add_input(book, "末端油温", outlet_temp, outlet_temp_unit, tl_si, "K", "temperature")
        if decay <= 1e-12:
            raise ValueError("e^(−aL) 过小（a·L 过大），反算起点温度将发散，拒绝计算")
        tr_si = t0_si + (tl_si - t0_si) / decay
        add_intermediate(book, "所需起点油温 T_R", tr_si, "K", "苏霍夫公式反解")
        out_si = tr_si
        out_name = "所需起点油温 T_R"
        out_note = "T_R = T_0 + (T_L − T_0)/e^(−aL)"
    else:
        raise ValueError("mode 必须为 'drop'（正算末端温度）或 'required_inlet'（反算起点温度）")

    # ---- 结果：按摄氏度返回（工程习惯），同时在中间量保留 K ----
    out_c = out_si - 273.15
    add_result(book, out_name, out_c, "C", out_note)
    add_result(book, out_name + "（开尔文）", out_si, "K", "SI 中间值")

    # ---- 判据 ----
    set_judgement(book, "埋地热油管道末端温度", value=out_c, unit="C")
    if mode == "required_inlet" and out_c > 90:
        add_warning(book, "反算起点温度超过 90 ℃（高于常见加热炉出口温度量级，"
                          "待判据卡片收录后以入库区间为准）——本提示为安全兜底，不代表已校核结论")
    return book
