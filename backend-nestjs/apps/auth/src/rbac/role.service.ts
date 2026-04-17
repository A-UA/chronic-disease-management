import { nextId } from '@cdm/shared';
import type {
  ListPayload,
  CreatePayload,
  CreateRoleData,
  UpdateRoleData,
  PaginatedResult,
  RoleVO,
  SuccessVO,
} from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { RoleEntity } from './role.entity.js';

@Injectable()
export class RoleService {
  constructor(@InjectRepository(RoleEntity) private readonly repo: Repository<RoleEntity>) {}

  async list(payload: ListPayload): Promise<PaginatedResult<RoleVO>> {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [entities, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items: entities.map(RoleService.toVO), total };
  }

  async create(payload: CreatePayload<CreateRoleData>): Promise<RoleVO> {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      code: payload.data.code,
      tenantId: payload.data.tenantId ?? null,
      parentRoleId: payload.data.parentRoleId ?? null,
      isSystem: payload.data.isSystem ?? false,
    });
    const saved = await this.repo.save(entity);
    return RoleService.toVO(saved);
  }

  async update(id: string, data: UpdateRoleData): Promise<RoleVO | null> {
    await this.repo.update(id, data);
    const updated = await this.repo.findOneBy({ id });
    return updated ? RoleService.toVO(updated) : null;
  }

  async delete(id: string): Promise<SuccessVO> {
    await this.repo.delete(id);
    return { success: true };
  }

  static toVO(entity: RoleEntity): RoleVO {
    return {
      id: entity.id,
      tenantId: entity.tenantId,
      parentRoleId: entity.parentRoleId,
      name: entity.name,
      code: entity.code,
      isSystem: entity.isSystem,
      createdAt: entity.createdAt,
      updatedAt: entity.updatedAt,
    };
  }
}
