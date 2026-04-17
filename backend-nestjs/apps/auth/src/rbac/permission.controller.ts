import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { PermissionService } from './permission.service.js';

@Controller()
export class PermissionController {
  constructor(private readonly service: PermissionService) {}

  @MessagePattern({ cmd: 'permission_list' })
  list(@Payload() payload: any) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'permission_create' })
  create(@Payload() payload: any) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'permission_update' })
  update(@Payload() payload: any) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'permission_delete' })
  delete(@Payload() payload: any) { return this.service.delete(payload.id); }
}
