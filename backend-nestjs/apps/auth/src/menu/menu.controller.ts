import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { MenuService } from './menu.service.js';

@Controller()
export class MenuController {
  constructor(private readonly service: MenuService) {}

  @MessagePattern({ cmd: 'menu_list' })
  list(@Payload() payload: any) { return this.service.list(payload); }

  @MessagePattern({ cmd: 'menu_create' })
  create(@Payload() payload: any) { return this.service.create(payload); }

  @MessagePattern({ cmd: 'menu_update' })
  update(@Payload() payload: any) { return this.service.update(payload.id, payload.data); }

  @MessagePattern({ cmd: 'menu_delete' })
  delete(@Payload() payload: any) { return this.service.delete(payload.id); }
}
