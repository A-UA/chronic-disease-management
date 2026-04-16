import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ManagementSuggestionEntity } from './management-suggestion.entity';
import { ManagementSuggestionService } from './management-suggestion.service';
import { ManagementSuggestionController } from './management-suggestion.controller';

@Module({
  imports: [TypeOrmModule.forFeature([ManagementSuggestionEntity])],
  controllers: [ManagementSuggestionController],
  providers: [ManagementSuggestionService],
})
export class ManagementSuggestionModule {}
