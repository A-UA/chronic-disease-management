import { nextId } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { UserEntity } from './user.entity.js';
import { OrganizationUserEntity } from '../organization/organization-user.entity.js';
import { OrganizationUserRoleEntity } from '../organization/organization-user-role.entity.js';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class UserService {
  constructor(
    @InjectRepository(UserEntity) private readonly repo: Repository<UserEntity>,
    @InjectRepository(OrganizationUserEntity) private readonly orgUserRepo: Repository<OrganizationUserEntity>,
    @InjectRepository(OrganizationUserRoleEntity) private readonly orgUserRoleRepo: Repository<OrganizationUserRoleEntity>
  ) {}

  async list(payload: any) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }

  async create(payload: any) {
    const entity = this.repo.create(payload as any);
    if (!(entity as any).id) { (entity as any).id = String(nextId()); }
    
    if (payload.password) {
      (entity as any).passwordHash = await bcrypt.hash(payload.password, 10);
    }
    
    const savedUser = (await this.repo.save(entity)) as unknown as UserEntity;

    // 绑定组织
    const orgId = payload.org_id || payload.identity?.orgId;
    const tenantId = payload.identity?.tenantId; // Assume current tenant

    if (orgId && tenantId) {
      await this.orgUserRepo.save({
        orgId,
        userId: savedUser.id,
        tenantId,
        userType: 'staff'
      });

      // 分配角色
      if (payload.role_ids && Array.isArray(payload.role_ids)) {
        for (const roleId of payload.role_ids) {
          await this.orgUserRoleRepo.save({
            orgId,
            userId: savedUser.id,
            roleId,
            tenantId
          });
        }
      }
    }

    return savedUser;
  }

  async update(id: string, data: any) {
    if (data.password) {
      data.passwordHash = await bcrypt.hash(data.password, 10);
      delete data.password;
    }
    await this.repo.update(id, data);
    return this.repo.findOne({ where: { id } as any });
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { success: true };
  }
}
