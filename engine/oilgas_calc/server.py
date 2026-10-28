# -*- coding: utf-8 -*-
"""油气储运 NF 计算引擎 MCP 服务器（stdio）。

工具清单：
- unit_convert        单位换算与量纲校验
- pipe_hydraulic      管道水力计算（雷诺数→流态→λ→沿程损失→压降）
- pipe_temperature_drop 苏霍夫温降（正算末端温度 / 反算所需起点温度）
- pipe_wall_thickness 壁厚计算（设计壁厚 / 许用压力校核）
- list_dimensions     列出全部物理量类别与单位（诊断）

行为约定：
- 每个计算工具返回计算书 JSON（输入、公式及溯源状态、常数、中间量、
  结果、判据对照状态、告警），模型只解释计算书，绝不修改数值。
- 量纲/参数校验失败时返回结构化错误 JSON（含可操作的修正提示），
  而不是抛出无详情异常——失败即报错，错误可定位。

环境变量：
- NF_KNOWLEDGE_DIR：知识库 references 目录（判据卡片所在）；未设置或
  无卡片时判据一律返回「未收录」（白盒行为）。
"""

import json

from mcp.server.mcpserver import MCPServer

from .calcbook import finalize
from .units import UnitError, convert_to_si, list_units
from .units import UNIT_TABLES
from . import hydraulic, strength, thermal

server = MCPServer("oilgas-calc")

_DIMENSIONS_DOC = (
    "length/pressure/flow_volume/flow_mass/density/viscosity_dynamic/"
    "viscosity_kinematic/temperature/roughness/thermal_conductance/"
    "specific_heat/stress/velocity/dimensionless"
)


def _error(kind, message, hint=""):
    """结构化错误返回（可操作：指明错误与修正方向）。"""
    payload = {"error": kind, "message": message, "hint": hint}
    return json.dumps(payload, ensure_ascii=False, indent=2)


@server.tool()
def unit_convert(value: float, from_unit: str, to_unit: str, dimension: str) -> str:
    """单位换算与量纲校验：把 value 从 from_unit 换算为 to_unit。

    dimension 为物理量类别（%s）。
    温度类别按偏移换算（C↔K）。单位不属于该类别时返回结构化错误并列出可用单位。
    """ % _DIMENSIONS_DOC
    try:
        si_val, si_unit = convert_to_si(value, from_unit, dimension)
    except UnitError as e:
        return _error("量纲校验失败", str(e), "可用 list_dimensions 查询该类别全部可用单位")
    try:
        if dimension == "temperature":
            if to_unit not in ("C", "K"):
                raise UnitError("目标温度单位 %r 不受支持（可用: C, K）" % to_unit)
            out = si_val - 273.15 if to_unit == "C" else si_val
            return finalize({
                "tool": "unit_convert",
                "inputs": [{"name": "输入值", "value": value, "unit": from_unit,
                            "dimension": dimension, "si_value": si_val, "si_unit": si_unit}],
                "results": [{"name": "换算结果", "value": round(out, 8), "unit": to_unit,
                             "note": "温度偏移换算"}],
                "judgement": {"status": "不适用", "note": "纯单位换算无需判据"},
                "warnings": [],
            })
        units = list_units(dimension).get(dimension, [])
        if to_unit not in units:
            raise UnitError("目标单位 %r 不属于物理量类别 %r（可用: %s）"
                            % (to_unit, dimension, ", ".join(units)))
        factor = UNIT_TABLES[dimension][to_unit]
        out = si_val / factor
        return finalize({
            "tool": "unit_convert",
            "inputs": [{"name": "输入值", "value": value, "unit": from_unit,
                        "dimension": dimension, "si_value": si_val, "si_unit": si_unit}],
            "results": [{"name": "换算结果", "value": round(out, 8), "unit": to_unit,
                         "note": "线性换算，因子 %.12g" % (UNIT_TABLES[dimension][from_unit] / factor)}],
            "judgement": {"status": "不适用", "note": "纯单位换算无需判据"},
            "warnings": [],
        })
    except UnitError as e:
        return _error("量纲校验失败", str(e), "可用 list_dimensions 查询该类别全部可用单位")


@server.tool()
def pipe_hydraulic(flow: float, flow_unit: str, inner_diameter: float, diameter_unit: str,
                   pipe_length: float, length_unit: str, roughness: float, roughness_unit: str,
                   density: float, density_unit: str,
                   dynamic_viscosity: float = None, viscosity_unit: str = "mPa.s",
                   kinematic_viscosity: float = None, kinematic_unit: str = "mm2/s") -> str:
    """管道沿程水力计算：流速→雷诺数→流态→沿程阻力系数→沿程损失→压降→水力坡降。

    动力黏度(dynamic_viscosity)与运动黏度(kinematic_viscosity)二选一提供，
    两者都给或都不给都会返回参数错误。所有输入经强制量纲校验（单位错误返回
    结构化错误并列出可用单位，不猜测）。返回计算书：输入及SI换算、公式及
    溯源状态（待校核）、中间量、结果、判据对照状态（知识库未收录判据时如实
    标注）、告警。
    示例：流量 100 m3/h、内径 300 mm、长度 50 km、粗糙度 0.05 mm、
    密度 850 kg/m3、动力黏度 20 mPa.s。
    """
    try:
        return finalize(hydraulic.pipe_hydraulic(
            flow, flow_unit, inner_diameter, diameter_unit, pipe_length, length_unit,
            roughness, roughness_unit, density, density_unit,
            dynamic_viscosity, viscosity_unit, kinematic_viscosity, kinematic_unit))
    except UnitError as e:
        return _error("量纲校验失败", str(e), "可用 list_dimensions 查询该类别全部可用单位")
    except ValueError as e:
        return _error("参数校验失败", str(e), "请检查参数取值与黏度二选一规则")


@server.tool()
def pipe_temperature_drop(mode: str, mass_flow: float, flow_unit: str,
                          outer_diameter: float, diameter_unit: str,
                          length: float, length_unit: str,
                          total_heat_transfer_coefficient: float, kt_unit: str,
                          environment_temp: float, env_temp_unit: str = "C",
                          inlet_temp: float = None, inlet_temp_unit: str = "C",
                          outlet_temp: float = None, outlet_temp_unit: str = "C",
                          specific_heat: float = None, cp_unit: str = "kJ/(kg.K)") -> str:
    """苏霍夫公式温降计算。mode='drop' 由起点温度算末端温度（提供 inlet_temp）；
    mode='required_inlet' 由末端温度反算所需起点温度（提供 outlet_temp）。
    其余参数：质量流量、管外径、长度、总传热系数 K、环境温度（即周围介质温度）、
    比热容（不提供时用默认 2.0 kJ/(kg·K) 并在计算书中告警）。返回计算书。
    """
    try:
        return finalize(thermal.pipe_temperature_drop(
            mode, mass_flow, flow_unit, outer_diameter, diameter_unit, length, length_unit,
            total_heat_transfer_coefficient, kt_unit, environment_temp, env_temp_unit,
            inlet_temp, inlet_temp_unit, outlet_temp, outlet_temp_unit,
            specific_heat, cp_unit))
    except UnitError as e:
        return _error("量纲校验失败", str(e), "可用 list_dimensions 查询该类别全部可用单位")
    except ValueError as e:
        return _error("参数校验失败", str(e), "检查 mode 取值与 mode 对应的必填温度参数")


@server.tool()
def pipe_wall_thickness(mode: str, design_pressure: float, pressure_unit: str,
                        outer_diameter: float, diameter_unit: str,
                        yield_strength: float, strength_unit: str,
                        design_factor: float,
                        weld_factor: float = 1.0, temperature_derating: float = 1.0,
                        corrosion_allowance: float = 0.0, allowance_unit: str = "mm",
                        nominal_thickness: float = None, thickness_unit: str = "mm") -> str:
    """管道壁厚计算。mode='design' 由设计压力计算所需壁厚；
    mode='check' 由名义壁厚（nominal_thickness）反算最大许用压力并给出强度校核结论。
    design_factor 为设计系数 F（按规范地区等级取值，由 Skill 引导查卡片）；
    weld_factor 焊缝系数；temperature_derating 温度折减系数；corrosion_allowance 腐蚀裕量。
    公式形式对应 GB 50251 系列通用表达，溯源状态为待校核。
    """
    try:
        return finalize(strength.pipe_wall_thickness(
            mode, design_pressure, pressure_unit, outer_diameter, diameter_unit,
            yield_strength, strength_unit, design_factor, weld_factor, temperature_derating,
            corrosion_allowance, allowance_unit, nominal_thickness, thickness_unit))
    except UnitError as e:
        return _error("量纲校验失败", str(e), "可用 list_dimensions 查询该类别全部可用单位")
    except ValueError as e:
        return _error("参数校验失败", str(e), "检查 mode 取值、系数区间与名义壁厚")


@server.tool()
def list_dimensions() -> str:
    """列出引擎支持的全部物理量类别与各单位（供诊断与输入单位自查）。"""
    return json.dumps(list_units(), ensure_ascii=False, indent=2)


def main():
    """stdio 入口。"""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
