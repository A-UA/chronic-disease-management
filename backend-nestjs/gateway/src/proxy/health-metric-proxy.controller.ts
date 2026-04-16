import { Controller, Get, Post, Param, Body, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { PATIENT_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard';
import { CurrentUser } from '../decorators/current-user.decorator';

@Controller('api/v1/health-metrics')
@UseGuards(JwtAuthGuard)
export class HealthMetricProxyController {
  constructor(
    @Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy,
  ) {}

  @Get(':patientId')
  findAll(@CurrentUser() identity: IdentityPayload, @Param('patientId') patientId: number) {
    return this.patientClient.send({ cmd: 'health_metric_find_all' }, { identity, patientId });
  }

  @Post(':patientId')
  create(
    @CurrentUser() identity: IdentityPayload, 
    @Param('patientId') patientId: number,
    @Body('metricType') metricType: string,
    @Body('metricValue') metricValue: string
  ) {
    return this.patientClient.send({ cmd: 'health_metric_create' }, { identity, patientId, metricType, metricValue });
  }
}
