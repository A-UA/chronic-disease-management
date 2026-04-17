import { nextId } from '@cdm/shared';
import type {
  ListPayload,
  CreatePayload,
  CreateUserData,
  UpdateUserData,
  PaginatedResult,
  UserVO,
  SuccessVO,
} from '@cdm/shared';
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

  async list(payload: ListPayload): Promise<PaginatedResult<UserVO>> {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [entities, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items: entities.map(UserService.toVO), total };
  }

  async create(payload: CreatePayload<CreateUserData>): Promise<UserVO> {
    const { data, identity } = payload;
    const entity = this.repo.create({
      id: nextId(),
      email: data.email,
      name: data.name ?? '',
    });

    if (data.password) {
      entity.passwordHash = await bcrypt.hash(data.password, 10);
    }

    const savedUser = await this.repo.save(entity);

    // 绑定组织
    const orgId = data.org_id || identity.orgId;
    const tenantId = identity.tenantId;

    if (orgId && tenantId) {
      await this.orgUserRepo.save({
        orgId,
        userId: savedUser.id,
        tenantId,
        userType: 'staff'
      });

      // 分配角色
      if (data.role_ids && Array.isArray(data.role_ids)) {
        for (const roleId of data.role_ids) {
          await this.orgUserRoleRepo.save({
            orgId,
            userId: savedUser.id,
            roleId,
            tenantId
          });
        }
      }
    }

    return UserService.toVO(savedUser);
  }

  async update(id: string, data: UpdateUserData): Promise<UserVO | null> {
    const updateData: Partial<UserEntity> = {};
    if (data.email !== undefined) updateData.email = data.email;
    if (data.name !== undefined) updateData.name = data.name;
    if (data.password) {
      updateData.passwordHash = await bcrypt.hash(data.password, 10);
    }
    await this.repo.update(id, updateData);
    const updated = await this.repo.findOneBy({ id });
    return updated ? UserService.toVO(updated) : null;
  }

  async delete(id: string): Promise<SuccessVO> {
    await this.repo.delete(id);
    return { success: true };
  }

  /** Entity → VO 转换（脱敏 passwordHash） */
  static toVO(entity: UserEntity): UserVO {
    return {
      id: entity.id,
      email: entity.email,
      name: entity.name,
      createdAt: entity.createdAt,
      updatedAt: entity.updatedAt,
    };
  }
}
