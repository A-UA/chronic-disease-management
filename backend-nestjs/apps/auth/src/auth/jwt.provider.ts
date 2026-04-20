import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

interface JwtPayloadData {
  sub: string;
  tenantId: string;
  orgId: string;
  allowedOrgIds: string[];
  roles: string[];
}

interface SelectionTokenPayload {
  sub: string;
  purpose: string;
}

@Injectable()
export class JwtProvider {
  constructor(private readonly jwtService: JwtService) {}

  createAccessToken(
    userId: string,
    tenantId: string,
    orgId: string,
    allowedOrgIds: string[],
    roles: string[],
  ): string {
    const payload: JwtPayloadData = {
      sub: userId,
      tenantId: tenantId,
      orgId: orgId,
      allowedOrgIds: allowedOrgIds,
      roles,
    };
    return this.jwtService.sign(payload);
  }

  createSelectionToken(userId: string): string {
    return this.jwtService.sign(
      { sub: userId, purpose: 'org_selection' },
      { expiresIn: '5m' },
    );
  }

  parseToken(token: string): SelectionTokenPayload {
    return this.jwtService.verify<SelectionTokenPayload>(token);
  }
}
