import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { AUTH_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('menus')
@UseGuards(JwtAuthGuard)
export class MenuProxyController {
  constructor(@Inject(AUTH_SERVICE) private readonly authClient: ClientProxy) {}

  @Get()
  async list(@Query() query: any, @CurrentUser() user: IdentityPayload) {
    const res = await firstValueFrom(this.authClient.send({ cmd: 'menu_list' }, { ...query, identity: user }));

    // tenants, orgs, users list endpoints expect PaginatedResult { total, items }
    if (res && res.items) return res.items;
    return res;
  }

  @Post()
  async create(@Body() body: any, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'menu_create' }, { ...body, identity: user }));
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() body: any, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'menu_update' }, { id, data: body, identity: user }));
  }

  @Delete(':id')
  async delete(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'menu_delete' }, { id, identity: user }));
  }
}
