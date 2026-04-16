import {
  Body,
  Controller,
  Get,
  Inject,
  Post,
  UseGuards,
} from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { AUTH_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard';
import { CurrentUser } from '../decorators/current-user.decorator';

class LoginBody {
  username: string;
  password: string;
}

class SelectOrgBody {
  orgId: number;
  selectionToken: string;
}

class SwitchOrgBody {
  orgId: number;
}

@Controller('api/v1/auth')
export class AuthProxyController {
  constructor(
    @Inject(AUTH_SERVICE) private readonly authClient: ClientProxy,
  ) {}

  @Post('login/access-token')
  async login(@Body() body: LoginBody) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'login' }, body),
    );
  }

  @Post('select-org')
  async selectOrg(@Body() body: SelectOrgBody) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'select_org' }, body),
    );
  }

  @Post('switch-org')
  @UseGuards(JwtAuthGuard)
  async switchOrg(
    @Body() body: SwitchOrgBody,
    @CurrentUser() identity: IdentityPayload,
  ) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'switch_org' }, { identity, orgId: body.orgId }),
    );
  }

  @Get('my-orgs')
  @UseGuards(JwtAuthGuard)
  async myOrgs(@CurrentUser() identity: IdentityPayload) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'my_orgs' }, { identity }),
    );
  }

  @Get('me')
  @UseGuards(JwtAuthGuard)
  async me(@CurrentUser() identity: IdentityPayload) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'get_me' }, { identity }),
    );
  }

  @Get('menu-tree')
  @UseGuards(JwtAuthGuard)
  async menuTree(@CurrentUser() identity: IdentityPayload) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'menu_tree' }, { identity }),
    );
  }
}
