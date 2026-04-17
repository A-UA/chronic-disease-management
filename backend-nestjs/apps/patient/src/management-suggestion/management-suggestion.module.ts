import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ManagementSuggestionEntity } from './management-suggestion.entity.js';
import { ManagementSuggestionService } from './management-suggestion.service.js';
import { ManagementSuggestionController } from './management-suggestion.controller.js';

@Module({
  imports: [TypeOrmModule.forFeature([ManagementSuggestionEntity])],
  controllers: [ManagementSuggestionController],
  providers: [ManagementSuggestionService],
})
export class ManagementSuggestionModule {}
