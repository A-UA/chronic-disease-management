import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request } from 'express';
import type { IdentityPayload } from '@cdm/shared';

interface JwtTokenPayload {
  sub: string;
  tenantId: string;
  orgId: string;
  allowedOrgIds?: string[];
  roles?: string[];
}

export interface RequestWithIdentity extends Request {
  identity: IdentityPayload;
}

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private readonly jwtService: JwtService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<RequestWithIdentity>();
    const authHeader = request.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
      throw new UnauthorizedException();
    }

    try {
      const token = authHeader.substring(7);
      const payload = this.jwtService.verify<JwtTokenPayload>(token);
      // 将身份信息注入 request 对象
      request.identity = {
        userId: payload.sub,
        tenantId: payload.tenantId,
        orgId: payload.orgId,
        allowedOrgIds: payload.allowedOrgIds || (payload.orgId ? [payload.orgId] : []),
        roles: payload.roles || [],
      };
      return true;
    } catch {
      throw new UnauthorizedException();
    }
  }
}
