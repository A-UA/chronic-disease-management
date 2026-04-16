import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { IdentityPayload } from '@cdm/shared';

export const CurrentUser = createParamDecorator(
  (_data: unknown, ctx: ExecutionContext): IdentityPayload => {
    const request = ctx.switchToHttp().getRequest();
    return request.identity;
  },
);
