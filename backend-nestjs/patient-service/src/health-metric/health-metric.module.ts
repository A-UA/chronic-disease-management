import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HealthMetricEntity } from './health-metric.entity';
import { HealthMetricService } from './health-metric.service';
import { HealthMetricController } from './health-metric.controller';

@Module({
  imports: [TypeOrmModule.forFeature([HealthMetricEntity])],
  controllers: [HealthMetricController],
  providers: [HealthMetricService],
})
export class HealthMetricModule {}
