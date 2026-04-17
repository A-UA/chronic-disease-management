import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { TenantService } from './tenant.service.js';
import type {
  ListPayload,
  CreatePayload,
  UpdatePayload,
  DeletePayload,
  CreateTenantData,
  UpdateTenantData,
} from '@cdm/shared';

@Controller()
export class TenantController {
  constructor(private readonly service: TenantService) {}

  @MessagePattern({ cmd: 'tenant_list' })
  list(@Payload() payload: ListPayload) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'tenant_create' })
  create(@Payload() payload: CreatePayload<CreateTenantData>) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'tenant_update' })
  update(@Payload() payload: UpdatePayload<UpdateTenantData>) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'tenant_delete' })
  delete(@Payload() payload: DeletePayload) { return this.service.delete(payload.id); }
}
