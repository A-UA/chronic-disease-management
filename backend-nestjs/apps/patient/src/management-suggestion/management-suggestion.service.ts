import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { ManagementSuggestionEntity } from './management-suggestion.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';

@Injectable()
export class ManagementSuggestionService {
  constructor(
    @InjectRepository(ManagementSuggestionEntity)
    private readonly repo: Repository<ManagementSuggestionEntity>,
  ) {}

  async findAllForPatient(identity: IdentityPayload, patientId: number) {
    return this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
        patientId,
      },
    });
  }

  async createSuggestion(identity: IdentityPayload, patientId: number, data: { suggestionType: string, content: string }) {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      createdByUserId: identity.userId,
      suggestionType: data.suggestionType,
      content: data.content,
      status: 'active',
      createdAt: new Date(),
    });
    return this.repo.save(entity);
  }
}
