import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { RoleService } from './role.service.js';
import type {
  ListPayload,
  CreatePayload,
  UpdatePayload,
  DeletePayload,
  CreateRoleData,
  UpdateRoleData,
} from '@cdm/shared';

@Controller()
export class RoleController {
  constructor(private readonly service: RoleService) {}

  @MessagePattern({ cmd: 'role_list' })
  list(@Payload() payload: ListPayload) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'role_create' })
  create(@Payload() payload: CreatePayload<CreateRoleData>) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'role_update' })
  update(@Payload() payload: UpdatePayload<UpdateRoleData>) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'role_delete' })
  delete(@Payload() payload: DeletePayload) { return this.service.delete(payload.id); }
}
