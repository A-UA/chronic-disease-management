import { nextId } from '@cdm/shared';
import type {
  ListPayload,
  CreatePayload,
  CreateTenantData,
  UpdateTenantData,
  PaginatedResult,
  TenantVO,
  SuccessVO,
} from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { TenantEntity } from './tenant.entity.js';

@Injectable()
export class TenantService {
  constructor(@InjectRepository(TenantEntity) private readonly repo: Repository<TenantEntity>) {}

  async list(payload: ListPayload): Promise<PaginatedResult<TenantVO>> {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [entities, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items: entities.map(TenantService.toVO), total };
  }

  async create(payload: CreatePayload<CreateTenantData>): Promise<TenantVO> {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      slug: payload.data.slug,
      planType: payload.data.planType ?? 'free',
    });
    const saved = await this.repo.save(entity);
    return TenantService.toVO(saved);
  }

  async update(id: string, data: UpdateTenantData): Promise<TenantVO | null> {
    await this.repo.update(id, data);
    const updated = await this.repo.findOneBy({ id });
    return updated ? TenantService.toVO(updated) : null;
  }

  async delete(id: string): Promise<SuccessVO> {
    await this.repo.delete(id);
    return { success: true };
  }

  static toVO(entity: TenantEntity): TenantVO {
    return {
      id: entity.id,
      name: entity.name,
      slug: entity.slug,
      planType: entity.planType,
      createdAt: entity.createdAt,
    };
  }
}
