import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { HealthMetricEntity } from './health-metric.entity';
import type { IdentityPayload } from '@cdm/shared';

@Injectable()
export class HealthMetricService {
  constructor(
    @InjectRepository(HealthMetricEntity)
    private readonly repo: Repository<HealthMetricEntity>,
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

  async create(identity: IdentityPayload, patientId: number, data: { metricType: string, metricValue: string }) {
    const entity = this.repo.create({
      id: Date.now(), // Generate properly in prod
      tenantId: identity.tenantId,
      orgId: identity.orgId,
      patientId,
      metricType: data.metricType,
      metricValue: data.metricValue,
      recordedAt: new Date(),
    });
    return this.repo.save(entity);
  }
}
