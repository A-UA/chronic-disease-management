"""健康指标异常告警服务

定义各指标类型的正常范围阈值，在录入时自动检测并生成告警。
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AlertThreshold:
    """单个指标的告警阈值"""
    metric_type: str
    low: float | None = None      # 低于此值告警
    high: float | None = None     # 高于此值告警
    high_secondary: float | None = None  # 第二值高阈值（如舒张压）
    low_secondary: float | None = None   # 第二值低阈值
    unit: str = ""
    description: str = ""


# 各指标的告警阈值定义
THRESHOLDS: dict[str, AlertThreshold] = {
    "blood_pressure": AlertThreshold(
        metric_type="blood_pressure",
        low=90, high=140,           # 收缩压
        low_secondary=60, high_secondary=90,  # 舒张压
        unit="mmHg",
        description="血压",
    ),
    "blood_sugar": AlertThreshold(
        metric_type="blood_sugar",
        low=3.9, high=11.1,         # 空腹 3.9-6.1，餐后上限 11.1
        unit="mmol/L",
        description="血糖",
    ),
    "heart_rate": AlertThreshold(
        metric_type="heart_rate",
        low=60, high=100,
        unit="bpm",
        description="心率",
    ),
    "spo2": AlertThreshold(
        metric_type="spo2",
        low=95, high=None,          # 低于 95% 告警
        unit="%",
        description="血氧饱和度",
    ),
    "bmi": AlertThreshold(
        metric_type="bmi",
        low=18.5, high=28.0,        # 中国标准：<18.5 偏瘦, >28 肥胖
        unit="kg/m²",
        description="BMI",
    ),
}


@dataclass
class HealthAlert:
    """健康指标告警结果"""
    metric_type: str
    level: str              # "warning" | "danger"
    message: str
    value: float
    threshold: float
    unit: str


def check_metric_alert(
    metric_type: str,
    value: float,
    value_secondary: float | None = None,
) -> list[HealthAlert]:
    """检测单次指标录入是否触发告警

    返回告警列表（可能为空）
    """
    threshold = THRESHOLDS.get(metric_type)
    if not threshold:
        return []

    alerts: list[HealthAlert] = []

    # 主值检测
    if threshold.high is not None and value > threshold.high:
        level = "danger" if value > threshold.high * 1.2 else "warning"
        alerts.append(HealthAlert(
            metric_type=metric_type,
            level=level,
            message=f"{threshold.description}偏高：{value} {threshold.unit}（正常上限 {threshold.high}）",
            value=value,
            threshold=threshold.high,
            unit=threshold.unit,
        ))

    if threshold.low is not None and value < threshold.low:
        level = "danger" if value < threshold.low * 0.8 else "warning"
        alerts.append(HealthAlert(
            metric_type=metric_type,
            level=level,
            message=f"{threshold.description}偏低：{value} {threshold.unit}（正常下限 {threshold.low}）",
            value=value,
            threshold=threshold.low,
            unit=threshold.unit,
        ))

    # 第二值检测（如血压舒张压）
    if value_secondary is not None:
        if threshold.high_secondary is not None and value_secondary > threshold.high_secondary:
            level = "danger" if value_secondary > threshold.high_secondary * 1.2 else "warning"
            alerts.append(HealthAlert(
                metric_type=metric_type,
                level=level,
                message=f"{threshold.description}（舒张压）偏高：{value_secondary} {threshold.unit}（正常上限 {threshold.high_secondary}）",
                value=value_secondary,
                threshold=threshold.high_secondary,
                unit=threshold.unit,
            ))
        if threshold.low_secondary is not None and value_secondary < threshold.low_secondary:
            level = "danger" if value_secondary < threshold.low_secondary * 0.8 else "warning"
            alerts.append(HealthAlert(
                metric_type=metric_type,
                level=level,
                message=f"{threshold.description}（舒张压）偏低：{value_secondary} {threshold.unit}（正常下限 {threshold.low_secondary}）",
                value=value_secondary,
                threshold=threshold.low_secondary,
                unit=threshold.unit,
            ))

    return alerts
