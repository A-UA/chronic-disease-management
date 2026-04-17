import { nextId } from '@cdm/shared';
import type { ListPayload, CreatePayload, CreateRoleData, UpdateRoleData } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { RoleEntity } from './role.entity.js';

@Injectable()
export class RoleService {
  constructor(@InjectRepository(RoleEntity) private readonly repo: Repository<RoleEntity>) {}

  async list(payload: ListPayload) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }

  async create(payload: CreatePayload<CreateRoleData>) {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      code: payload.data.code,
      tenantId: payload.data.tenantId ?? null,
      parentRoleId: payload.data.parentRoleId ?? null,
      isSystem: payload.data.isSystem ?? false,
    });
    return this.repo.save(entity);
  }

  async update(id: string, data: UpdateRoleData) {
    await this.repo.update(id, data);
    return this.repo.findOneBy({ id });
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { success: true };
  }
}
