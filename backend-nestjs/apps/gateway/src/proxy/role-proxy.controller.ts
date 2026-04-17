import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { AUTH_SERVICE } from '@cdm/shared';
import type { IdentityPayload } from '@cdm/shared';
import { PaginationQueryDto, CreateRoleDto, UpdateRoleDto } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('rbac/roles')
@UseGuards(JwtAuthGuard)
export class RoleProxyController {
  constructor(@Inject(AUTH_SERVICE) private readonly authClient: ClientProxy) {}

  @Get()
  async list(@Query() query: PaginationQueryDto, @CurrentUser() user: IdentityPayload) {
    const res = await firstValueFrom(this.authClient.send({ cmd: 'role_list' }, { ...query, identity: user }));

    // tenants, orgs, users list endpoints expect PaginatedResult { total, items }
    if (res && res.items) return res.items;
    return res;
  }

  @Post()
  async create(@Body() body: CreateRoleDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'role_create' }, { data: body, identity: user }));
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() body: UpdateRoleDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'role_update' }, { id, data: body, identity: user }));
  }

  @Delete(':id')
  async delete(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'role_delete' }, { id, identity: user }));
  }
}
