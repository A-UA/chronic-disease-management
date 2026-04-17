import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { UserService } from './user.service.js';
import type {
  ListPayload,
  CreatePayload,
  UpdatePayload,
  DeletePayload,
  CreateUserData,
  UpdateUserData,
} from '@cdm/shared';

@Controller()
export class UserController {
  constructor(private readonly service: UserService) {}

  @MessagePattern({ cmd: 'user_list' })
  list(@Payload() payload: ListPayload) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'user_create' })
  create(@Payload() payload: CreatePayload<CreateUserData>) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'user_update' })
  update(@Payload() payload: UpdatePayload<UpdateUserData>) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'user_delete' })
  delete(@Payload() payload: DeletePayload) { return this.service.delete(payload.id); }
}
