# -*- coding: utf-8 -*-
"""单位换算与量纲校验模块（闸门三：量纲防御）。

设计原则：
- 引擎内部一律使用 SI 单位计算；
- 每个输入参数声明物理量类别（dimension），输入单位不属于该类别时直接报错，
  绝不猜测、绝不静默换算；
- 换算关系为确定性常量，不涉及拟合或经验数据。
"""

# 单位换算表：dimension -> {unit: factor_to_SI}（SI 基准单位在表末注明）
UNIT_TABLES = {
    "length": {  # SI: m
        "m": 1.0, "mm": 0.001, "cm": 0.01, "km": 1000.0, "ft": 0.3048, "in": 0.0254,
    },
    "pressure": {  # SI: Pa
        "Pa": 1.0, "kPa": 1e3, "MPa": 1e6, "bar": 1e5, "atm": 101325.0,
        "psi": 6894.757293168, "kgf/cm2": 98066.5,
    },
    "flow_volume": {  # SI: m3/s
        "m3/s": 1.0, "m3/h": 1.0 / 3600.0, "m3/d": 1.0 / 86400.0, "L/s": 0.001, "L/min": 0.001 / 60.0,
    },
    "flow_mass": {  # SI: kg/s
        "kg/s": 1.0, "kg/h": 1.0 / 3600.0, "t/h": 1000.0 / 3600.0, "t/d": 1000.0 / 86400.0,
    },
    "density": {  # SI: kg/m3
        "kg/m3": 1.0, "g/cm3": 1000.0, "t/m3": 1000.0, "kg/L": 1000.0,
    },
    "viscosity_dynamic": {  # SI: Pa.s
        "Pa.s": 1.0, "mPa.s": 0.001, "cP": 0.001, "mPa·s": 0.001,
    },
    "viscosity_kinematic": {  # SI: m2/s
        "m2/s": 1.0, "mm2/s": 1e-6, "cSt": 1e-6, "m2/h": 1.0 / 3600.0,
    },
    "temperature": {  # 特殊处理：摄氏/开尔文偏移换算，SI: K
        "C": "special", "K": "special",
    },
    "roughness": {  # SI: m（绝对粗糙度）
        "m": 1.0, "mm": 0.001, "um": 1e-6,
    },
    "thermal_conductance": {  # SI: W/(m2.K)（总传热系数 K）
        "W/(m2.K)": 1.0, "W/(m2*C)": 1.0,
    },
    "specific_heat": {  # SI: J/(kg.K)
        "J/(kg.K)": 1.0, "kJ/(kg.K)": 1000.0, "kJ/(kg*C)": 1000.0,
    },
    "stress": {  # SI: Pa（屈服强度等）
        "Pa": 1.0, "kPa": 1e3, "MPa": 1e6,
    },
    "velocity": {  # SI: m/s
        "m/s": 1.0, "m/h": 1.0 / 3600.0,
    },
    "dimensionless": {  # 无量纲
        "-": 1.0, "": 1.0,
    },
}


class UnitError(Exception):
    """量纲校验失败：单位不属于声明的物理量类别，或单位未知。"""


def convert_to_si(value, unit, dimension):
    """将 value 从 unit 换算为 SI 单位，并完成量纲校验。

    - 温度类别做偏移换算（℃→K）；
    - 其他类别按线性因子换算；
    - 单位不在类别的换算表内 → 抛 UnitError（含可用单位列表）。
    返回 (si_value, si_unit)。
    """
    if dimension not in UNIT_TABLES:
        raise UnitError(
            "未定义的物理量类别: %r（引擎支持: %s）" % (dimension, ", ".join(sorted(UNIT_TABLES)))
        )
    table = UNIT_TABLES[dimension]

    if dimension == "temperature":
        if unit in ("C", "degC"):
            return float(value) + 273.15, "K"
        if unit == "K":
            return float(value), "K"
        raise UnitError("温度单位 %r 不受支持（可用: C, K）" % unit)

    if unit not in table:
        raise UnitError(
            "单位 %r 不属于物理量类别 %r（该类别可用单位: %s）"
            % (unit, dimension, ", ".join(sorted(k for k in table if k)))
        )
    return float(value) * table[unit], _si_unit_of(dimension)


def _si_unit_of(dimension):
    si_map = {
        "length": "m", "pressure": "Pa", "flow_volume": "m3/s", "flow_mass": "kg/s",
        "density": "kg/m3", "viscosity_dynamic": "Pa.s", "viscosity_kinematic": "m2/s",
        "temperature": "K", "roughness": "m", "thermal_conductance": "W/(m2.K)",
        "specific_heat": "J/(kg.K)", "stress": "Pa", "velocity": "m/s", "dimensionless": "-",
    }
    return si_map.get(dimension, "?")


def list_units(dimension=None):
    """列出可用物理量类别及其单位（供诊断与自检）。"""
    if dimension:
        table = UNIT_TABLES.get(dimension)
        if table is None:
            raise UnitError("未定义的物理量类别: %r" % dimension)
        return {dimension: sorted(k for k in table if k)}
    return {d: sorted(k for k in t if k) for d, t in UNIT_TABLES.items()}
