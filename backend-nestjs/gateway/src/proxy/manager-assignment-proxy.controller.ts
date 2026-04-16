import { Controller, Get, Post, Param, Body, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { PATIENT_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard';
import { CurrentUser } from '../decorators/current-user.decorator';

@Controller('api/v1/manager-assignments')
@UseGuards(JwtAuthGuard)
export class ManagerAssignmentProxyController {
  constructor(
    @Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy,
  ) {}

  @Get(':patientId')
  findAll(@CurrentUser() identity: IdentityPayload, @Param('patientId') patientId: number) {
    return this.patientClient.send({ cmd: 'manager_assignment_find_all' }, { identity, patientId });
  }

  @Post(':patientId')
  assignManager(
    @CurrentUser() identity: IdentityPayload, 
    @Param('patientId') patientId: number,
    @Body('managerUserId') managerUserId: number,
    @Body('assignmentType') assignmentType: string
  ) {
    return this.patientClient.send({ cmd: 'manager_assignment_create' }, { identity, patientId, managerUserId, assignmentType });
  }
}
