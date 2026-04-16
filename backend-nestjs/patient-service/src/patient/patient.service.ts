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
}
