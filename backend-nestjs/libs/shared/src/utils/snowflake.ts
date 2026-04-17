import { Snowflake } from '@sapphire/snowflake';

/**
 * 项目统一雪花 ID 生成器
 * 纪元: 1288834974657n (2010-11-04 09:42:54.657Z)
 * 与 Java 端 Hutool 默认纪元保持绝对一致，保证生成的 ID 长度和量级相同（19位数字）
 */
const CDM_EPOCH = 1288834974657n;
const snowflake = new Snowflake(CDM_EPOCH);

/**
 * 生成一个全局唯一的雪花 ID
 * 返回字符串形式以避免 JS 精度丢失，并在类型上兼容 TypeORM bigint Entity 定义
 */
export function nextId(): string {
  return snowflake.generate().toString();
}

/**
 * 将 bigint 格式的 ID 转为字符串（用于 API 响应序列化）
 */
export function idToString(id: string | number | bigint): string {
  return String(id);
}
