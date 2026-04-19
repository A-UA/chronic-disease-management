import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { HttpModule } from '@nestjs/axios';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { BigIntSerializerInterceptor, AUTH_TCP_PORT, PATIENT_TCP_PORT, AI_TCP_PORT } from '@cdm/shared';

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
import { ChatProxyController, ConversationProxyController } from './proxy/chat-proxy.controller.js';
import { TenantProxyController } from './proxy/tenant-proxy.controller.js';
import { OrganizationProxyController } from './proxy/org-proxy.controller.js';
import { UserProxyController } from './proxy/user-proxy.controller.js';
import { RoleProxyController } from './proxy/role-proxy.controller.js';
import { PermissionProxyController } from './proxy/permission-proxy.controller.js';
import { MenuProxyController } from './proxy/menu-proxy.controller.js';
@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
      signOptions: { expiresIn: '7d' },
    }),
    HttpModule,
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
      {
        name: 'AI_SERVICE',
        transport: Transport.TCP,
        options: { host: process.env.AI_HOST || 'localhost', port: Number(process.env.AI_TCP_PORT) || AI_TCP_PORT },
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
    ChatProxyController,
    ConversationProxyController,
    TenantProxyController,
    OrganizationProxyController,
    UserProxyController,
    RoleProxyController,
    PermissionProxyController,
    MenuProxyController,
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
