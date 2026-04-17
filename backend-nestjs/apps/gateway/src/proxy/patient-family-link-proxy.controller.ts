import { Controller, Get, Post, Param, Body, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { PATIENT_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('family-links')
@UseGuards(JwtAuthGuard)
export class PatientFamilyLinkProxyController {
  constructor(
    @Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy,
  ) {}

  @Get(':patientId')
  findAll(@CurrentUser() identity: IdentityPayload, @Param('patientId') patientId: string) {
    return this.patientClient.send({ cmd: 'family_find_all' }, { identity, patientId });
  }

  @Post(':patientId')
  linkFamily(
    @CurrentUser() identity: IdentityPayload, 
    @Param('patientId') patientId: string,
    @Body('familyUserId') familyUserId: string,
    @Body('relationship') relationship: string
  ) {
    return this.patientClient.send({ cmd: 'family_link' }, { identity, patientId, familyUserId, relationship });
  }
}
