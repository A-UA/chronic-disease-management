---
name: medication-reminder
description: 根据患者用药方案生成个性化服药提醒内容。当需要为患者创建服药提醒、整理用药计划或生成用药指导时使用。
license: Apache-2.0
metadata:
  author: cdm-team
  version: "1.0"
  parameters:
    medication-list:
      type: string
      description: 药物列表（名称+剂量+频次）
      required: true
    patient-name:
      type: string
      description: 患者姓名
---

# 服药提醒生成器

## 使用场景
当管理师需要为患者生成清晰易懂的服药提醒时使用此技能。

## 提醒规则

1. 按服药时间分组（早/中/晚/睡前）
2. 标注空腹/餐后要求
3. 提醒药物相互作用注意事项
4. 使用通俗语言，避免专业术语
5. 加入鼓励性语句

## 输出格式

生成一条适合发送给患者的短消息（200 字以内），包含：
- 今日需服用的药物和时间
- 服用注意事项
- 简短鼓励

## 示例输出

> 张阿姨您好！今日用药提醒：
> 🌅 早餐后：二甲双胍 0.5g
> 🌙 睡前：厄贝沙坦 150mg
> ⚠️ 二甲双胍请随餐服用，避免空腹
> 💪 坚持用药，您的健康在进步！
