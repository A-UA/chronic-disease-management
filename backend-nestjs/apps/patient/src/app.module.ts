import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { databaseConfig } from '@cdm/shared';
import { PatientModule } from './patient/patient.module.js';
import { HealthMetricModule } from './health-metric/health-metric.module.js';
import { PatientFamilyLinkModule } from './patient-family-link/patient-family-link.module.js';
import { ManagerAssignmentModule } from './manager-assignment/manager-assignment.module.js';
import { ManagementSuggestionModule } from './management-suggestion/management-suggestion.module.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [databaseConfig] }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get<string>('database.host'),
        port: config.get<number>('database.port'),
        username: config.get<string>('database.username'),
        password: config.get<string>('database.password'),
        database: config.get<string>('database.database'),
        autoLoadEntities: true,
        synchronize: false,
      }),
    }),
    PatientModule,
    HealthMetricModule,
    PatientFamilyLinkModule,
    ManagerAssignmentModule,
    ManagementSuggestionModule,
  ],
})
export class AppModule {}
