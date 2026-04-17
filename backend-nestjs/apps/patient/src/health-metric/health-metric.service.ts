import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { HealthMetricEntity } from './health-metric.entity.js';
import { IdentityPayload, nextId } from '@cdm/shared';
import type { HealthMetricVO } from '@cdm/shared';

@Injectable()
export class HealthMetricService {
  constructor(
    @InjectRepository(HealthMetricEntity)
    private readonly repo: Repository<HealthMetricEntity>,
  ) {}

  async findAllForPatient(identity: IdentityPayload, patientId: string): Promise<HealthMetricVO[]> {
    const entities = await this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
        patientId,
      },
    });
    return entities.map(HealthMetricService.toVO);
  }

  async create(identity: IdentityPayload, patientId: string, data: { metricType: string, metricValue: string }): Promise<HealthMetricVO> {
    const entity = this.repo.create({
      id: nextId(),
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      metricType: data.metricType,
      metricValue: data.metricValue,
      recordedAt: new Date(),
    });
    const saved = await this.repo.save(entity);
    return HealthMetricService.toVO(saved);
  }

  static toVO(entity: HealthMetricEntity): HealthMetricVO {
    return {
      id: entity.id,
      patientId: entity.patientId,
      metricType: entity.metricType,
      metricValue: entity.metricValue,
      recordedAt: entity.recordedAt,
    };
  }
}
