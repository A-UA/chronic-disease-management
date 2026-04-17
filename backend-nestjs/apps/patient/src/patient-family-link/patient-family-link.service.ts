import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { PatientFamilyLinkEntity } from './patient-family-link.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';

@Injectable()
export class PatientFamilyLinkService {
  constructor(
    @InjectRepository(PatientFamilyLinkEntity)
    private readonly repo: Repository<PatientFamilyLinkEntity>,
  ) {}

  async findAllForPatient(identity: IdentityPayload, patientId: string) {
    return this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
        patientId,
      },
    });
  }

  async linkFamily(identity: IdentityPayload, patientId: string, data: { familyUserId: string, relationship: string }) {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      familyUserId: data.familyUserId,
      relationship: data.relationship,
      createdAt: new Date(),
    });
    return this.repo.save(entity);
  }
}
