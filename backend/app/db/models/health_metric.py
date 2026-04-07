"""健康指标数据模型：支持血压/血糖/体重/心率/BMI 等结构化指标录入"""
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IDMixin, TimestampMixin


class HealthMetric(Base, IDMixin, TimestampMixin):
    __tablename__ = "health_metrics"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True,
    )
    recorded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True,
    )

    # 指标类型：blood_pressure, blood_sugar, weight, heart_rate, bmi, spo2
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 主要数值（收缩压、空腹血糖、体重等）
    value: Mapped[float] = mapped_column(Float, nullable=False)
    # 次要数值（舒张压等，可选）
    value_secondary: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 单位
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    # 实际测量时间
    measured_at: Mapped[datetime] = mapped_column(nullable=False)
    # 备注（如"餐后2小时"、"晨起空腹"）
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_patient_metric_time", "patient_id", "metric_type", "measured_at"),
        Index("idx_health_metrics_tenant_org", "tenant_id", "org_id", "patient_id"),
    )
