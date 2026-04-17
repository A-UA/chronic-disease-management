import { nextId } from '@cdm/shared';
import type {
  ListPayload,
  CreatePayload,
  CreatePermissionData,
  UpdatePermissionData,
  PaginatedResult,
  PermissionVO,
  SuccessVO,
} from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PermissionEntity } from './permission.entity.js';

@Injectable()
export class PermissionService {
  constructor(@InjectRepository(PermissionEntity) private readonly repo: Repository<PermissionEntity>) {}

  async list(payload: ListPayload): Promise<PaginatedResult<PermissionVO>> {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [entities, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items: entities.map(PermissionService.toVO), total };
  }

  async create(payload: CreatePayload<CreatePermissionData>): Promise<PermissionVO> {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      code: payload.data.code,
      resourceId: payload.data.resourceId,
      actionId: payload.data.actionId,
    });
    const saved = await this.repo.save(entity);
    return PermissionService.toVO(saved);
  }

  async update(id: string, data: UpdatePermissionData): Promise<PermissionVO | null> {
    await this.repo.update(id, data);
    const updated = await this.repo.findOneBy({ id });
    return updated ? PermissionService.toVO(updated) : null;
  }

  async delete(id: string): Promise<SuccessVO> {
    await this.repo.delete(id);
    return { success: true };
  }

  static toVO(entity: PermissionEntity): PermissionVO {
    return {
      id: entity.id,
      name: entity.name,
      code: entity.code,
      resourceId: entity.resourceId,
      actionId: entity.actionId,
    };
  }
}
