import { Controller, Get, Post, Param, Body, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { PATIENT_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('management-suggestions')
@UseGuards(JwtAuthGuard)
export class ManagementSuggestionProxyController {
  constructor(
    @Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy,
  ) {}

  @Get(':patientId')
  findAll(@CurrentUser() identity: IdentityPayload, @Param('patientId') patientId: number) {
    return this.patientClient.send({ cmd: 'management_suggestion_find_all' }, { identity, patientId });
  }

  @Post(':patientId')
  createSuggestion(
    @CurrentUser() identity: IdentityPayload, 
    @Param('patientId') patientId: number,
    @Body('suggestionType') suggestionType: string,
    @Body('content') content: string
  ) {
    return this.patientClient.send({ cmd: 'management_suggestion_create' }, { identity, patientId, suggestionType, content });
  }
}
