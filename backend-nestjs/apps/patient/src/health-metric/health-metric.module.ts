import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HealthMetricEntity } from './health-metric.entity.js';
import { HealthMetricService } from './health-metric.service.js';
import { HealthMetricController } from './health-metric.controller.js';

@Module({
  imports: [TypeOrmModule.forFeature([HealthMetricEntity])],
  controllers: [HealthMetricController],
  providers: [HealthMetricService],
})
export class HealthMetricModule {}
