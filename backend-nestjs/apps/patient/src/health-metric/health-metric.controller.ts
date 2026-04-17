import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { HealthMetricService } from './health-metric.service.js';
import type { PatientIdPayload, CreateHealthMetricPayload } from '@cdm/shared';

@Controller()
export class HealthMetricController {
  constructor(private readonly service: HealthMetricService) {}

  @MessagePattern({ cmd: 'health_metric_find_all' })
  async findAll(@Payload() data: PatientIdPayload) {
    return this.service.findAllForPatient(data.identity, data.patientId);
  }

  @MessagePattern({ cmd: 'health_metric_create' })
  async create(@Payload() data: CreateHealthMetricPayload) {
    return this.service.create(data.identity, data.patientId, { metricType: data.metricType, metricValue: data.metricValue });
  }
}
