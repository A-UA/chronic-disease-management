import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { OrganizationService } from './org.service.js';
import { AUTH_DASHBOARD_STATS } from '@cdm/shared';
import type {
  ListPayload,
  CreatePayload,
  UpdatePayload,
  DeletePayload,
  CreateOrgData,
  UpdateOrgData,
} from '@cdm/shared';

@Controller()
export class OrganizationController {
  constructor(private readonly service: OrganizationService) {}

  @MessagePattern({ cmd: 'org_list' })
  list(@Payload() payload: ListPayload) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'org_create' })
  create(@Payload() payload: CreatePayload<CreateOrgData>) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'org_update' })
  update(@Payload() payload: UpdatePayload<UpdateOrgData>) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'org_delete' })
  delete(@Payload() payload: DeletePayload) { return this.service.delete(payload.id); }

  @MessagePattern({ cmd: AUTH_DASHBOARD_STATS })
  dashboardStats() { return this.service.dashboardStats(); }
}
