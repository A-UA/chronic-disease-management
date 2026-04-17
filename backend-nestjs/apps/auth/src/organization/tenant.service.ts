import { nextId } from '@cdm/shared';
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { TenantEntity } from './tenant.entity.js';

@Injectable()
export class TenantService {
  constructor(@InjectRepository(TenantEntity) private readonly repo: Repository<TenantEntity>) {}
  async list(payload: any) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }
  async create(payload: any) {
    const entity = this.repo.create(payload as any);
    if (!(entity as any).id) { (entity as any).id = String(nextId()); }
    return this.repo.save(entity);
  }
  async update(id: string, data: any) {
    await this.repo.update(id, data);
    return this.repo.findOne({ where: { id } as any });
  }
  async delete(id: string) {
    await this.repo.delete(id);
    return { success: true };
  }
}
