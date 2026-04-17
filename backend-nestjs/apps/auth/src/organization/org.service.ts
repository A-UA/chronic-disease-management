import { nextId } from '@cdm/shared';
import type { ListPayload, CreatePayload, CreateOrgData, UpdateOrgData } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OrganizationEntity } from './organization.entity.js';

@Injectable()
export class OrganizationService {
  constructor(@InjectRepository(OrganizationEntity) private readonly repo: Repository<OrganizationEntity>) {}

  async list(payload: ListPayload) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }

  async create(payload: CreatePayload<CreateOrgData>) {
    const entity = this.repo.create({
      id: nextId(),
      name: payload.data.name,
      code: payload.data.code,
      tenantId: payload.data.tenantId,
      parentId: payload.data.parentId ?? null,
      status: payload.data.status ?? 'active',
    });
    return this.repo.save(entity);
  }

  async update(id: string, data: UpdateOrgData) {
    await this.repo.update(id, data);
    return this.repo.findOneBy({ id });
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { success: true };
  }
}
