---
name: blood-pressure-analysis
description: 分析患者血压数据趋势，识别异常波动并给出慢病管理建议。当用户需要分析血压数据、评估高血压风险或获取血压管理建议时使用。
license: Apache-2.0
compatibility: 慢病管理 AI SaaS 平台
metadata:
  author: cdm-team
  version: "1.0"
  required-permission: patient:read
  parameters:
    blood-pressure-data:
      type: string
      description: 患者血压数据（JSON 格式，包含日期和收缩压/舒张压）
      required: true
    patient-age:
      type: integer
      description: 患者年龄
---

# 血压趋势分析

## 使用场景
当用户提供血压数据并希望了解趋势、异常和管理建议时，使用此技能。

## 分析步骤

1. **数据解读**：解析血压数据，识别收缩压和舒张压
2. **趋势识别**：分析整体趋势（上升/下降/平稳）
3. **异常检测**：标记收缩压 ≥140 或 ≤90，舒张压 ≥90 或 ≤60 的异常值
4. **波动评估**：评估血压波动性（低/中/高）
5. **风险评级**：综合评估为低危/中危/高危

## 输出格式

### 📊 趋势概要
- 数据周期、平均值、趋势方向

### ⚠️ 异常记录
- 列出所有超标数据点

### 📋 管理建议
- 基于分析结果给出 2-3 条具体建议
- 如有必要，建议就医或调整用药

### 🏷️ 风险等级
- 明确标注低危/中危/高危

## 注意事项
- 此分析仅供参考，不构成医疗诊断
- 严重异常应建议患者及时就医
