import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { BigIntSerializerInterceptor, AUTH_TCP_PORT, PATIENT_TCP_PORT } from '@cdm/shared';

import { AuthProxyController } from './proxy/auth-proxy.controller.js';
import { PatientProxyController } from './proxy/patient-proxy.controller.js';
import { HealthMetricProxyController } from './proxy/health-metric-proxy.controller.js';
import { PatientFamilyLinkProxyController } from './proxy/patient-family-link-proxy.controller.js';
import { ManagerAssignmentProxyController } from './proxy/manager-assignment-proxy.controller.js';
import { ManagementSuggestionProxyController } from './proxy/management-suggestion-proxy.controller.js';
import { KnowledgeBaseProxyController } from './proxy/knowledge-base-proxy.controller.js';
import { KnowledgeDocumentProxyController } from './proxy/knowledge-document-proxy.controller.js';
import { AgentProxyService } from './proxy/services/agent-proxy.service.js';
import { MinioProxyService } from './proxy/services/minio-proxy.service.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
      signOptions: { expiresIn: '7d' },
    }),
    ClientsModule.register([
      {
        name: 'AUTH_SERVICE',
        transport: Transport.TCP,
        options: { host: process.env.AUTH_HOST || 'localhost', port: Number(process.env.AUTH_TCP_PORT) || AUTH_TCP_PORT },
      },
      {
        name: 'PATIENT_SERVICE',
        transport: Transport.TCP,
        options: { host: process.env.PATIENT_HOST || 'localhost', port: Number(process.env.PATIENT_TCP_PORT) || PATIENT_TCP_PORT },
      },
    ]),
  ],
  controllers: [
    AuthProxyController,
    PatientProxyController,
    HealthMetricProxyController,
    PatientFamilyLinkProxyController,
    ManagerAssignmentProxyController,
    ManagementSuggestionProxyController,
    KnowledgeBaseProxyController,
    KnowledgeDocumentProxyController,
  ],
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: BigIntSerializerInterceptor,
    },
    AgentProxyService,
    MinioProxyService,
  ],
})
export class AppModule {}
