import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { PatientService } from './patient.service.js';
import { PATIENT_DASHBOARD_STATS } from '@cdm/shared';
import type { IdentityPayload, CreatePatientPayload } from '@cdm/shared';

@Controller()
export class PatientController {
  constructor(private readonly patientService: PatientService) {}

  @MessagePattern({ cmd: 'patient_find_all' })
  async findAll(@Payload() identity: IdentityPayload) {
    return this.patientService.findAll(identity);
  }

  @MessagePattern({ cmd: 'patient_create' })
  async createPatient(@Payload() data: CreatePatientPayload) {
    return this.patientService.createPatient(data.identity, { name: data.name, gender: data.gender });
  }

  @MessagePattern({ cmd: PATIENT_DASHBOARD_STATS })
  dashboardStats() { return this.patientService.dashboardStats(); }
}
