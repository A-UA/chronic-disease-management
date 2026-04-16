import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { PatientEntity } from './patient.entity';
import { IdentityPayload } from '@cdm/shared';

@Injectable()
export class PatientService {
  constructor(
    @InjectRepository(PatientEntity)
    private readonly repo: Repository<PatientEntity>,
  ) {}

  async findAll(identity: IdentityPayload) {
    return this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
      },
    });
  }

  async createPatient(identity: IdentityPayload, data: { name: string; gender: string }) {
    const entity = this.repo.create({
      id: Date.now(), // Generate properly in prod
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      name: data.name,
      gender: data.gender,
    });
    return this.repo.save(entity);
  }
}
