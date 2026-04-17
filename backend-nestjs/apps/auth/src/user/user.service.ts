import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { UserEntity } from './user.entity.js';

@Injectable()
export class UserService {
  constructor(@InjectRepository(UserEntity) private readonly repo: Repository<UserEntity>) {}
  async list(payload: any) {
    const skip = Number(payload.skip) || 0;
    const limit = Number(payload.limit) || 50;
    const [items, total] = await this.repo.findAndCount({ skip, take: limit });
    return { items, total };
  }
  async create(payload: any) {
    const entity = this.repo.create(payload as any);
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
