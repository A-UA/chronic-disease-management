import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { PatientFamilyLinkEntity } from './patient-family-link.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';
import type { PatientFamilyLinkVO } from '@cdm/shared';

@Injectable()
export class PatientFamilyLinkService {
  constructor(
    @InjectRepository(PatientFamilyLinkEntity)
    private readonly repo: Repository<PatientFamilyLinkEntity>,
  ) {}

  async findAllForPatient(identity: IdentityPayload, patientId: string): Promise<PatientFamilyLinkVO[]> {
    const entities = await this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
        patientId,
      },
    });
    return entities.map(PatientFamilyLinkService.toVO);
  }

  async linkFamily(identity: IdentityPayload, patientId: string, data: { familyUserId: string, relationship: string }): Promise<PatientFamilyLinkVO> {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      familyUserId: data.familyUserId,
      relationship: data.relationship,
      createdAt: new Date(),
    });
    const saved = await this.repo.save(entity);
    return PatientFamilyLinkService.toVO(saved);
  }

  static toVO(entity: PatientFamilyLinkEntity): PatientFamilyLinkVO {
    return {
      id: entity.id,
      patientId: entity.patientId,
      familyUserId: entity.familyUserId,
      relationship: entity.relationship,
      createdAt: entity.createdAt,
    };
  }
}
