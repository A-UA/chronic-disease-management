import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { PatientFamilyLinkService } from './patient-family-link.service.js';
import type { IdentityPayload } from '@cdm/shared';

@Controller()
export class PatientFamilyLinkController {
  constructor(private readonly service: PatientFamilyLinkService) {}

  @MessagePattern({ cmd: 'family_find_all' })
  async findAll(@Payload() data: { identity: IdentityPayload; patientId: number }) {
    return this.service.findAllForPatient(data.identity, data.patientId);
  }

  @MessagePattern({ cmd: 'family_link' })
  async linkFamily(@Payload() data: { identity: IdentityPayload; patientId: number; familyUserId: number; relationship: string }) {
    return this.service.linkFamily(data.identity, data.patientId, { familyUserId: data.familyUserId, relationship: data.relationship });
  }
}
