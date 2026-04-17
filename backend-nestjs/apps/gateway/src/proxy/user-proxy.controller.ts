import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { AUTH_SERVICE } from '@cdm/shared';
import type { IdentityPayload } from '@cdm/shared';
import { PaginationQueryDto, CreateUserDto, UpdateUserDto } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('users')
@UseGuards(JwtAuthGuard)
export class UserProxyController {
  constructor(@Inject(AUTH_SERVICE) private readonly authClient: ClientProxy) {}

  @Get()
  async list(@Query() query: PaginationQueryDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'user_list' }, { ...query, identity: user }));
  }

  @Post()
  async create(@Body() body: CreateUserDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'user_create' }, { data: body, identity: user }));
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() body: UpdateUserDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'user_update' }, { id, data: body, identity: user }));
  }

  @Delete(':id')
  async delete(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'user_delete' }, { id, identity: user }));
  }
}
