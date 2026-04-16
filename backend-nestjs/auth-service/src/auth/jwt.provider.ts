import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class JwtProvider {
  constructor(private readonly jwtService: JwtService) {}

  createAccessToken(
    userId: number,
    tenantId: number,
    orgId: number,
    allowedOrgIds: number[],
    roles: string[],
  ): string {
    return this.jwtService.sign({
      sub: String(userId),
      tenant_id: String(tenantId),
      org_id: String(orgId),
      allowed_org_ids: allowedOrgIds,
      roles,
    });
  }

  createSelectionToken(userId: number): string {
    return this.jwtService.sign(
      { sub: String(userId), purpose: 'org_selection' },
      { expiresIn: '5m' },
    );
  }

  parseToken(token: string): any {
    return this.jwtService.verify(token);
  }
}
