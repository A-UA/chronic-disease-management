import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { ManagerAssignmentEntity } from './manager-assignment.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';
import type { ManagerAssignmentVO } from '@cdm/shared';

@Injectable()
export class ManagerAssignmentService {
  constructor(
    @InjectRepository(ManagerAssignmentEntity)
    private readonly repo: Repository<ManagerAssignmentEntity>,
  ) {}

  async findAllForPatient(identity: IdentityPayload, patientId: string): Promise<ManagerAssignmentVO[]> {
    const entities = await this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
        patientId,
      },
    });
    return entities.map(ManagerAssignmentService.toVO);
  }

  async assignManager(identity: IdentityPayload, patientId: string, data: { managerUserId: string, assignmentType: string }): Promise<ManagerAssignmentVO> {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      managerUserId: data.managerUserId,
      assignmentType: data.assignmentType,
      createdAt: new Date(),
    });
    const saved = await this.repo.save(entity);
    return ManagerAssignmentService.toVO(saved);
  }

  static toVO(entity: ManagerAssignmentEntity): ManagerAssignmentVO {
    return {
      id: entity.id,
      patientId: entity.patientId,
      managerUserId: entity.managerUserId,
      assignmentType: entity.assignmentType,
      createdAt: entity.createdAt,
    };
  }
}
