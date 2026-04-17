import { nextId } from '@cdm/shared';
import type { ListPayload, CreatePayload, CreatePermissionData, UpdatePermissionData } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PermissionEntity } from './permission.entity.js';

@Injectable()
export class PermissionService {
  constructor(@InjectRepository(PermissionEntity) private readonly repo: Repository<PermissionEntity>) {}

  async list(payload: ListPayload) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }

  async create(payload: CreatePayload<CreatePermissionData>) {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      code: payload.data.code,
      resourceId: payload.data.resourceId,
      actionId: payload.data.actionId,
    });
    return this.repo.save(entity);
  }

  async update(id: string, data: UpdatePermissionData) {
    await this.repo.update(id, data);
    return this.repo.findOneBy({ id });
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { success: true };
  }
}
