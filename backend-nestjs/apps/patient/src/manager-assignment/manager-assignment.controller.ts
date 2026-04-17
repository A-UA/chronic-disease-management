import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { ManagerAssignmentService } from './manager-assignment.service.js';
import type { IdentityPayload } from '@cdm/shared';

@Controller()
export class ManagerAssignmentController {
  constructor(private readonly service: ManagerAssignmentService) {}

  @MessagePattern({ cmd: 'manager_assignment_find_all' })
  async findAll(@Payload() data: { identity: IdentityPayload; patientId: string }) {
    return this.service.findAllForPatient(data.identity, data.patientId);
  }

  @MessagePattern({ cmd: 'manager_assignment_create' })
  async assignManager(@Payload() data: { identity: IdentityPayload; patientId: string; managerUserId: string; assignmentType: string }) {
    return this.service.assignManager(data.identity, data.patientId, { managerUserId: data.managerUserId, assignmentType: data.assignmentType });
  }
}
