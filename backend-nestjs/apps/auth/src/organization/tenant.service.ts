import { nextId } from '@cdm/shared';
import type { ListPayload, CreatePayload, CreateTenantData, UpdateTenantData } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { TenantEntity } from './tenant.entity.js';

@Injectable()
export class TenantService {
  constructor(@InjectRepository(TenantEntity) private readonly repo: Repository<TenantEntity>) {}

  async list(payload: ListPayload) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }

  async create(payload: CreatePayload<CreateTenantData>) {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      slug: payload.data.slug,
      planType: payload.data.planType ?? 'free',
    });
    return this.repo.save(entity);
  }

  async update(id: string, data: UpdateTenantData) {
    await this.repo.update(id, data);
    return this.repo.findOneBy({ id });
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { success: true };
  }
}
