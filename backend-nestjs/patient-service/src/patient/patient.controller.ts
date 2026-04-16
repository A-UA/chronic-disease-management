import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { PatientService } from './patient.service';
import { PATIENT_SERVICE } from '@cdm/shared';
import type { IdentityPayload } from '@cdm/shared';

@Controller()
export class PatientController {
  constructor(private readonly patientService: PatientService) {}

  @MessagePattern({ cmd: 'patient_find_all' })
  async findAll(@Payload() identity: IdentityPayload) {
    return this.patientService.findAll(identity);
  }
}
