import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { UserService } from './user.service.js';

@Controller()
export class UserController {
  constructor(private readonly service: UserService) {}

  @MessagePattern({ cmd: 'user_list' })
  list(@Payload() payload: any) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'user_create' })
  create(@Payload() payload: any) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'user_update' })
  update(@Payload() payload: any) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'user_delete' })
  delete(@Payload() payload: any) { return this.service.delete(payload.id); }
}
