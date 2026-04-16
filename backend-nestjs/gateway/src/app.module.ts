import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { JwtModule } from '@nestjs/jwt';
import { AUTH_SERVICE, AUTH_TCP_PORT, PATIENT_SERVICE, PATIENT_TCP_PORT } from '@cdm/shared';
import { AuthProxyController } from './proxy/auth-proxy.controller';
import { PatientProxyController } from './proxy/patient-proxy.controller';
import { HealthMetricProxyController } from './proxy/health-metric-proxy.controller';
import { PatientFamilyLinkProxyController } from './proxy/patient-family-link-proxy.controller';
import { ManagerAssignmentProxyController } from './proxy/manager-assignment-proxy.controller';
import { ManagementSuggestionProxyController } from './proxy/management-suggestion-proxy.controller';
import { KnowledgeBaseProxyController } from './proxy/knowledge-base-proxy.controller';
import { KnowledgeDocumentProxyController } from './proxy/knowledge-document-proxy.controller';
import { MinioProxyService } from './proxy/services/minio-proxy.service';
import { AgentProxyService } from './proxy/services/agent-proxy.service';
import { HttpModule } from '@nestjs/axios';

@Module({
  imports: [
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
    }),
    ClientsModule.register([
      {
        name: AUTH_SERVICE,
        transport: Transport.TCP,
        options: { host: 'localhost', port: AUTH_TCP_PORT },
      },
      {
        name: PATIENT_SERVICE,
        transport: Transport.TCP,
        options: { host: 'localhost', port: PATIENT_TCP_PORT },
      },
    ]),
    HttpModule,
  ],
  controllers: [
    AuthProxyController, 
    PatientProxyController, 
    HealthMetricProxyController, 
    PatientFamilyLinkProxyController,
    ManagerAssignmentProxyController,
    ManagementSuggestionProxyController,
    KnowledgeBaseProxyController,
    KnowledgeDocumentProxyController
  ],
  providers: [
    MinioProxyService,
    AgentProxyService
  ]
})
export class AppModule {}
