import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request } from 'express';

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private readonly jwtService: JwtService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const authHeader = request.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
      throw new UnauthorizedException();
    }

    try {
      const token = authHeader.substring(7);
      const payload = this.jwtService.verify(token);
      // 将身份信息注入 request 对象
      (request as any).identity = {
        userId: String(payload.sub),
        tenantId: String(payload.tenant_id),
        orgId: String(payload.org_id),
        allowedOrgIds: payload.allowed_org_ids || (payload.org_id ? [String(payload.org_id)] : []),
        roles: payload.roles || [],
      };
      return true;
    } catch {
      throw new UnauthorizedException();
    }
  }
}
