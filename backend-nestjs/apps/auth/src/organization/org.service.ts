import { nextId } from '@cdm/shared';
import type {
  ListPayload,
  CreatePayload,
  CreateOrgData,
  UpdateOrgData,
  PaginatedResult,
  OrganizationVO,
  SuccessVO,
} from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OrganizationEntity } from './organization.entity.js';

@Injectable()
export class OrganizationService {
  constructor(@InjectRepository(OrganizationEntity) private readonly repo: Repository<OrganizationEntity>) {}

  async list(payload: ListPayload): Promise<PaginatedResult<OrganizationVO>> {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [entities, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items: entities.map(OrganizationService.toVO), total };
  }

  async create(payload: CreatePayload<CreateOrgData>): Promise<OrganizationVO> {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      code: payload.data.code,
      tenantId: payload.data.tenantId,
      parentId: payload.data.parentId ?? null,
      status: payload.data.status ?? 'active',
    });
    const saved = await this.repo.save(entity);
    return OrganizationService.toVO(saved);
  }

  async update(id: string, data: UpdateOrgData): Promise<OrganizationVO | null> {
    await this.repo.update(id, data);
    const updated = await this.repo.findOneBy({ id });
    return updated ? OrganizationService.toVO(updated) : null;
  }

  async delete(id: string): Promise<SuccessVO> {
    await this.repo.delete(id);
    return { success: true };
  }

  static toVO(entity: OrganizationEntity): OrganizationVO {
    return {
      id: entity.id,
      tenantId: entity.tenantId,
      parentId: entity.parentId,
      name: entity.name,
      code: entity.code,
      status: entity.status,
      createdAt: entity.createdAt,
      updatedAt: entity.updatedAt,
    };
  }
}
