import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { PatientEntity } from './patient.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';
import type { PatientVO } from '@cdm/shared';

@Injectable()
export class PatientService {
  constructor(
    @InjectRepository(PatientEntity)
    private readonly repo: Repository<PatientEntity>,
  ) {}

  async findAll(identity: IdentityPayload): Promise<PatientVO[]> {
    const entities = await this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
      },
    });
    return entities.map(PatientService.toVO);
  }

  async createPatient(identity: IdentityPayload, data: { name: string; gender: string }): Promise<PatientVO> {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      name: data.name,
      gender: data.gender,
    });
    const saved = await this.repo.save(entity);
    return PatientService.toVO(saved);
  }

  static toVO(entity: PatientEntity): PatientVO {
    return {
      id: entity.id,
      tenantId: entity.tenantId,
      orgId: entity.orgId,
      name: entity.name,
      gender: entity.gender,
    };
  }
}
