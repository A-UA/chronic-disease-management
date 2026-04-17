import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { ManagementSuggestionEntity } from './management-suggestion.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';
import type { ManagementSuggestionVO } from '@cdm/shared';

@Injectable()
export class ManagementSuggestionService {
  constructor(
    @InjectRepository(ManagementSuggestionEntity)
    private readonly repo: Repository<ManagementSuggestionEntity>,
  ) {}

  async findAllForPatient(identity: IdentityPayload, patientId: string): Promise<ManagementSuggestionVO[]> {
    const entities = await this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
        patientId,
      },
    });
    return entities.map(ManagementSuggestionService.toVO);
  }

  async createSuggestion(identity: IdentityPayload, patientId: string, data: { suggestionType: string, content: string }): Promise<ManagementSuggestionVO> {
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
    const saved = await this.repo.save(entity);
    return ManagementSuggestionService.toVO(saved);
  }

  static toVO(entity: ManagementSuggestionEntity): ManagementSuggestionVO {
    return {
      id: entity.id,
      patientId: entity.patientId,
      createdByUserId: entity.createdByUserId,
      suggestionType: entity.suggestionType,
      content: entity.content,
      status: entity.status,
      createdAt: entity.createdAt,
    };
  }
}
