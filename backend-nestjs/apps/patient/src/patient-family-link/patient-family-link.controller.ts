import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { PatientFamilyLinkService } from './patient-family-link.service.js';
import type { PatientIdPayload, LinkFamilyPayload } from '@cdm/shared';

@Controller()
export class PatientFamilyLinkController {
  constructor(private readonly service: PatientFamilyLinkService) {}

  @MessagePattern({ cmd: 'family_find_all' })
  async findAll(@Payload() data: PatientIdPayload) {
    return this.service.findAllForPatient(data.identity, data.patientId);
  }

  @MessagePattern({ cmd: 'family_link' })
  async linkFamily(@Payload() data: LinkFamilyPayload) {
    return this.service.linkFamily(data.identity, data.patientId, { familyUserId: data.familyUserId, relationship: data.relationship });
  }
}
