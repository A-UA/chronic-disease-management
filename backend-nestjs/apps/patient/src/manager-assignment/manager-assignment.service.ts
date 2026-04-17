import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { ManagerAssignmentEntity } from './manager-assignment.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';

@Injectable()
export class ManagerAssignmentService {
  constructor(
    @InjectRepository(ManagerAssignmentEntity)
    private readonly repo: Repository<ManagerAssignmentEntity>,
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

  async assignManager(identity: IdentityPayload, patientId: string, data: { managerUserId: string, assignmentType: string }) {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      managerUserId: data.managerUserId,
      assignmentType: data.assignmentType,
      createdAt: new Date(),
    });
    return this.repo.save(entity);
  }
}
