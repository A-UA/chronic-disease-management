import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcryptjs';
import { RpcException } from '@nestjs/microservices';
import { UserEntity } from '../user/user.entity.js';
import { OrganizationEntity } from '../organization/organization.entity.js';
import { OrganizationUserEntity } from '../organization/organization-user.entity.js';
import { OrganizationUserRoleEntity } from '../organization/organization-user-role.entity.js';
import { RoleEntity } from '../rbac/role.entity.js';
import { PermissionEntity } from '../rbac/permission.entity.js';
import { JwtProvider } from './jwt.provider.js';
import { MenuService } from '../menu/menu.service.js';
import { IdentityPayload } from '@cdm/shared';

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(UserEntity)
    private readonly userRepo: Repository<UserEntity>,
    @InjectRepository(OrganizationEntity)
    private readonly orgRepo: Repository<OrganizationEntity>,
    @InjectRepository(OrganizationUserEntity)
    private readonly orgUserRepo: Repository<OrganizationUserEntity>,
    @InjectRepository(OrganizationUserRoleEntity)
    private readonly orgUserRoleRepo: Repository<OrganizationUserRoleEntity>,
    @InjectRepository(RoleEntity)
    private readonly roleRepo: Repository<RoleEntity>,
    @InjectRepository(PermissionEntity)
    private readonly permRepo: Repository<PermissionEntity>,
    private readonly jwtProvider: JwtProvider,
    private readonly menuService: MenuService,
  ) {}

  async login(username: string, password: string) {
    const user = await this.userRepo.findOne({ where: { email: username } });
    if (!user || !this.verifyPassword(password, user.passwordHash)) {
      throw new RpcException({ statusCode: 422, message: 'Incorrect email or password' });
    }

    const orgUsers = await this.orgUserRepo.find({ where: { userId: user.id } });
    if (orgUsers.length === 0) {
      throw new RpcException({
        statusCode: 422,
        message: 'User is not a member of any active organization',
      });
    }

    if (orgUsers.length === 1) {
      const ou = orgUsers[0];
      const org = await this.orgRepo.findOneBy({ id: ou.orgId });
      const roleCodes = await this.getRoleCodes(ou.orgId, ou.userId);
      const allowedOrgIds = await this.getDescendingOrgIds(ou.orgId);
      const token = this.jwtProvider.createAccessToken(
        user.id, org.tenantId, org.id, allowedOrgIds, roleCodes,
      );
      return {
        access_token: token,
        token_type: 'bearer',
        organization: { id: org.id, name: org.name, tenant_id: org.tenantId },
        require_org_selection: false,
      };
    }

    // 多部门
    const selectionToken = this.jwtProvider.createSelectionToken(user.id);
    const orgList = await Promise.all(
      orgUsers.map(async (ou) => {
        const org = await this.orgRepo.findOneBy({ id: ou.orgId });
        return { id: org.id, name: org.name, tenant_id: org.tenantId };
      }),
    );

    return {
      access_token: null as string | null,
      token_type: 'bearer',
      organizations: orgList,
      require_org_selection: true,
      selection_token: selectionToken,
    };
  }

  async selectOrg(orgId: number, selectionToken: string) {
    let payload: any;
    try {
      payload = this.jwtProvider.parseToken(selectionToken);
      if (payload.purpose !== 'org_selection') {
        throw new Error();
      }
    } catch {
      throw new RpcException({ statusCode: 422, message: 'Invalid or expired selection token' });
    }

    const userId = Number(payload.sub);
    const ou = await this.orgUserRepo.findOne({ where: { orgId, userId } });
    if (!ou) {
      throw new RpcException({ statusCode: 403, message: 'User is not a member of this organization' });
    }

    const org = await this.orgRepo.findOneBy({ id: orgId });
    const roleCodes = await this.getRoleCodes(orgId, userId);
    const allowedOrgIds = await this.getDescendingOrgIds(orgId);
    const token = this.jwtProvider.createAccessToken(
      userId, org.tenantId, org.id, allowedOrgIds, roleCodes,
    );

    return {
      access_token: token,
      token_type: 'bearer',
      organization: { id: org.id, name: org.name, tenant_id: org.tenantId },
    };
  }

  async switchOrg(identity: IdentityPayload, orgId: number) {
    const ou = await this.orgUserRepo.findOne({
      where: { orgId, userId: identity.userId },
    });
    if (!ou) {
      throw new RpcException({ statusCode: 403, message: 'User is not a member of this organization' });
    }

    const org = await this.orgRepo.findOneBy({ id: orgId });
    const roleCodes = await this.getRoleCodes(orgId, identity.userId);
    const allowedOrgIds = await this.getDescendingOrgIds(orgId);
    const token = this.jwtProvider.createAccessToken(
      identity.userId, org.tenantId, org.id, allowedOrgIds, roleCodes,
    );

    return {
      access_token: token,
      token_type: 'bearer',
      organization: { id: org.id, name: org.name, tenant_id: org.tenantId },
    };
  }

  async listMyOrgs(userId: number) {
    const orgUsers = await this.orgUserRepo.find({ where: { userId } });
    return Promise.all(
      orgUsers.map(async (ou) => {
        const org = await this.orgRepo.findOneBy({ id: ou.orgId });
        return { id: org.id, name: org.name, tenant_id: org.tenantId };
      }),
    );
  }

  async getMe(identity: IdentityPayload) {
    const user = await this.userRepo.findOneBy({ id: identity.userId });
    const perms = await this.getEffectivePermissions(identity.orgId, identity.userId);

    return {
      id: user.id,
      email: user.email,
      name: user.name,
      created_at: user.createdAt,
      tenant_id: identity.tenantId,
      org_id: identity.orgId,
      permissions: [...perms],
    };
  }

  async getMenuTree(identity: IdentityPayload) {
    const perms = await this.getEffectivePermissions(identity.orgId, identity.userId);
    return this.menuService.getMenuTree(identity.tenantId, perms);
  }

  // ── 私有方法 ──

  private async getDescendingOrgIds(rootOrgId: number): Promise<number[]> {
    const queue = [rootOrgId];
    const result = new Set<number>();
    
    while (queue.length > 0) {
      const current = queue.shift();
      if (current && !result.has(current)) {
        result.add(current);
        const children = await this.orgRepo.find({ where: { parentId: current } });
        queue.push(...children.map(c => c.id));
      }
    }
    return Array.from(result);
  }

  private verifyPassword(raw: string, hash: string): boolean {
    if (!hash) return false;
    if (hash.startsWith('$argon2')) return false; // Argon2 暂不支持
    return bcrypt.compareSync(raw, hash);
  }

  private async getRoleCodes(orgId: number, userId: number): Promise<string[]> {
    const ourList = await this.orgUserRoleRepo.find({ where: { orgId, userId } });
    const codes: string[] = [];
    for (const our of ourList) {
      const role = await this.roleRepo.findOneBy({ id: our.roleId });
      if (role) codes.push(role.code);
    }
    return codes;
  }

  private async getEffectivePermissions(orgId: number, userId: number): Promise<Set<string>> {
    const ourList = await this.orgUserRoleRepo.find({ where: { orgId, userId } });
    const roleIds = ourList.map((our) => our.roleId);

    // 展开继承链
    const allRoleIds = new Set(roleIds);
    const queue = [...roleIds];
    while (queue.length > 0) {
      const rid = queue.shift()!;
      const role = await this.roleRepo.findOneBy({ id: rid });
      if (role?.parentRoleId && !allRoleIds.has(role.parentRoleId)) {
        allRoleIds.add(role.parentRoleId);
        queue.push(role.parentRoleId);
      }
    }

    if (allRoleIds.size === 0) return new Set();

    // 查询所有角色的权限码
    const roles = await this.roleRepo.find({
      where: [...allRoleIds].map((id) => ({ id })),
      relations: ['permissions'],
    });

    const permCodes = new Set<string>();
    for (const role of roles) {
      for (const perm of role.permissions || []) {
        permCodes.add(perm.code);
      }
    }
    return permCodes;
  }
}
