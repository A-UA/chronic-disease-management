import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { OrganizationService } from './org.service.js';

@Controller()
export class OrganizationController {
  constructor(private readonly service: OrganizationService) {}

  @MessagePattern({ cmd: 'org_list' })
  list(@Payload() payload: any) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'org_create' })
  create(@Payload() payload: any) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'org_update' })
  update(@Payload() payload: any) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'org_delete' })
  delete(@Payload() payload: any) { return this.service.delete(payload.id); }
}
