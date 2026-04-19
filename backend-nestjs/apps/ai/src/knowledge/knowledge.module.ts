import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { KnowledgeBaseEntity } from './entities/knowledge-base.entity.js';
import { DocumentEntity } from './entities/document.entity.js';
import { KnowledgeController } from './knowledge.controller.js';
import { KnowledgeService } from './knowledge.service.js';
import { InfraModule } from '../infra/infra.module.js';

@Module({
  imports: [
    TypeOrmModule.forFeature([KnowledgeBaseEntity, DocumentEntity]),
    InfraModule,
  ],
  controllers: [KnowledgeController],
  providers: [KnowledgeService],
})
export class KnowledgeModule {}
