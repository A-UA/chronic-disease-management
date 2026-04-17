import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

/**
 * 将对象中可能存在的 bigint 或超出安全整数范围的数字转为字符串
 * 解决前端 JavaScript Number(>2^53) 精度丢失问题
 */
@Injectable()
export class BigIntSerializerInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map(data => {
        if (!data) return data;
        return JSON.parse(
          JSON.stringify(data, (_, v) => {
            if (typeof v === 'bigint') {
              return v.toString();
            }
            // 同时兼容处理字符串形式但本质是 bigint 的可能情况（pg 驱动默认把 bigint 转为 string 返回）
            // 在这一步其实不需要对字符串再做处理，只需处理原生 bigint 即可防患于未然
            return v;
          })
        );
      })
    );
  }
}
