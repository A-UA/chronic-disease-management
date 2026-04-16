import { Controller, Get, Post, Body, UseGuards } from '@nestjs/common';
import { Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { PATIENT_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard';
import { CurrentUser } from '../decorators/current-user.decorator';

@Controller('api/v1/patients')
@UseGuards(JwtAuthGuard)
export class PatientProxyController {
  constructor(
    @Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy,
  ) {}

  @Get()
  findAll(@CurrentUser() identity: IdentityPayload) {
    return this.patientClient.send({ cmd: 'patient_find_all' }, identity);
  }

  @Post()
  createPatient(
    @CurrentUser() identity: IdentityPayload,
    @Body('name') name: string,
    @Body('gender') gender: string
  ) {
    return this.patientClient.send({ cmd: 'patient_create' }, { identity, name, gender });
  }
}
