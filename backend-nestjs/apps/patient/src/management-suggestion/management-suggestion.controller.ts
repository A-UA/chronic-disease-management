import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { ManagementSuggestionService } from './management-suggestion.service.js';
import type { PatientIdPayload, CreateSuggestionPayload } from '@cdm/shared';

@Controller()
export class ManagementSuggestionController {
  constructor(private readonly service: ManagementSuggestionService) {}

  @MessagePattern({ cmd: 'management_suggestion_find_all' })
  async findAll(@Payload() data: PatientIdPayload) {
    return this.service.findAllForPatient(data.identity, data.patientId);
  }

  @MessagePattern({ cmd: 'management_suggestion_create' })
  async createSuggestion(@Payload() data: CreateSuggestionPayload) {
    return this.service.createSuggestion(data.identity, data.patientId, { suggestionType: data.suggestionType, content: data.content });
  }
}
