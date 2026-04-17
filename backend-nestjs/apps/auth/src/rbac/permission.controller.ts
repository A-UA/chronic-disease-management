import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { PermissionService } from './permission.service.js';
import type {
  ListPayload,
  CreatePayload,
  UpdatePayload,
  DeletePayload,
  CreatePermissionData,
  UpdatePermissionData,
} from '@cdm/shared';

@Controller()
export class PermissionController {
  constructor(private readonly service: PermissionService) {}

  @MessagePattern({ cmd: 'permission_list' })
  list(@Payload() payload: ListPayload) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'permission_create' })
  create(@Payload() payload: CreatePayload<CreatePermissionData>) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'permission_update' })
  update(@Payload() payload: UpdatePayload<UpdatePermissionData>) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'permission_delete' })
  delete(@Payload() payload: DeletePayload) { return this.service.delete(payload.id); }
}
