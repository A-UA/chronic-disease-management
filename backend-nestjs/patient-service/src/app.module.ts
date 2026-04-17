import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PatientModule } from './patient/patient.module';
import { HealthMetricModule } from './health-metric/health-metric.module';
import { PatientFamilyLinkModule } from './patient-family-link/patient-family-link.module';
import { ManagerAssignmentModule } from './manager-assignment/manager-assignment.module';
import { ManagementSuggestionModule } from './management-suggestion/management-suggestion.module';
import { KnowledgeModule } from './knowledge/knowledge.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      username: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
      database: process.env.DB_NAME || 'postgres',
      autoLoadEntities: true,
      synchronize: false,
    }),
    PatientModule,
    HealthMetricModule,
    PatientFamilyLinkModule,
    ManagerAssignmentModule,
    ManagementSuggestionModule,
    KnowledgeModule,
  ],
})
export class AppModule {}
