import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { RoleService } from './role.service.js';

@Controller()
export class RoleController {
  constructor(private readonly service: RoleService) {}

  @MessagePattern({ cmd: 'role_list' })
  list(@Payload() payload: any) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'role_create' })
  create(@Payload() payload: any) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'role_update' })
  update(@Payload() payload: any) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'role_delete' })
  delete(@Payload() payload: any) { return this.service.delete(payload.id); }
}
